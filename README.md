# Hyderabad Traffic Dashboard

A real-time traffic monitoring web application for Hyderabad, India. Features live incident tracking, traffic level indicators, and meaningful visualizations using Mapbox and Google Maps APIs.

## ✨ Features

- **Live Traffic Map**: Interactive Mapbox visualization of Hyderabad
- **Real-time Traffic Data**: Automatic updates every 30 seconds via Google Maps Directions API
- **Preset Areas**: Quick jump to HITEC City, Banjara Hills, Kukatpally, Gachibowli
- **Incident Filters**: Filter by accident, congestion, slowdown, or view all
- **Traffic Statistics**: Total incidents and traffic level display
- **Location Detection**: Find traffic near your current location
- **Auto-refresh Toggle**: Enable/disable 30-second automatic updates
- **Responsive UI**: Dashboard with incident list and statistics

## 🚀 Quick Start

### 1. Get API Keys

#### Mapbox Access Token
1. Visit [mapbox.com](https://www.mapbox.com)
2. Sign up for a free account
3. Go to Account → Tokens
4. Create a new token (make sure it has appropriate scopes)
5. Copy the token

#### Google Maps API Key
1. Visit [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable the **Maps JavaScript API** and **Directions API**
4. Go to Credentials → Create API Key
5. Copy the key
6. (Optional) Restrict it to your domain for security

### 2. Setup Environment

Create a `.env` file in the `server/` directory:

```bash
cat > server/.env << EOF
MAPBOX_ACCESS_TOKEN=your_mapbox_token_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
PORT=3000
EOF
```

Replace the tokens with your actual keys.

### 3. Install Dependencies

**Python (Recommended):**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run the Server

**Python (FastAPI):**
```bash
uvicorn server.main:app --reload --host 0.0.0.0 --port 3000
```

### 5. Open in Browser

Navigate to: **http://localhost:3000**

## 📊 How It Works

**Architecture Overview (Learning Guide for Grade 9)**

This project demonstrates real-world web development concepts:

### 1. **Frontend** (HTML/CSS/JavaScript in `templates/index.html`)
   - User interacts with the dashboard
   - Fetches traffic data from our backend API
   - Uses Mapbox to display incidents on an interactive map
   - Handles all UI interactions (filtering, zone selection, auto-refresh)

### 2. **Backend API** (Python FastAPI in `server/main.py`)
   - Receives requests from frontend with map bounds
   - Queries Google Maps Directions API for traffic conditions
   - Processes data to calculate congestion levels
   - Returns incidents as JSON for frontend to display

### 3. **Data Processing** (Python modules)
   - `config.py`: Centralized configuration (routes, API keys, thresholds)
   - `utils.py`: Pure functions for calculating congestion and filtering routes
   - `cache.py`: Simple caching to reduce API calls (performance optimization)

### 4. **Data Flow**
   ```
   User opens map
        ↓
   Frontend fetches current map bounds
        ↓
   Backend checks cache first (TTL 30 seconds)
        ↓
   If not cached: Query Google Maps API for 6 routes in the bounds
        ↓
   Process API response: Calculate congestion ratios
        ↓
   Cache results + return JSON to frontend
        ↓
   Frontend displays markers and statistics
   ```

### 5. **Key Python Concepts Demonstrated**

| Concept | Where Used | Learning Value |
|---------|-----------|-----------------|
| **Functions** | `utils.calculate_congestion()`, `utils.is_route_in_bbox()` | Breaking code into reusable pieces |
| **Type Hints** | Function parameters and returns | Making code self-documenting |
| **Error Handling** | try-except blocks in API calls | Gracefully handling failures |
| **Logging** | `logger.info()`, `logger.warning()` | Debugging production issues |
| **Data Structures** | Dictionaries, lists for incident data | Organizing complex data |
| **Configuration Management** | `config.py` module | Separating config from code |
| **Caching** | `cache.py` with TTL | Optimization and performance |
| **Unit Testing** | `tests/test_main.py` with pytest | Ensuring code reliability |

---

## 🧪 Testing Your Code

Before deploying, always test locally!

### Run Unit Tests (Testing individual functions)
```bash
# Install dependencies if not already done
pip install -r requirements.txt

# Run all tests
pytest tests/test_main.py -v

# Expected output:
# test_calculate_congestion.py::TestCalculateCongestion::test_heavy_congestion PASSED
# test_calculate_congestion.py::TestCalculateCongestion::test_zero_duration PASSED
# ... (more tests) ...
```

### Run the Server Locally
```bash
# Activate virtual environment
source .venv/bin/activate

# Start server
uvicorn server.main:app --reload --host 0.0.0.0 --port 3000

# Server logs (learning: reading logs to understand what's happening):
# INFO:     Uvicorn running on http://0.0.0.0:3000
# INFO:     Starting Hyderabad Traffic Dashboard
# INFO:     MAPBOX_ACCESS_TOKEN is set: True
# INFO:     GOOGLE_MAPS_API_KEY is set: True
```

### Test in Browser
1. Open http://localhost:3000
2. Click "Refresh" button → incidents should load
3. Pan/zoom the map → new areas should fetch incidents
4. Click an incident → should pan to that location
5. Toggle "Auto: ON/OFF" → auto-refresh should start/stop
6. Select an area → map should jump to that zone
7. Filter by incident type → markers should update

---

## 📁 Project Structure (Code Organization)

```
grade9/
├── server/
│   ├── main.py           # FastAPI app and route handlers
│   ├── config.py         # Constants and environment variables
│   ├── utils.py          # Pure utility functions
│   ├── cache.py          # Simple caching with TTL
│   ├── __init__.py       # Makes 'server' a Python package
│   └── .env              # (Not committed) API keys
│
├── templates/
│   └── index.html        # Jinja2 template with Mapbox + JavaScript
│
├── public/
│   ├── styles.css        # CSS styling
│   └── app.js            # (Legacy) static JavaScript
│
├── tests/
│   ├── test_main.py      # Unit tests for functions
│   └── __init__.py
│
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── render.yaml           # Deployment config for Render.com
```

### What Each File Does

| File | Purpose | Learning Focus |
|------|---------|-----------------|
| `main.py` | Defines API endpoints, handles HTTP requests | REST APIs, async/await |
| `config.py` | Centralized constants (routes, API URLs, thresholds) | Configuration management |
| `utils.py` | Pure functions for calculations and filtering | Functional programming, pure functions |
| `cache.py` | Simple key-value cache with TTL | Data structures, optimization |
| `test_main.py` | Tests for `utils.py` functions | Unit testing with pytest |
| `index.html` | User interface, fetches from API | Frontend-backend communication |

---

## 🐛 Common Issues & Solutions

### "GOOGLE_MAPS_API_KEY not set"
```
Solution: Add to server/.env file (don't commit it!)
GOOGLE_MAPS_API_KEY=your_actual_key_here
```

### "No incidents loading"
1. Check browser console (F12 → Console tab) for errors
2. Check server logs for API errors
3. Verify API keys are still valid (quota remaining?)
4. Try zooming into Hyderabad: [78.4867, 17.3850]

### "Port 3000 already in use"
```bash
# Use a different port
uvicorn server.main:app --reload --port 8000
# Then visit http://localhost:8000
```

### Tests Failing?
```bash
# Run with verbose output to see what failed
pytest tests/test_main.py -v

# Run specific test
pytest tests/test_main.py::TestCalculateCongestion::test_heavy_congestion -v
```

---

## 📚 Learning Resources

### Python Concepts Used
- **Functions & Modules**: [Real Python - Functions](https://realpython.com/defining-your-own-python-function/)
- **Async/Await**: [Real Python - Async IO](https://realpython.com/async-io-python/)
- **Type Hints**: [Real Python - Type Hints](https://realpython.com/python-type-checking/)
- **Logging**: [Python Docs - Logging](https://docs.python.org/3/library/logging.html)
- **Testing with pytest**: [Pytest.org](https://docs.pytest.org/)

### Web Development
- **REST APIs**: [What is REST? - MDN](https://developer.mozilla.org/en-US/docs/Glossary/REST)
- **FastAPI**: [FastAPI Documentation](https://fastapi.tiangolo.com/)
- **HTTP Status Codes**: [MDN - HTTP Status](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)

### APIs Used
- **Google Maps Directions API**: [Official Docs](https://developers.google.com/maps/documentation/directions)
- **Mapbox GL JS**: [Official Docs](https://docs.mapbox.com/mapbox-gl-js/)

---

## 🔄 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ templates/index.html (Frontend)                           │  │
│  │ ┌────────────────────────────────────────────────────┐   │  │
│  │ │ 1. User opens map or pans/zooms                    │   │  │
│  │ │ 2. Get current bounds: [lng_min, lat_min, ...]    │   │  │
│  │ │ 3. fetch(/api/incidents?bbox=...)                 │   │  │
│  │ └────────────────────────────────────────────────────┘   │  │
│  └─────────────────────┬──────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ HTTP GET /api/incidents
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│                        PYTHON BACKEND                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ server/main.py: fetch_incidents()                        │  │
│  │ ┌────────────────────────────────────────────────────┐   │  │
│  │ │ 1. Validate bbox parameter                        │   │  │
│  │ │ 2. Check cache.get(bbox_hash)  ← cache.py       │   │  │
│  │ │    If HIT: Return cached incidents                │   │  │
│  │ │    If MISS: Continue to step 3                    │   │  │
│  │ │ 3. For each route in config.HYDERABAD_ROUTES:    │   │  │
│  │ │    - Check if route overlaps bbox (utils.py)     │   │  │
│  │ │    - Query Google Maps API with route coords     │   │  │
│  │ │ 4. Process response:                              │   │  │
│  │ │    - Extract duration vs duration_in_traffic     │   │  │
│  │ │    - Calculate congestion (utils.calculate_...)  │   │  │
│  │ │    - Format as incident object                   │   │  │
│  │ │ 5. Cache result (cache.set())                     │   │  │
│  │ │ 6. Return JSON response                           │   │  │
│  │ └────────────────────────────────────────────────────┘   │  │
│  └─────────────────────┬──────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ JSON Response
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│                      BACK TO BROWSER                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Frontend processes JSON:                                 │  │
│  │ 1. Parse incidents array                                │  │
│  │ 2. Clear old markers                                    │  │
│  │ 3. For each incident:                                  │  │
│  │    - Create Mapbox marker with incident icon/color    │  │
│  │    - Add to map                                        │  │
│  │ 4. Update statistics (count, traffic level)            │  │
│  │ 5. Build incident list HTML                           │  │
│  │ 6. Render to user!                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Next Steps for Learning

### Try These Modifications:
1. **Add more routes** - Edit `config.py` HYDERABAD_ROUTES
2. **Change congestion thresholds** - Modify `config.CONGESTION_THRESHOLDS`
3. **Write a new test** - Add a test case to `tests/test_main.py`
4. **Add logging statements** - Use `logger.info()` to track what's happening
5. **Implement new endpoints** - Add more API routes to `server/main.py`

### Understanding the Code:
- Read `server/utils.py` → Pure functions with docstrings
- Read `server/cache.py` → Simple data structures in action
- Read `tests/test_main.py` → How to verify your code works
- Read JavaScript comments in `templates/index.html` → Frontend-backend communication

---

## 📝 How It Works

1. **Frontend** (Mapbox GL JS):
   - Displays an interactive map centered on Hyderabad
   - Shows traffic conditions as markers on major routes
   - Auto-refreshes every 30 seconds
   - Supports filtering and area selection

2. **Backend** (Python FastAPI):
   - Queries Google Maps Directions API for traffic conditions
   - Analyzes traffic delays across major Hyderabad routes
   - Returns traffic conditions as incident-like data
   - Handles viewport bounding box queries

3. **Data Flow**:
   ```
   Frontend → Backend → Google Maps Directions API
                    ↓
              Traffic Conditions
                    ↓
   Frontend Renders Markers & Statistics
   ```

## 🎨 UI Components

| Component | Purpose |
|-----------|---------|
| **Header** | Application title and current traffic status |
| **Controls** | Refresh button and auto-refresh toggle |
| **Statistics** | Incident count and traffic level |
| **Legend** | Color-coded incident type reference |
| **Incidents List** | Detailed list of incidents in view |
| **Map** | Interactive Mapbox display |

## 🔧 Configuration

### Adjust Auto-refresh Interval

Edit `public/app.js` line ~140:
```javascript
autoRefreshInterval = setInterval(loadIncidents, 30000); // Change 30000 to desired milliseconds
```

### Change Map Center/Zoom

Edit `public/app.js` line ~19:
```javascript
const map = new mapboxgl.Map({
  center: [78.4867, 17.3850],  // [longitude, latitude]
  zoom: 12                        // Change zoom level (1-22)
});
```

## 📦 Tech Stack

- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Mapbox GL JS
- **Backend**: Python (FastAPI) or Node.js (Express)
- **APIs**: 
  - Mapbox (map tiles and styling)
  - HERE Traffic (incident data)
- **Package Managers**: npm, pip

## 📝 Requirements

### Python
- Python 3.7+
- FastAPI >= 0.95.0
- uvicorn >= 0.22.0
- httpx >= 0.24.0
- python-dotenv >= 1.0.0

### Node.js
- Node.js 14+
- Express 4.18.2
- cors 2.8.5
- dotenv 16.0.0
- node-fetch 2.6.7

## 🐛 Troubleshooting

### "MAPBOX_ACCESS_TOKEN not set"
- Check `server/.env` file exists
- Verify `MAPBOX_ACCESS_TOKEN` is set correctly
- Restart server after adding token

### "HERE_API_KEY not set"
- Add `HERE_API_KEY` to `server/.env`
- Restart server
- Try clicking "Refresh Incidents" button

### No incidents showing
- Increase map zoom (incidents may only show in specific regions)
- Check browser console (F12) for errors
- Verify API keys are valid and have quota remaining

### CORS errors
- Ensure backend is running on the same origin
- Check that CORS middleware is enabled (it is by default)

## 🚀 Deployment

### To GitHub
```bash
git add .
git commit -m "Add traffic dashboard"
git push origin main
```

### To Heroku (Python)
```bash
heroku create your-app-name
heroku config:set MAPBOX_ACCESS_TOKEN=your_token HERE_API_KEY=your_key
git push heroku main
```

### To Vercel/Netlify (Frontend only)
```bash
npm run build  # If needed
# Deploy the public/ folder as static site
```

### To Render (recommended)

You can deploy this repo to Render as a Python Web Service. I added a `render.yaml` manifest to help configure the service, but you still need to set secrets in the Render dashboard.

1. Push your repository to GitHub if you haven't already.
2. In Render, create a new "Web Service" and connect your GitHub repo (or import using `render.yaml`).
3. Use these build/start settings (the `render.yaml` already sets these):

```bash
Build command: pip install -r requirements.txt
Start command: uvicorn server.main:app --host 0.0.0.0 --port $PORT
```

4. Under Environment → Environment Variables, add:

- `MAPBOX_ACCESS_TOKEN` = your_mapbox_token
- `HERE_API_KEY` = your_here_api_key

Render exposes a `PORT` variable automatically; do not override it.

Notes:
- Don't commit your API keys into the repo; set them as Render environment variables.
- If your repo currently contains the `.venv/` folder tracked by git, push may fail due to large files. I can help remove `.venv/` from the repo history if you want — that will rewrite history and require a force-push.


## 📄 License

MIT

## 🤝 Contributing

Contributions welcome! Feel free to submit PRs for improvements.

## 📞 Support

For issues with:
- **Mapbox**: Visit [docs.mapbox.com](https://docs.mapbox.com)
- **HERE**: Visit [developer.here.com/documentation](https://developer.here.com/documentation)
- **FastAPI**: Visit [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
