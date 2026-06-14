# CyberRoute — Features Roadmap

What's built, what's next.

---

## Currently Live

| Feature | Status | Notes |
|---------|--------|-------|
| 20 IT-corridor routes | ✅ | HITEC City + Financial District hubs |
| Google Maps Routes API | ✅ | Primary data source |
| TomTom fallback | ✅ | Per-route fallback if Google fails |
| Mapbox traffic layer | ✅ | Green/amber/red roads always visible |
| Direction filter | ✅ | All / Inbound / Outbound |
| Best route hero card | ✅ | Fastest route highlighted when filtered |
| Trip planner | ✅ | Select route → ETA + delay breakdown |
| Leave-by calculator | ✅ | "Need to arrive by X → leave at Y" |
| Favourite routes | ✅ | Starred routes float to top, saved in localStorage |
| Trend badges | ✅ | ↑ worse / ↓ better vs previous refresh |
| 5-minute server cache | ✅ | Avoids hammering Google on every map pan |
| WhatsApp share | ✅ | Share route status with one tap |
| Locate me | ✅ | Pan map to current location |
| Server wake-up banner | ✅ | Shows after 6s if Render is cold-starting |

---

## Potential Next Features

### Easy (a few hours each)

**Push notifications**
- Browser Notification API alert when a starred route goes heavy
- Files: `public/app.js`

**Time-of-day label**
- Show "Morning rush", "Evening rush", "Off-peak" banner based on IST time
- Purely frontend — no API call needed

**Route share card**
- Generate a shareable image (canvas) with the route summary
- Files: `public/app.js`

---

### Medium (1–3 days)

**Historical trends chart**
- Store each refresh result in SQLite
- Show a 24-hour sparkline per route (best time to travel)
- Files to add: `server/database.py`, `server/models.py`

**Alternate route suggestions**
- When a route is heavy, suggest a nearby lighter route
- Purely frontend using existing data

**More corridors**
- Add ORR (Outer Ring Road) routes
- Add Old City / Charminar area routes
- Files: `server/config.py` (just add tuples to `HYDERABAD_ROUTES`)

---

### Advanced (3–7 days)

**PWA (Progressive Web App)**
- Add `manifest.json` + service worker
- Users can install on phone home screen
- Offline cache shows last-known data

**WebSocket live updates**
- Replace poll-on-refresh with a WebSocket push
- Server pushes new data every 5 minutes automatically
- Files to add: WebSocket endpoint in `server/main.py`

**Traffic pattern ML**
- Train a model on historical data to predict congestion 1–2 hours ahead
- Show "Expected to worsen by 6 PM" label on route cards
- Files to add: `server/predictor.py`

---

## Known Limitations

| Limitation | Workaround |
|------------|-----------|
| Render free tier sleeps after 15 min inactivity | Wake-up banner; first load is slow |
| Google Routes API requires billing enabled | TomTom fallback covers this |
| No auto-refresh (removed by design) | Manual ↻ Refresh button |
| Routes are fixed corridors, not arbitrary origin→destination | Trip planner covers the 20 pre-defined routes |
| Cache is in-memory, resets on server restart | Acceptable — Render restarts are rare |
