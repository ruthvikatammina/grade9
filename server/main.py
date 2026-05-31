import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
from dotenv import load_dotenv

load_dotenv()

HERE_API_KEY = os.getenv('HERE_API_KEY')
MAPBOX_TOKEN = os.getenv('MAPBOX_ACCESS_TOKEN')

app = FastAPI(title="Hyderabad Traffic MVP")

# Serve the frontend static files under /static and provide root template
app.mount("/static", StaticFiles(directory="public"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get('/')
async def root_index(request: Request):
    return templates.TemplateResponse('index.html', {"request": request, "mapboxToken": MAPBOX_TOKEN})


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
