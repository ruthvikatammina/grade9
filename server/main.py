"""
TGTraffic — FastAPI backend.

Provider fallback chain per route:
  1. Google Maps Routes API  (best accuracy)
  2. TomTom Routing API      (free tier, used when Google fails)
  3. No result for that route (skipped silently)

Results are cached for 5 minutes.
"""

import asyncio
import hashlib
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx
from jinja2 import Environment, FileSystemLoader

from server.config import (
    GOOGLE_MAPS_API_KEY, TOMTOM_API_KEY, MAPBOX_TOKEN,
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
    logger.info('GOOGLE_MAPS_API_KEY set: %s', bool(GOOGLE_MAPS_API_KEY))
    logger.info('TOMTOM_API_KEY set: %s',      bool(TOMTOM_API_KEY))
    logger.info('MAPBOX_TOKEN set: %s',         bool(MAPBOX_TOKEN))


@app.get('/')
async def index(request: Request):
    tmpl = templates.get_template('index.html')
    return HTMLResponse(tmpl.render(mapboxToken=MAPBOX_TOKEN))


@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.get('/api/debug')
async def debug():
    results = {}

    # Test Google
    if GOOGLE_MAPS_API_KEY:
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
            if data.get('routes'):
                r = data['routes'][0]
                normal  = int(r.get('staticDuration', '0s').rstrip('s'))
                traffic = int(r.get('duration',       '0s').rstrip('s'))
                results['google'] = {'status': 'OK', 'normal_mins': round(normal/60,1), 'traffic_mins': round(traffic/60,1)}
            else:
                results['google'] = {'status': 'ERROR', 'detail': data.get('error', data)}
        except Exception as e:
            results['google'] = {'status': 'ERROR', 'detail': str(e)}
    else:
        results['google'] = {'status': 'NOT_CONFIGURED'}

    # Test TomTom
    if TOMTOM_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f'https://api.tomtom.com/routing/1/calculateRoute/'
                    f'17.3850,78.4867:17.4454,78.3794/json',
                    params={'key': TOMTOM_API_KEY, 'traffic': 'true', 'travelMode': 'car'},
                )
            data = resp.json()
            routes = data.get('routes', [])
            if routes:
                summary = routes[0]['summary']
                normal  = summary.get('noTrafficTravelTimeInSeconds', summary['travelTimeInSeconds'])
                traffic = summary['travelTimeInSeconds']
                results['tomtom'] = {'status': 'OK', 'normal_mins': round(normal/60,1), 'traffic_mins': round(traffic/60,1)}
            else:
                results['tomtom'] = {'status': 'ERROR', 'detail': data}
        except Exception as e:
            results['tomtom'] = {'status': 'ERROR', 'detail': str(e)}
    else:
        results['tomtom'] = {'status': 'NOT_CONFIGURED'}

    return results


@app.get('/api/incidents')
async def incidents(bbox: Optional[str] = None) -> JSONResponse:
    if not bbox:
        raise HTTPException(400, 'Missing bbox parameter (min_lng,min_lat,max_lng,max_lat)')
    if not GOOGLE_MAPS_API_KEY and not TOMTOM_API_KEY:
        raise HTTPException(500, 'No traffic API key configured')

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

    async def query_google(origin_lat, origin_lng, dest_lat, dest_lng):
        if not GOOGLE_MAPS_API_KEY:
            return None
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
        if resp.status_code in (429, 403):
            return None
        data = resp.json()
        if data.get('error', {}).get('status') in ('RESOURCE_EXHAUSTED', 'PERMISSION_DENIED'):
            return None
        resp.raise_for_status()
        routes = data.get('routes', [])
        if not routes:
            return None
        r       = routes[0]
        normal  = int(r.get('staticDuration', '0s').rstrip('s'))
        traffic = int(r.get('duration',       '0s').rstrip('s'))
        return normal, traffic

    async def query_tomtom(origin_lat, origin_lng, dest_lat, dest_lng):
        if not TOMTOM_API_KEY:
            return None
        async with httpx.AsyncClient(timeout=GOOGLE_MAPS_API_TIMEOUT) as client:
            resp = await client.get(
                f'https://api.tomtom.com/routing/1/calculateRoute/'
                f'{origin_lat},{origin_lng}:{dest_lat},{dest_lng}/json',
                params={'key': TOMTOM_API_KEY, 'traffic': 'true', 'travelMode': 'car'},
            )
        if resp.status_code != 200:
            return None
        data   = resp.json()
        routes = data.get('routes', [])
        if not routes:
            return None
        summary = routes[0]['summary']
        normal  = summary.get('noTrafficTravelTimeInSeconds', summary['travelTimeInSeconds'])
        traffic = summary['travelTimeInSeconds']
        return normal, traffic

    async def query(origin_lat, origin_lng, dest_lat, dest_lng, name):
        mid_lat = (origin_lat + dest_lat) / 2
        mid_lng = (origin_lng + dest_lng) / 2
        try:
            times = await query_google(origin_lat, origin_lng, dest_lat, dest_lng)
            if times is None:
                logger.info('Google failed for %s — trying TomTom', name)
                times = await query_tomtom(origin_lat, origin_lng, dest_lat, dest_lng)
            if times is None:
                return None

            normal, traffic = times
            cong = calculate_congestion(traffic, normal)
            return {
                'description':      name,
                'event':            cong['event_type'],
                'severity':         cong['severity'],
                'coordinates':      [mid_lng, mid_lat],
                'lat':              mid_lat,
                'lng':              mid_lng,
                'normal_mins':      round(normal  / 60, 1),
                'traffic_mins':     round(traffic / 60, 1),
                'delay_mins':       round((traffic - normal) / 60, 1),
                'delay_ratio':      round(cong['delay_ratio'], 2),
                'duration_normal':  normal,
                'duration_traffic': traffic,
            }
        except Exception as e:
            logger.warning('Route %s failed: %s', name, e)
            return None

    semaphore = asyncio.Semaphore(5)

    async def query_throttled(*args):
        async with semaphore:
            return await query(*args)

    results = await asyncio.gather(*[query_throttled(*r) for r in visible])
    routes  = [r for r in results if r is not None]

    if routes:
        incidents_cache.set(cache_key, routes, ttl_seconds=CACHE_TTL_SECONDS)
    logger.info('Returning %d routes (source: google+tomtom fallback)', len(routes))
    return JSONResponse({'incidents': routes, 'cached': False})


@app.on_event('shutdown')
async def shutdown():
    logger.info('TGTraffic shutting down')
