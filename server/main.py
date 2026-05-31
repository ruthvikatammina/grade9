import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx
from dotenv import load_dotenv
import logging
from jinja2 import Environment, FileSystemLoader

load_dotenv()

HERE_API_KEY = os.getenv('HERE_API_KEY')
MAPBOX_TOKEN = os.getenv('MAPBOX_ACCESS_TOKEN')

app = FastAPI(title="Hyderabad Traffic MVP")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hyderabad-traffic")

# Serve the frontend static files under /static and provide root template
app.mount("/static", StaticFiles(directory="public"), name="static")
# Use Jinja2 Environment directly to avoid starlette cache issue on some Jinja versions
templates_env = Environment(loader=FileSystemLoader('templates'))


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Hyderabad Traffic app")
    logger.info("MAPBOX_ACCESS_TOKEN set: %s", bool(MAPBOX_TOKEN))
    logger.info("HERE_API_KEY set: %s", bool(HERE_API_KEY))


@app.get('/')
async def root_index(request: Request):
    tmpl = templates_env.get_template('index.html')
    content = tmpl.render(mapboxToken=MAPBOX_TOKEN)
    return HTMLResponse(content=content)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get('/config')
async def config():
    return {"mapboxToken": MAPBOX_TOKEN}


@app.get('/api/incidents')
async def incidents(bbox: Optional[str] = None):
    if not bbox:
        raise HTTPException(status_code=400, detail='missing bbox query param')

    if not HERE_API_KEY:
        raise HTTPException(status_code=500, detail='HERE_API_KEY not set on server')

    try:
        min_lng, min_lat, max_lng, max_lat = [float(x) for x in bbox.split(',')]
    except Exception:
        raise HTTPException(status_code=400, detail='invalid bbox format')

    topLeftLat = max_lat
    topLeftLon = min_lng
    bottomRightLat = min_lat
    bottomRightLon = max_lng

    url = f"https://traffic.ls.hereapi.com/traffic/6.3/incidents.json?bbox={topLeftLat},{topLeftLon};{bottomRightLat},{bottomRightLon}&apiKey={HERE_API_KEY}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return JSONResponse(content=resp.json())


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('server.main:app', host='0.0.0.0', port=int(os.getenv('PORT', '3000')), reload=True)
