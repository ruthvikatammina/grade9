/*
 * ============================================================
 * HYDERABAD TRAFFIC DASHBOARD — app.js
 * ============================================================
 *
 * WHAT THIS FILE DOES:
 *   1. Initialises the Mapbox map
 *   2. Fetches traffic incidents from our Python backend (/api/incidents)
 *   3. Draws coloured markers on the map
 *   4. Updates the sidebar (stats, list, filter)
 *   5. Auto-refreshes every 30 seconds
 *
 * HOW THE DATA FLOWS:
 *   Browser → fetch("/api/incidents?bbox=…")
 *          → Python (server/main.py)
 *          → Google Maps API
 *          → Python calculates congestion (server/utils.py)
 *          → Returns JSON list of incidents
 *          → We draw markers + update UI
 *
 * KEY CONCEPTS USED:
 *   - async / await  : waiting for server responses without freezing
 *   - fetch()        : built-in browser function to call APIs
 *   - DOM methods    : getElementById, createElement, innerHTML, etc.
 *   - addEventListener: reacting to clicks, map moves, etc.
 *   - Arrow functions: (x) => { ... }
 * ============================================================
 */

// ── 1. CONFIGURATION ──────────────────────────────────────────────────────────

// How often (ms) to auto-refresh. 30 000 ms = 30 seconds.
const REFRESH_INTERVAL_MS = 30_000;

// The Mapbox token was injected by our Python template (templates/index.html).
// Python's Jinja2 did:  window.MAPBOX_TOKEN = "{{ mapboxToken }}"
const MAPBOX_TOKEN = window.MAPBOX_TOKEN;

// Jump-to coordinates for each named area (longitude first — that's Mapbox's format)
const ZONES = {
  hyderabad:  { center: [78.4867, 17.3850], zoom: 12 },
  hitech:     { center: [78.3794, 17.4454], zoom: 13 },
  banjara:    { center: [78.4237, 17.4175], zoom: 13 },
  kukatpally: { center: [78.4202, 17.4479], zoom: 13 },
  gachibowli: { center: [78.4010, 17.4404], zoom: 13 },
};

// Colour for each incident type (matches the CSS .dot classes)
const TYPE_COLORS = {
  accident:   '#dc2626',  // red
  congestion: '#ea580c',  // orange
  slowdown:   '#d97706',  // amber
  other:      '#2563eb',  // blue
};


// ── 2. GRAB DOM ELEMENTS ──────────────────────────────────────────────────────
// We cache these once so we don't search the DOM every time we update them.

const statusEl      = document.getElementById('status');        // top-right status pill
const statCountEl   = document.getElementById('stat-count');    // "Incidents" number
const statLevelEl   = document.getElementById('stat-level');    // "Traffic now" text
const listEl        = document.getElementById('incident-list'); // scrollable card list
const listCountEl   = document.getElementById('list-count');    // small count next to "Incidents"
const listFooterEl  = document.getElementById('list-footer');   // "…and X more"
const lastUpdatedEl = document.getElementById('last-updated');  // bottom timestamp
const zoneSelectEl  = document.getElementById('zone-select');   // area dropdown
const autoBtnEl     = document.getElementById('btn-auto');      // Auto-refresh toggle


// ── 3. STATE VARIABLES ────────────────────────────────────────────────────────
// These variables remember the current state of the app.

let allIncidents  = [];      // Latest array of incidents from the API
let currentFilter = 'all';   // Which type to show: 'all' | 'congestion' | 'slowdown' | 'accident'
let mapMarkers    = [];       // Mapbox Marker objects currently on the map
let autoRefresh   = true;     // Is auto-refresh currently on?
let refreshTimer  = null;     // The setInterval timer ID (so we can cancel it)


// ── 4. INITIALISE MAPBOX MAP ──────────────────────────────────────────────────

if (!MAPBOX_TOKEN) {
  // No token → show an error and stop
  document.getElementById('status').textContent = '⚠ MAPBOX_ACCESS_TOKEN missing';
  throw new Error('MAPBOX_ACCESS_TOKEN not set');
}

mapboxgl.accessToken = MAPBOX_TOKEN;

const map = new mapboxgl.Map({
  container: 'map',                              // <div id="map"> in the HTML
  style: 'mapbox://styles/mapbox/traffic-day-v2',// Mapbox's built-in traffic style
  center: [78.4867, 17.3850],                    // Hyderabad city centre [lng, lat]
  zoom: 12,
});

// Add zoom controls (+/-) in the bottom-right corner
map.addControl(new mapboxgl.NavigationControl(), 'bottom-right');


// ── 5. HELPER FUNCTIONS ───────────────────────────────────────────────────────

/**
 * Work out the incident type from its text description.
 * Returns one of: 'accident' | 'congestion' | 'slowdown' | 'other'
 *
 * LEARNING: .toLowerCase() normalises the text so "HEAVY" and "heavy" both match.
 */
function classifyType(text = '') {
  const t = text.toLowerCase();
  if (t.includes('accident') || t.includes('crash'))           return 'accident';
  if (t.includes('congestion') || t.includes('heavy'))         return 'congestion';
  if (t.includes('slow') || t.includes('slowdown'))            return 'slowdown';
  return 'other';
}

/**
 * Turn an incident count into a human-friendly traffic level string.
 *
 * LEARNING: This is a simple "bucketing" function — common in data processing.
 */
function trafficLevel(count) {
  if (count > 25) return 'Severe';
  if (count > 15) return 'Heavy';
  if (count > 8)  return 'Moderate';
  return 'Light';
}

/**
 * Extract the display text from a raw incident object.
 * The API can return the description in different field names,
 * so we check them in priority order.
 */
function incidentLabel(incident) {
  return incident.event || incident.description || 'Traffic incident';
}

/**
 * Remove every marker currently shown on the map.
 *
 * LEARNING: .forEach() runs a function once for each item in an array.
 */
function clearMapMarkers() {
  mapMarkers.forEach(m => m.remove());
  mapMarkers = [];
}

/**
 * Place a single coloured dot on the map for one incident.
 *
 * @param {number} lat   - latitude
 * @param {number} lon   - longitude
 * @param {string} label - human-readable description
 * @param {string} type  - 'accident' | 'congestion' | 'slowdown' | 'other'
 */
function addMapMarker(lat, lon, label, type) {
  const color = TYPE_COLORS[type] || TYPE_COLORS.other;

  // Build a custom HTML element for the dot
  const dot = document.createElement('div');
  dot.style.cssText = `
    width: 14px; height: 14px;
    background: ${color};
    border-radius: 50%;
    border: 2px solid white;
    box-shadow: 0 0 8px ${color}99;
  `;

  // Build the popup that appears when the user clicks the dot
  const popupHTML = `
    <div class="popup-type" style="color:${color}">${type.toUpperCase()}</div>
    <div class="popup-desc">${label}</div>
    <div class="popup-coords">${lat.toFixed(4)}, ${lon.toFixed(4)}</div>
  `;

  const marker = new mapboxgl.Marker(dot)
    .setLngLat([lon, lat])    // Mapbox needs [longitude, latitude] — note the order!
    .setPopup(new mapboxgl.Popup({ offset: 12 }).setHTML(popupHTML))
    .addTo(map);

  mapMarkers.push(marker);
}


// ── 6. RENDER FUNCTIONS ───────────────────────────────────────────────────────

/**
 * Redraw all markers on the map, respecting the current filter.
 *
 * LEARNING: Array.filter() returns a new array containing only items
 *           that pass the test function (returning true).
 */
function renderMarkers() {
  clearMapMarkers();

  allIncidents
    .filter(inc => {
      if (currentFilter === 'all') return true;           // show everything
      return classifyType(incidentLabel(inc)) === currentFilter;
    })
    .forEach(inc => {
      addMapMarker(
        inc.lat,
        inc.lng || inc.lon,
        incidentLabel(inc),
        classifyType(incidentLabel(inc))
      );
    });
}

/**
 * Rebuild the sidebar incident list from allIncidents.
 *
 * LEARNING: We clear the list (innerHTML = '') then append new cards.
 *           We use document.createElement() to build each card safely
 *           (avoids XSS if description text contained HTML characters).
 */
function renderList() {
  listEl.innerHTML = '';

  const filtered = allIncidents.filter(inc =>
    currentFilter === 'all' || classifyType(incidentLabel(inc)) === currentFilter
  );

  listCountEl.textContent = filtered.length > 0 ? `(${filtered.length})` : '';

  if (filtered.length === 0) {
    listEl.innerHTML = '<div class="empty-state">No incidents in this area</div>';
    listFooterEl.textContent = '';
    return;
  }

  // Show up to 15 cards; more would make the list unwieldy
  const visible = filtered.slice(0, 15);

  visible.forEach(inc => {
    const type  = classifyType(incidentLabel(inc));
    const color = TYPE_COLORS[type];
    const label = incidentLabel(inc);

    const card = document.createElement('div');
    card.className = 'incident-card';

    // Build inner HTML (the label is text-only, so no XSS risk here)
    card.innerHTML = `
      <span class="dot ${type}" style="background:${color}"></span>
      <div class="incident-card-text">
        <div class="incident-type">${type}</div>
        <div class="incident-desc">${label}</div>
      </div>
    `;

    // Clicking a card flies the map to that location
    card.addEventListener('click', () => {
      map.flyTo({ center: [inc.lng || inc.lon, inc.lat], zoom: 15, essential: true });
    });

    listEl.appendChild(card);
  });

  // Footer: "… and X more" if there are more than 15
  if (filtered.length > 15) {
    listFooterEl.textContent = `… and ${filtered.length - 15} more`;
  } else {
    listFooterEl.textContent = '';
  }
}

/**
 * Update the stats section (count + traffic level).
 */
function renderStats() {
  const count = allIncidents.length;
  const level = trafficLevel(count);

  statCountEl.textContent = count;
  statLevelEl.textContent = level;

  // Also update the header status pill
  statusEl.textContent = `${level} traffic · ${count} incidents`;
}

/**
 * Convenience: run all render functions together.
 */
function renderAll() {
  renderStats();
  renderMarkers();
  renderList();
  lastUpdatedEl.textContent = `Updated ${new Date().toLocaleTimeString()}`;
}


// ── 7. DATA FETCHING ──────────────────────────────────────────────────────────

/**
 * Fetch incidents from our Python backend and refresh the UI.
 *
 * LEARNING: async/await lets us write asynchronous code that reads like
 *           synchronous code. "await" pauses this function until the
 *           promise resolves, without freezing the browser.
 *
 * The URL we call:  /api/incidents?bbox=minLng,minLat,maxLng,maxLat
 * The backend uses the bbox to only return routes visible on screen.
 */
async function fetchIncidents() {
  statusEl.textContent = 'Loading…';

  // Get the current map viewport as a bounding box
  const b = map.getBounds();
  const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(',');

  try {
    // Call our Python API
    const response = await fetch(`/api/incidents?bbox=${encodeURIComponent(bbox)}`);

    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status}`);
    }

    // Parse the JSON body (also async — the body may still be downloading)
    const data = await response.json();

    // The Python API returns: { incidents: [...], cached: true/false }
    allIncidents = data.incidents || [];

    renderAll();
  } catch (err) {
    console.error('fetchIncidents error:', err);
    statusEl.textContent = '⚠ Could not load incidents';
  }
}


// ── 8. AUTO-REFRESH ───────────────────────────────────────────────────────────

function startAutoRefresh() {
  stopAutoRefresh(); // cancel any existing timer first
  refreshTimer = setInterval(fetchIncidents, REFRESH_INTERVAL_MS);
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}


// ── 9. EVENT LISTENERS ────────────────────────────────────────────────────────

// Refresh button → immediately fetch new data
document.getElementById('btn-refresh').addEventListener('click', fetchIncidents);

// Auto-refresh toggle
autoBtnEl.addEventListener('click', () => {
  autoRefresh = !autoRefresh;

  if (autoRefresh) {
    autoBtnEl.textContent = '⏱ Auto: ON';
    autoBtnEl.classList.add('active');
    startAutoRefresh();
  } else {
    autoBtnEl.textContent = '⏱ Auto: OFF';
    autoBtnEl.classList.remove('active');
    stopAutoRefresh();
  }
});

// "My location" button — uses the browser's Geolocation API
document.getElementById('btn-locate').addEventListener('click', () => {
  navigator.geolocation.getCurrentPosition(
    pos => {
      // Success: fly the map to the user's coordinates
      map.flyTo({ center: [pos.coords.longitude, pos.coords.latitude], zoom: 14 });
    },
    () => {
      statusEl.textContent = '⚠ Location unavailable';
    }
  );
});

// Zone dropdown → fly to the selected area
zoneSelectEl.addEventListener('change', () => {
  const zone = ZONES[zoneSelectEl.value];
  if (!zone) return;
  map.flyTo({ center: zone.center, zoom: zone.zoom });
  zoneSelectEl.value = ''; // reset so user can pick same option again
});

// Filter buttons → update currentFilter and re-render
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    // Remove 'active' from all filter buttons
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    // Add 'active' to the clicked one
    btn.classList.add('active');

    currentFilter = btn.dataset.type; // read the data-type="…" attribute
    renderMarkers();
    renderList();
  });
});

// When the user pans or zooms the map, refresh incidents for the new viewport
map.on('moveend', () => {
  if (autoRefresh) fetchIncidents();
});


// ── 10. START THE APP ─────────────────────────────────────────────────────────

// Wait for the map tiles to load, then fetch the first batch of incidents
map.on('load', () => {
  fetchIncidents();
  startAutoRefresh();
});
