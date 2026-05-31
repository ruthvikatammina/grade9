# Hyderabad Traffic Dashboard

A real-time traffic monitoring web application for Hyderabad, India. Features live incident tracking, traffic level indicators, and meaningful visualizations using Mapbox and HERE Traffic APIs.

## ✨ Features

- **Live Traffic Map**: Interactive Mapbox visualization of Hyderabad
- **Real-time Incidents**: Automatic updates every 30 seconds
- **Color-coded Markers**:
  - 🔴 Red: Accidents & Collisions
  - 🟠 Orange: Heavy Congestion
  - 🟡 Yellow: Slowdowns
  - 🔵 Blue: Other incidents
- **Traffic Statistics**: Total incidents and traffic level display
- **Auto-refresh**: Enable/disable 30-second automatic updates
- **Responsive UI**: Dashboard with incident list and statistics

## 🚀 Quick Start

### 1. Get API Keys

#### Mapbox Access Token
1. Visit [mapbox.com](https://www.mapbox.com)
2. Sign up for a free account
3. Go to Account → Tokens
4. Create a new token (make sure it has appropriate scopes)
5. Copy the token

#### HERE API Key
1. Visit [developer.here.com](https://developer.here.com)
2. Sign up for a free account
3. Go to REST API → Create API Key
4. Copy the API key

### 2. Setup Environment

Create a `.env` file in the `server/` directory:

```bash
cat > server/.env << EOF
MAPBOX_ACCESS_TOKEN=your_mapbox_token_here
HERE_API_KEY=your_here_api_key_here
PORT=3000
EOF
```

Replace `your_mapbox_token_here` and `your_here_api_key_here` with your actual keys.

### 3. Install Dependencies

**Python (Recommended):**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Or Node.js:**
```bash
npm install
```

### 4. Run the Server

**Python (FastAPI):**
```bash
uvicorn server.main:app --reload --host 0.0.0.0 --port 3000
```

Or use npm helper:
```bash
npm run pydev
```

**Node.js (Express):**
```bash
npm run dev
```

### 5. Open in Browser

Navigate to: **http://localhost:3000**

## 📊 How It Works

1. **Frontend** (Mapbox GL JS):
   - Displays an interactive map centered on Hyderabad
   - Shows traffic incidents as colored markers
   - Auto-refreshes every 30 seconds

2. **Backend** (Python FastAPI or Node.js Express):
   - Proxies requests to HERE Traffic API
   - Returns incidents based on viewport bounding box
   - Handles authentication with API keys

3. **Data Flow**:
   ```
   Frontend → Backend → HERE Traffic API
                    ↓
              Incident Data
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
