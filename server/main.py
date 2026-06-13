"""
TGTraffic — FastAPI backend.

Queries the Google Maps Routes API for each configured route and returns
live travel times. Results are cached for 5 minutes so manual refreshes
stay within Google's free tier.
"""

import asyncio
import hashlib
import logging
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx
from jinja2 import Environment, FileSystemLoader

from server.config import (
    GOOGLE_MAPS_API_KEY, MAPBOX_TOKEN, PORT,
    HYDERABAD_ROUTES, CACHE_TTL_SECONDS, BBOX_TOLERANCE,
    GOOGLE_MAPS_API_TIMEOUT,
)
from server.utils import calculate_congestion, is_route_in_bbox
from server.cache import incidents_cache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
logger = logging.getLogger('tgtraffic')

app = FastAPI(title='TGTraffic')
app.mount('/static', StaticFiles(directory='public'), name='static')
templates = Environment(loader=FileSystemLoader('templates'))


@app.on_event('startup')
async def startup():
    logger.info('TGTraffic starting up')
    logger.info('MAPBOX_TOKEN set: %s', bool(MAPBOX_TOKEN))
    logger.info('GOOGLE_MAPS_API_KEY set: %s', bool(GOOGLE_MAPS_API_KEY))
    if not GOOGLE_MAPS_API_KEY:
        logger.warning('GOOGLE_MAPS_API_KEY not set — API calls will fail')


@app.get('/')
async def index(request: Request):
    tmpl = templates.get_template('index.html')
    return HTMLResponse(tmpl.render(mapboxToken=MAPBOX_TOKEN))


@app.get('/health')
async def health():
    return {'status': 'ok'}



@app.get('/api/debug')
async def debug():
    """Quick smoke-test: calls the Routes API for one route and shows raw result."""
    if not GOOGLE_MAPS_API_KEY:
        return {'error': 'GOOGLE_MAPS_API_KEY not set'}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                'https://routes.googleapis.com/directions/v2:computeRoutes',
                headers={
                    'X-Goog-Api-Key': GOOGLE_MAPS_API_KEY,
                    'X-Goog-FieldMask': 'routes.duration,routes.staticDuration',
                    'Content-Type': 'application/json',
                },
                json={
                    'origin':      {'location': {'latLng': {'latitude': 17.3850, 'longitude': 78.4867}}},
                    'destination': {'location': {'latLng': {'latitude': 17.4454, 'longitude': 78.3794}}},
                    'travelMode': 'DRIVE',
                    'routingPreference': 'TRAFFIC_AWARE',
                },
            )
        data = resp.json()
        if not data.get('routes'):
            return {'status': 'ERROR', 'response': data}
        route = data['routes'][0]
        normal  = int(route.get('staticDuration', '0s').rstrip('s'))
        traffic = int(route.get('duration',       '0s').rstrip('s'))
        return {
            'status': 'OK',
            'normal_mins':  round(normal  / 60, 1),
            'traffic_mins': round(traffic / 60, 1),
            'delay_mins':   round((traffic - normal) / 60, 1),
        }
    except Exception as e:
        return {'error': str(e)}


@app.get('/api/incidents')
async def incidents(bbox: Optional[str] = None) -> JSONResponse:
    if not bbox:
        raise HTTPException(400, 'Missing bbox parameter (min_lng,min_lat,max_lng,max_lat)')
    if not GOOGLE_MAPS_API_KEY:
        raise HTTPException(500, 'GOOGLE_MAPS_API_KEY not configured')

    try:
        min_lng, min_lat, max_lng, max_lat = [float(x) for x in bbox.split(',')]
    except (ValueError, IndexError):
        raise HTTPException(400, 'Invalid bbox format')

    cache_key = hashlib.md5(bbox.encode()).hexdigest()
    cached = incidents_cache.get(cache_key)
    if cached is not None:
        logger.info('Cache HIT — returning %d routes', len(cached))
        return JSONResponse({'incidents': cached, 'cached': True})

    visible = [
        r for r in HYDERABAD_ROUTES
        if is_route_in_bbox(r[0], r[1], r[2], r[3], min_lat, min_lng, max_lat, max_lng,
                            tolerance=BBOX_TOLERANCE)
    ]
    logger.info('%d/%d routes in viewport', len(visible), len(HYDERABAD_ROUTES))

    async def query(origin_lat, origin_lng, dest_lat, dest_lng, name):
        mid_lat = (origin_lat + dest_lat) / 2
        mid_lng = (origin_lng + dest_lng) / 2
        try:
            async with httpx.AsyncClient(timeout=GOOGLE_MAPS_API_TIMEOUT) as client:
                resp = await client.post(
                    'https://routes.googleapis.com/directions/v2:computeRoutes',
                    headers={
                        'X-Goog-Api-Key': GOOGLE_MAPS_API_KEY,
                        'X-Goog-FieldMask': 'routes.duration,routes.staticDuration',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'origin':      {'location': {'latLng': {'latitude': origin_lat, 'longitude': origin_lng}}},
                        'destination': {'location': {'latLng': {'latitude': dest_lat,   'longitude': dest_lng}}},
                        'travelMode': 'DRIVE',
                        'routingPreference': 'TRAFFIC_AWARE',
                    },
                )

            if resp.status_code == 429:
                logger.warning('Rate limited on route %s — skipping', name)
                return None
            data = resp.json()
            err_status = data.get('error', {}).get('status', '')
            if err_status == 'RESOURCE_EXHAUSTED':
                logger.warning('Resource exhausted for route %s — skipping', name)
                return None

            resp.raise_for_status()
            if not data.get('routes'):
                return None

            r       = data['routes'][0]
            normal  = int(r.get('staticDuration', '0s').rstrip('s'))
            traffic = int(r.get('duration',       '0s').rstrip('s'))
            cong    = calculate_congestion(traffic, normal)

            return {
                'description':    name,
                'event':          cong['event_type'],
                'severity':       cong['severity'],
                'coordinates':    [mid_lng, mid_lat],
                'lat':            mid_lat,
                'lng':            mid_lng,
                'normal_mins':    round(normal  / 60, 1),
                'traffic_mins':   round(traffic / 60, 1),
                'delay_mins':     round((traffic - normal) / 60, 1),
                'delay_ratio':    round(cong['delay_ratio'], 2),
                'duration_normal':  normal,
                'duration_traffic': traffic,
            }
        except Exception as e:
            logger.warning('Route %s failed: %s', name, e)
            return None

    # Limit to 5 concurrent Google API calls to avoid rate-limiting
    semaphore = asyncio.Semaphore(5)

    async def query_throttled(*args):
        async with semaphore:
            return await query(*args)

    results = await asyncio.gather(*[query_throttled(*r) for r in visible])
    routes  = [r for r in results if r is not None]

    # Only cache if we got actual results — don't cache empty failures
    if routes:
        incidents_cache.set(cache_key, routes, ttl_seconds=CACHE_TTL_SECONDS)
    logger.info('Returning %d routes', len(routes))
    return JSONResponse({'incidents': routes, 'cached': False})


@app.on_event('shutdown')
async def shutdown():
    logger.info('TGTraffic shutting down')
