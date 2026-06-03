/*
 * ============================================================
 * HYDERABAD TRAFFIC DASHBOARD — app.js
 * ============================================================
 *
 * HOW THE DATA FLOWS (Python → Browser):
 *   1. Map loads → we call /api/incidents?bbox=…
 *   2. Python (server/main.py) receives the request
 *   3. Python queries Google Maps for each route in the bbox
 *   4. Python's utils.py calculates the congestion level
 *   5. Python returns JSON: { incidents: [...], cached: bool }
 *   6. We draw coloured markers + update the sidebar
 *
 * KEY JAVASCRIPT CONCEPTS USED HERE:
 *   async/await   – wait for server replies without freezing the page
 *   fetch()       – call an API endpoint
 *   DOM methods   – getElementById, createElement, addEventListener
 *   Arrow fns     – (x) => expression
 *   Array methods – .filter(), .forEach(), .slice()
 * ============================================================
 */

// ── Config ────────────────────────────────────────────────

const REFRESH_MS = 30_000; // auto-refresh every 30 seconds

// Coordinates for the "Jump to area" dropdown [lng, lat]
const ZONES = {
  hyderabad:  { center: [78.4867, 17.3850], zoom: 12 },
  hitech:     { center: [78.3794, 17.4454], zoom: 13 },
  banjara:    { center: [78.4237, 17.4175], zoom: 13 },
  kukatpally: { center: [78.4202, 17.4479], zoom: 13 },
  gachibowli: { center: [78.4010, 17.4404], zoom: 13 },
};

// Dot colours for each incident severity (matches CSS badge classes)
const COLORS = {
  accident:   '#ef4444',
  congestion: '#f97316',
  slowdown:   '#eab308',
  other:      '#3b82f6',
};

// CSS class for the status pill based on traffic level
const LEVEL_PILL = {
  Light:    'pill-light',
  Moderate: 'pill-moderate',
  Heavy:    'pill-heavy',
  Severe:   'pill-severe',
};

// ── DOM references ─────────────────────────────────────────

const statusPillEl  = document.getElementById('status-pill');
const statCountEl   = document.getElementById('stat-count');
const statLevelEl   = document.getElementById('stat-level');
const listEl        = document.getElementById('incident-list');
const listCountEl   = document.getElementById('list-count');
const listFooterEl  = document.getElementById('list-footer');
const lastUpdatedEl = document.getElementById('last-updated');
const zoneSelectEl  = document.getElementById('zone-select');
const autoBtnEl     = document.getElementById('btn-auto');

// ── State ──────────────────────────────────────────────────

let allIncidents  = [];     // latest array from the API
let currentFilter = 'all';  // active type filter
let mapMarkers    = [];     // Mapbox Marker objects on the map
let autoRefresh   = true;
let refreshTimer  = null;

// ── Map setup ──────────────────────────────────────────────

const token = window.MAPBOX_TOKEN;
if (!token) {
  statusPillEl.textContent = '⚠ Token missing';
  statusPillEl.className = 'pill pill-error';
  throw new Error('MAPBOX_ACCESS_TOKEN not set');
}

mapboxgl.accessToken = token;

const map = new mapboxgl.Map({
  container: 'map',
  style: 'mapbox://styles/mapbox/dark-v11',  // dark base map — matches the dark sidebar
  center: [78.4867, 17.3850],               // Hyderabad centre
  zoom: 12,
});

map.addControl(new mapboxgl.NavigationControl(), 'bottom-right');

// ── Helpers ────────────────────────────────────────────────

// Classify an incident description into one of four types
function classifyType(text = '') {
  const t = (text || '').toLowerCase();
  if (t.includes('accident') || t.includes('crash'))    return 'accident';
  if (t.includes('congestion') || t.includes('heavy'))  return 'congestion';
  if (t.includes('slow') || t.includes('slowdown'))     return 'slowdown';
  return 'other';
}

// Map incident count to a traffic level label
function toLevel(count) {
  if (count > 25) return 'Severe';
  if (count > 15) return 'Heavy';
  if (count > 8)  return 'Moderate';
  return 'Light';
}

// Get the display text from an incident object
function label(inc) {
  return inc.event || inc.description || 'Traffic incident';
}

// ── Render: markers on the map ─────────────────────────────

function clearMarkers() {
  mapMarkers.forEach(m => m.remove());
  mapMarkers = [];
}

function addMarker(inc) {
  const type  = classifyType(label(inc));
  const color = COLORS[type];
  const lng   = inc.lng ?? inc.lon;

  // Build a tiny coloured circle element
  const el = document.createElement('div');
  el.style.cssText = `
    width:12px; height:12px; border-radius:50%;
    background:${color};
    border:2px solid rgba(255,255,255,0.6);
    box-shadow: 0 0 12px ${color}88, 0 0 4px ${color};
    cursor:pointer;
  `;

  const popup = new mapboxgl.Popup({ offset: 14, closeButton: true })
    .setHTML(`
      <div class="popup-type" style="color:${color}">${type.toUpperCase()}</div>
      <div class="popup-desc">${label(inc)}</div>
      <div class="popup-coords">${inc.lat.toFixed(4)}, ${lng.toFixed(4)}</div>
    `);

  const marker = new mapboxgl.Marker(el)
    .setLngLat([lng, inc.lat])
    .setPopup(popup)
    .addTo(map);

  mapMarkers.push(marker);
}

function renderMarkers() {
  clearMarkers();
  allIncidents
    .filter(inc => currentFilter === 'all' || classifyType(label(inc)) === currentFilter)
    .forEach(addMarker);
}

// ── Render: sidebar list ───────────────────────────────────

function renderList() {
  listEl.innerHTML = '';

  const filtered = allIncidents.filter(inc =>
    currentFilter === 'all' || classifyType(label(inc)) === currentFilter
  );

  listCountEl.textContent = filtered.length;

  if (filtered.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        No incidents found<br>in this area right now.
      </div>`;
    listFooterEl.textContent = '';
    return;
  }

  filtered.slice(0, 15).forEach(inc => {
    const type  = classifyType(label(inc));
    const color = COLORS[type];
    const lng   = inc.lng ?? inc.lon;

    const card = document.createElement('div');
    card.className = 'incident-card';
    card.innerHTML = `
      <div class="incident-card-dot" style="background:${color}; box-shadow:0 0 6px ${color}88;"></div>
      <div class="incident-card-body">
        <div class="incident-card-type">${type}</div>
        <div class="incident-card-desc">${label(inc)}</div>
      </div>
    `;

    // Click → fly map to this incident
    card.addEventListener('click', () =>
      map.flyTo({ center: [lng, inc.lat], zoom: 15, essential: true })
    );

    listEl.appendChild(card);
  });

  listFooterEl.textContent = filtered.length > 15
    ? `… and ${filtered.length - 15} more incidents`
    : '';
}

// ── Render: stats + status pill ────────────────────────────

function renderStats() {
  const count = allIncidents.length;
  const level = toLevel(count);

  statCountEl.textContent = count;
  statLevelEl.textContent = level;

  statusPillEl.textContent = `${level} · ${count} incidents`;
  statusPillEl.className   = `pill ${LEVEL_PILL[level] || 'pill-light'}`;
}

// Run everything at once
function renderAll() {
  renderStats();
  renderMarkers();
  renderList();
  lastUpdatedEl.textContent = `Updated ${new Date().toLocaleTimeString()}`;
}

// ── Data fetching ──────────────────────────────────────────

/*
 * fetch() is asynchronous — it starts a network request and returns a "promise".
 * "await" pauses this function until the promise resolves (data arrives),
 * without blocking anything else in the browser.
 *
 * The bbox (bounding box) tells our Python backend which part of the map
 * is visible, so it only queries relevant routes.
 */
async function fetchIncidents() {
  statusPillEl.textContent = 'Loading…';
  statusPillEl.className   = 'pill pill-loading';

  const b    = map.getBounds();
  const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(',');

  try {
    const res  = await fetch(`/api/incidents?bbox=${encodeURIComponent(bbox)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();   // { incidents: [...], cached: bool }
    allIncidents = data.incidents || [];

    if (allIncidents.length === 0) {
      statusPillEl.textContent = 'No data — check /api/debug';
      statusPillEl.className   = 'pill pill-error';
    }

    renderAll();
  } catch (err) {
    console.error(err);
    statusPillEl.textContent = '⚠ Error';
    statusPillEl.className   = 'pill pill-error';
  }
}

// ── Auto-refresh ───────────────────────────────────────────

function startAuto() {
  stopAuto();
  refreshTimer = setInterval(fetchIncidents, REFRESH_MS);
}

function stopAuto() {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
}

// ── Event listeners ────────────────────────────────────────

document.getElementById('btn-refresh').addEventListener('click', fetchIncidents);

autoBtnEl.addEventListener('click', () => {
  autoRefresh = !autoRefresh;
  if (autoRefresh) {
    autoBtnEl.textContent = '⏱ Auto ON';
    autoBtnEl.classList.add('active');
    startAuto();
  } else {
    autoBtnEl.textContent = '⏱ Auto OFF';
    autoBtnEl.classList.remove('active');
    stopAuto();
  }
});

document.getElementById('btn-locate').addEventListener('click', () => {
  navigator.geolocation.getCurrentPosition(
    pos => map.flyTo({ center: [pos.coords.longitude, pos.coords.latitude], zoom: 14 }),
    ()  => { statusPillEl.textContent = '⚠ Location unavailable'; }
  );
});

zoneSelectEl.addEventListener('change', () => {
  const zone = ZONES[zoneSelectEl.value];
  if (!zone) return;
  map.flyTo({ center: zone.center, zoom: zone.zoom });
  zoneSelectEl.value = '';
  if (autoRefresh) fetchIncidents();
});

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.type;
    renderMarkers();
    renderList();
  });
});

// Re-fetch when the user pans or zooms to a new area
map.on('moveend', () => { if (autoRefresh) fetchIncidents(); });

// ── Boot ───────────────────────────────────────────────────
// Start fetching as soon as the map is ready.
// Fallback: if map 'load' doesn't fire within 4 seconds, boot anyway.

let booted = false;

function boot() {
  if (booted) return;
  booted = true;
  fetchIncidents();
  startAuto();
}

map.on('load', boot);
setTimeout(boot, 4000);
