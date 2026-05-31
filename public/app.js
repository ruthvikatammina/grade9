async function init() {
  const cfg = await fetch('/config').then(r => r.json());
  if (!cfg.mapboxToken) {
    document.getElementById('panel').innerText = 'MAPBOX_ACCESS_TOKEN not set on server (see server/.env)';
    return;
  }

  mapboxgl.accessToken = cfg.mapboxToken;

  const map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/traffic-day-v2',
    center: [78.4867, 17.3850],
    zoom: 12
  });

  let markers = [];
  let autoRefreshEnabled = true;
  let autoRefreshInterval = null;

  // Classify incident type by keywords
  function getIncidentType(text = '') {
    const str = (text || '').toLowerCase();
    if (str.includes('accident') || str.includes('crash') || str.includes('collision')) return 'accident';
    if (str.includes('congestion') || str.includes('heavy') || str.includes('jam')) return 'congestion';
    if (str.includes('slow') || str.includes('slowdown')) return 'slowdown';
    return 'other';
  }

  function getIncidentColor(type) {
    const colors = {
      accident: '#d32f2f',      // Red
      congestion: '#ff6f00',    // Orange
      slowdown: '#fbc02d',      // Yellow
      other: '#1976d2'          // Blue
    };
    return colors[type] || colors.other;
  }

  // Find any objects containing numeric lat/lon-like properties
  function findPoints(obj, out = []) {
    if (!obj || typeof obj !== 'object') return out;
    if (Array.isArray(obj)) {
      for (const v of obj) findPoints(v, out);
      return out;
    }

    const keys = Object.keys(obj).reduce((acc, k) => (acc[k.toLowerCase()] = obj[k], acc), {});

    const latKeys = ['lat', 'latitude', 'y'];
    const lonKeys = ['lon', 'lng', 'long', 'longitude', 'x'];

    for (const lk of latKeys) {
      for (const rk of lonKeys) {
        if (lk in keys && rk in keys) {
          const lat = Number(keys[lk]);
          const lon = Number(keys[rk]);
          if (!Number.isNaN(lat) && !Number.isNaN(lon)) {
            out.push({ lat, lon, src: obj });
          }
        }
      }
    }

    // WKT POINT: "POINT (lon lat)"
    if (typeof keys['shape'] === 'string') {
      const m = keys['shape'].match(/POINT \((-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\)/i);
      if (m) out.push({ lat: Number(m[2]), lon: Number(m[1]), src: obj });
    }

    // coordinates arrays
    if (Array.isArray(keys['coordinates']) && keys['coordinates'].length >= 2) {
      const [a, b] = keys['coordinates'];
      if (!Number.isNaN(a) && !Number.isNaN(b)) {
        out.push({ lat: Number(b), lon: Number(a), src: obj });
      }
    }

    for (const k of Object.keys(obj)) {
      findPoints(obj[k], out);
    }

    return out;
  }

  function clearMarkers() {
    for (const m of markers) m.remove();
    markers = [];
  }

  function addMarker({ lat, lon, src }, idx) {
    const eventText = src?.event || src?.description || 'Traffic incident';
    const type = getIncidentType(eventText);
    const color = getIncidentColor(type);

    const el = document.createElement('div');
    el.className = 'incident-marker';
    el.style.width = '18px';
    el.style.height = '18px';
    el.style.background = color;
    el.style.borderRadius = '50%';
    el.style.boxShadow = `0 0 8px ${color}80`;
    el.style.border = '2px solid white';

    const popupHtml = `
      <div class="incident-popup">
        <strong>${type.toUpperCase()}</strong><br>
        ${eventText}<br>
        <small>${lat.toFixed(4)}, ${lon.toFixed(4)}</small>
      </div>
    `;

    const marker = new mapboxgl.Marker(el)
      .setLngLat([lon, lat])
      .setPopup(new mapboxgl.Popup({ offset: 8 }).setHTML(popupHtml))
      .addTo(map);

    markers.push({ marker, type });
  }

  function updateStats(points) {
    const count = points.length;
    const types = points.reduce((acc, p) => {
      const type = getIncidentType(p.src?.event || '');
      acc[type] = (acc[type] || 0) + 1;
      return acc;
    }, {});

    document.getElementById('incidentCount').innerText = count;

    let trafficLevel = 'Light';
    if (count > 20) trafficLevel = 'Heavy';
    else if (count > 10) trafficLevel = 'Moderate';

    document.getElementById('trafficLevel').innerText = trafficLevel;
    document.getElementById('status').innerText = `● Status: ${trafficLevel} Traffic (${count} incidents)`;

    // Update incident list
    const list = document.getElementById('incidentsList');
    list.innerHTML = '';
    
    points.slice(0, 15).forEach((p, i) => {
      const type = getIncidentType(p.src?.event || '');
      const color = getIncidentColor(type);
      const event = p.src?.event || p.src?.description || 'Unknown incident';
      
      const item = document.createElement('div');
      item.className = 'incident-item';
      item.innerHTML = `
        <span class="incident-dot" style="background: ${color}"></span>
        <div class="incident-info">
          <strong>${type}</strong><br>
          <small>${event}</small>
        </div>
      `;
      list.appendChild(item);
    });

    if (count > 15) {
      const more = document.createElement('div');
      more.style.fontSize = '12px';
      more.style.textAlign = 'center';
      more.style.color = '#666';
      more.innerText = `... and ${count - 15} more`;
      list.appendChild(more);
    }
  }

  async function loadIncidents() {
    const b = map.getBounds();
    const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(',');
    
    try {
      const res = await fetch(`/api/incidents?bbox=${bbox}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      const data = await res.json();
      const points = findPoints(data);

      clearMarkers();
      points.forEach((p, i) => addMarker(p, i));
      updateStats(points);

      const now = new Date().toLocaleTimeString();
      console.log(`Updated at ${now}: ${points.length} incidents found`);
    } catch (err) {
      console.error('Error fetching incidents:', err);
      document.getElementById('status').innerText = '● Status: Error loading data';
    }
  }

  function startAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(loadIncidents, 30000); // Refresh every 30s
    loadIncidents(); // Load immediately
  }

  function stopAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
  }

  // Event listeners
  document.getElementById('loadIncidents').addEventListener('click', loadIncidents);

  document.getElementById('toggleAutoRefresh').addEventListener('click', () => {
    autoRefreshEnabled = !autoRefreshEnabled;
    const btn = document.getElementById('toggleAutoRefresh');
    
    if (autoRefreshEnabled) {
      startAutoRefresh();
      btn.innerText = '🔄 Auto-refresh: ON';
      btn.classList.remove('inactive');
    } else {
      stopAutoRefresh();
      btn.innerText = '🔄 Auto-refresh: OFF';
      btn.classList.add('inactive');
    }
  });

  map.on('moveend', () => {
    if (autoRefreshEnabled) {
      loadIncidents();
    }
  });

  // Start auto-refresh on init
  startAutoRefresh();
}

init();
