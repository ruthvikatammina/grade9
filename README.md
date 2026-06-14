# CyberRoute — Hyderabad IT Corridor Traffic

Live traffic dashboard for the Cyberabad commute corridor. Shows real-time travel times across 20 routes connecting HITEC City, Financial District (Nanakramguda), and surrounding areas — built with FastAPI, Mapbox, and Google Maps Routes API.

**Live:** https://traffic-update.onrender.com

---

## What It Does

- **Live route cards** — 20 IT-corridor routes with current travel time, delay, and congestion severity
- **Mapbox traffic layer** — colour-coded roads (green / amber / red) directly on the map
- **Direction filter** — view All / Inbound (→ HITEC City or Financial District) / Outbound
- **Best route hero** — highlights the fastest option when a direction is selected
- **Trip planner** — select any route to see ETA, delay, and leave-by time calculator
- **Favourites** — star routes; they float to the top on every refresh (saved in localStorage)
- **Trend badges** — ↑ worse / ↓ better compared to the previous refresh
- **Provider fallback** — Google Maps Routes API → TomTom Routing API per route, so data still loads if one provider has issues
- **5-minute cache** — results are cached server-side; manual refresh bypasses the cache

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, uvicorn |
| HTTP client | httpx (async) |
| Templating | Jinja2 |
| Map | Mapbox GL JS v2.15 |
| Traffic data | Google Maps Routes API (primary), TomTom Routing API (fallback) |
| Hosting | Render.com (free tier) |

---

## Project Structure

```
grade9/
├── server/
│   ├── main.py        # FastAPI app — endpoints, fallback query logic, cache
│   ├── config.py      # 20 routes, API keys, congestion thresholds, TTL
│   ├── utils.py       # calculate_congestion(), is_route_in_bbox()
│   ├── cache.py       # In-memory TTL cache
│   └── __init__.py
│
├── templates/
│   └── index.html     # Single-page HTML (Jinja2 injects Mapbox token)
│
├── public/
│   ├── app.js         # All frontend logic — fetch, render, map, filters
│   └── styles.css     # Dark GitHub-style theme
│
├── tests/
│   └── test_main.py   # Unit tests for utils functions
│
├── requirements.txt
├── render.yaml        # Render.com deploy config
└── README.md
```

---

## How It Works

### Data flow

```
Page load
  └─► fetchWithBbox(CORRIDOR_BBOX)          ← runs immediately, no map needed
        └─► GET /api/incidents?bbox=…
              ├─ cache HIT → return cached JSON
              └─ cache MISS
                   ├─ filter 20 routes to those inside bbox
                   ├─ asyncio.gather() — query all visible routes in parallel
                   │    └─ Semaphore(5) — max 5 concurrent API calls
                   │         ├─ query_google()  → Google Maps Routes API
                   │         └─ if Google fails → query_tomtom()
                   ├─ calculate_congestion(traffic_secs, normal_secs)
                   ├─ cache result (5 min TTL, only if non-empty)
                   └─ return JSON → frontend renders cards + map markers
```

### Congestion classification

| Severity | Condition |
|----------|-----------|
| Heavy | traffic time ≥ 1.5× normal |
| Slow | traffic time ≥ 1.2× normal |
| Clear | traffic time < 1.2× normal |

### Routes covered

20 routes across the Cyberabad IT corridor:

- **Inbound to HITEC City** — from Secunderabad, Kukatpally, Ameerpet, Nampally, LB Nagar, Dilsukhnagar, Kompally, Airport
- **Inbound to Financial District** — from Secunderabad, Ameerpet, Nampally, LB Nagar, Airport
- **Between hubs** — HITEC City ↔ Financial District
- **Outbound** — HITEC City / Financial District → Nampally, Airport
- **Other** — Nampally → Banjara Hills, Gachibowli → HITEC City

---

## Local Setup

### 1. Get API keys

**Mapbox** (for the map)
1. Sign up at mapbox.com
2. Account → Tokens → copy your default public token

**Google Maps Routes API** (primary traffic data)
1. Google Cloud Console → Enable **Routes API**
2. APIs & Services → Credentials → Create API Key
3. Billing must be enabled (Routes API requires it even on free tier)

**TomTom** (optional fallback)
1. Sign up at developer.tomtom.com
2. Dashboard → Create API Key (free tier: 2,500 req/day)

### 2. Create `.env`

```bash
MAPBOX_ACCESS_TOKEN=pk.eyJ1...
GOOGLE_MAPS_API_KEY=AIza...
TOMTOM_API_KEY=...          # optional
PORT=3000
```

### 3. Install and run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn server.main:app --reload --port 3000
```

Open **http://localhost:3000**

### 4. Verify APIs are working

Visit **http://localhost:3000/api/debug** — returns status for both Google and TomTom with sample travel times.

---

## API Reference

### `GET /`
Serves the main HTML page (Mapbox token injected via Jinja2).

### `GET /health`
Returns `{"status": "ok"}` — used by Render for health checks.

### `GET /api/incidents?bbox=min_lng,min_lat,max_lng,max_lat`
Returns live traffic data for all routes within the bounding box.

**Response:**
```json
{
  "incidents": [
    {
      "description": "Nampally → HITEC City",
      "event": "Heavy congestion",
      "severity": "heavy",
      "lat": 17.4152,
      "lng": 78.4330,
      "normal_mins": 28.5,
      "traffic_mins": 44.2,
      "delay_mins": 15.7,
      "delay_ratio": 1.55
    }
  ],
  "cached": false
}
```

### `GET /api/debug`
Tests both Google and TomTom APIs with one hardcoded route. Useful for diagnosing key issues.

---

## Deployment (Render.com)

The `render.yaml` file configures the service automatically.

**Environment variables to set in Render dashboard:**

| Variable | Required | Description |
|----------|----------|-------------|
| `MAPBOX_ACCESS_TOKEN` | Yes | Mapbox public token |
| `GOOGLE_MAPS_API_KEY` | Yes | Google Routes API key |
| `TOMTOM_API_KEY` | No | Fallback if Google fails |

Render sets `PORT` automatically — do not override it.

**Deploy branch:** `claude/brave-pasteur-HXaDc`

---

## Troubleshooting

### No route cards loading
1. Visit `/api/debug` — check if Google returns `"status": "OK"`
2. If `PERMISSION_DENIED` — Routes API not enabled or billing not set up in Google Cloud
3. If `quota_exhausted` errors — add `TOMTOM_API_KEY` as a fallback
4. Hard refresh (`Ctrl+Shift+R`) to clear cached JS/CSS

### Map not showing
- Check that `MAPBOX_ACCESS_TOKEN` is set correctly in environment variables
- The Mapbox traffic layer requires a valid token — the sidebar still works without it

### Server sleeping (Render free tier)
- Render free tier sleeps after 15 min of inactivity
- First load after sleep takes ~30 seconds — a "Server waking up…" message appears after 6 seconds

### Port already in use
```bash
uvicorn server.main:app --reload --port 8000
```

---

## Running Tests

```bash
pytest tests/test_main.py -v
```

---

## Made by

**Ruthvika Tammina**
