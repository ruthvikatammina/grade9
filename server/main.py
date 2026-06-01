"""
Hyderabad Traffic Dashboard Backend.

A FastAPI application that provides real-time traffic data for Hyderabad
by querying the Google Maps Directions API and analyzing travel time delays.

Learning objectives:
- Building a REST API with FastAPI
- Async/await pattern with httpx
- Error handling and validation
- Logging for debugging
- Caching to improve performance
"""

import logging
from typing import Optional, List, Dict
import hashlib

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx
from jinja2 import Environment, FileSystemLoader

# Import our modules (learning: modular code organization)
from server.config import *
from server.utils import calculate_congestion, is_route_in_bbox
from server.cache import incidents_cache

# Configure logging (learning: how to debug applications)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hyderabad-traffic")

# Initialize FastAPI app
app = FastAPI(title="Hyderabad Traffic MVP")

# Serve the frontend static files and templates
app.mount("/static", StaticFiles(directory="public"), name="static")
templates_env = Environment(loader=FileSystemLoader('templates'))


@app.on_event("startup")
async def startup_event():
    """Log startup information for debugging."""
    logger.info("Starting Hyderabad Traffic Dashboard")
    logger.info("MAPBOX_ACCESS_TOKEN is set: %s", bool(MAPBOX_TOKEN))
    logger.info("GOOGLE_MAPS_API_KEY is set: %s", bool(GOOGLE_MAPS_API_KEY))
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("WARNING: GOOGLE_MAPS_API_KEY not set. API calls will fail.")



# ============================================================================
# ROUTE: Root Page
# ============================================================================

@app.get('/')
async def root_index(request: Request):
    """Serve the main HTML page with Mapbox token injected."""
    tmpl = templates_env.get_template('index.html')
    content = tmpl.render(mapboxToken=MAPBOX_TOKEN)
    return HTMLResponse(content=content)


# ============================================================================
# ROUTE: Health Check
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint for deployment monitoring."""
    return {"status": "ok"}


# ============================================================================
# ROUTE: Configuration
# ============================================================================

@app.get('/config')
async def get_config():
    """Return frontend configuration (e.g., Mapbox token)."""
    return {"mapboxToken": MAPBOX_TOKEN}


# ============================================================================
# ROUTE: Traffic Incidents
# ============================================================================



@app.get('/api/incidents')
async def fetch_incidents(bbox: Optional[str] = None) -> JSONResponse:
    """
    Fetch traffic incidents for a given map viewport (bounding box).

    This endpoint queries the Google Maps Directions API for all routes that
    intersect with the viewport and returns traffic conditions as incidents.

    Query Parameters:
        bbox: Bounding box in format "min_lng,min_lat,max_lng,max_lat"
              Example: "-0.5,51.4,0.5,51.6" for London area

    Returns:
        JSON response with structure:
        {
            "incidents": [
                {
                    "event": "Heavy congestion",
                    "description": "Route description with destination",
                    "type": "heavy",
                    "coordinates": [lng, lat],
                    "lat": lat,
                    "lng": lng,
                    "duration_normal": seconds,
                    "duration_traffic": seconds
                },
                ...
            ]
        }

    Raises:
        HTTPException 400: Missing or invalid bbox parameter
        HTTPException 500: Missing API key or API errors

    Learning objectives:
    - Async functions and httpx for concurrent requests
    - Error handling with try-except
    - Data transformation and validation
    - Logging for debugging
    """
    # Validate: bbox parameter provided
    if not bbox:
        logger.warning("API call missing bbox parameter")
        raise HTTPException(
            status_code=400,
            detail='Missing bbox query parameter. Format: "min_lng,min_lat,max_lng,max_lat"'
        )

    # Validate: API key configured
    if not GOOGLE_MAPS_API_KEY:
        logger.error("GOOGLE_MAPS_API_KEY not set on server")
        raise HTTPException(
            status_code=500,
            detail='Server not configured with GOOGLE_MAPS_API_KEY'
        )

    # Parse bbox string to coordinates
    try:
        min_lng, min_lat, max_lng, max_lat = [float(x) for x in bbox.split(',')]
        logger.debug(f"Fetching incidents for bbox: {min_lng},{min_lat},{max_lng},{max_lat}")
    except (ValueError, IndexError):
        logger.warning(f"Invalid bbox format: {bbox}")
        raise HTTPException(
            status_code=400,
            detail='Invalid bbox format. Use: "min_lng,min_lat,max_lng,max_lat" with comma-separated numbers'
        )

    # Check cache (learning: optimization with caching)
    # Hash the bbox to create a cache key
    cache_key = hashlib.md5(bbox.encode()).hexdigest()
    cached_incidents = incidents_cache.get(cache_key)
    if cached_incidents is not None:
        logger.info(f"✓ Cache HIT for bbox {bbox}. Returning {len(cached_incidents)} cached incidents")
        return JSONResponse(content={'incidents': cached_incidents, 'cached': True})

    incidents_list: List[Dict] = []

    # Query Google Maps for each route in viewport
    async with httpx.AsyncClient(timeout=GOOGLE_MAPS_TOTAL_TIMEOUT) as client:
        for origin_lat, origin_lng, dest_lat, dest_lng, route_name in HYDERABAD_ROUTES:
            # Filter: only query routes within bounding box (optimization)
            if not is_route_in_bbox(
                origin_lat, origin_lng, dest_lat, dest_lng,
                min_lat, min_lng, max_lat, max_lng,
                tolerance=BBOX_TOLERANCE
            ):
                continue

            # Calculate route center point (for display)
            route_center_lng = (origin_lng + dest_lng) / 2
            route_center_lat = (origin_lat + dest_lat) / 2

            try:
                # Query Google Maps Directions API
                url = (
                    f"https://maps.googleapis.com/maps/api/directions/json?"
                    f"origin={origin_lat},{origin_lng}"
                    f"&destination={dest_lat},{dest_lng}"
                    f"&departure_time=now"
                    f"&traffic_model=best_guess"
                    f"&key={GOOGLE_MAPS_API_KEY}"
                )

                logger.debug(f"Querying route: {route_name}")
                resp = await client.get(url, timeout=GOOGLE_MAPS_API_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()

                # Parse response and extract travel time data
                if data.get('status') == 'OK' and data.get('routes'):
                    route = data['routes'][0]
                    leg = route['legs'][0]

                    duration = leg.get('duration', {}).get('value', 0)
                    duration_in_traffic = leg.get('duration_in_traffic', {}).get('value', 0)

                    # Calculate congestion using utility function
                    congestion = calculate_congestion(duration_in_traffic, duration)

                    # Create incident object for frontend
                    incident = {
                        'event': congestion['event_type'],
                        'description': f"{route_name}: {leg.get('end_address', 'Route')}",
                        'type': congestion['severity'],
                        'coordinates': [route_center_lng, route_center_lat],
                        'lat': route_center_lat,
                        'lng': route_center_lng,
                        'duration_normal': duration,
                        'duration_traffic': duration_in_traffic,
                        'delay_ratio': round(congestion['delay_ratio'], 2)
                    }
                    incidents_list.append(incident)
                    logger.debug(f"✓ {route_name}: {congestion['event_type']} (ratio: {congestion['delay_ratio']:.2f}x)")

            except httpx.TimeoutException:
                logger.warning(f"Timeout querying route {route_name}")
                continue
            except httpx.RequestError as e:
                logger.warning(f"Network error on route {route_name}: {e}")
                continue
            except KeyError as e:
                logger.warning(f"Unexpected API response for {route_name}: missing key {e}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error on route {route_name}: {e}")
                continue

    logger.info(f"Returned {len(incidents_list)} incidents from {len(HYDERABAD_ROUTES)} routes")

    # Cache the result (learning: optimization with caching)
    incidents_cache.set(cache_key, incidents_list, ttl_seconds=30)
    logger.info(f"✓ Cached {len(incidents_list)} incidents for bbox {bbox}")

    return JSONResponse(content={'incidents': incidents_list, 'cached': False})


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown for monitoring."""
    logger.info("Shutting down Hyderabad Traffic Dashboard")


if __name__ == '__main__':
    """Run the development server."""
    import uvicorn
    import os

    uvicorn.run(
        'server.main:app',
        host='0.0.0.0',
        port=PORT,
        reload=True,
        log_level="info"
    )
