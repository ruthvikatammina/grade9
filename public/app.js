/* CyberRoute — Hyderabad IT Corridor */

const MAP_CENTER     = [78.3794, 17.4454];
const MAP_ZOOM       = 11;
const CORRIDOR_BBOX  = '78.2,17.2,78.6,17.7';
const SEV_COLOR      = { clear: '#3fb950', slow: '#d29922', heavy: '#f85149' };

let map          = null;
let markersLayer = [];
let lastData     = [];
let prevData     = {};
let dirFilter    = 'all';
let favourites   = new Set(JSON.parse(localStorage.getItem('cyberroute-favs') || '[]'));

// ── DOM refs ──────────────────────────────────────────────────────────────────
const elStatusPill  = document.getElementById('status-pill');
const elGoBanner    = document.getElementById('go-banner');
const elNumClear    = document.getElementById('num-clear');
const elNumSlow     = document.getElementById('num-slow');
const elNumHeavy    = document.getElementById('num-heavy');
const elTripSelect  = document.getElementById('trip-select');
const elTripResult  = document.getElementById('trip-result');
const elRouteList   = document.getElementById('route-list');
const elRouteCount  = document.getElementById('route-count');
const elLastUpdated   = document.getElementById('last-updated');
const elToast         = document.getElementById('toast');
const elLeaveByRow    = document.getElementById('leave-by-row');
const elArriveByInput = document.getElementById('arrive-by-input');
const elLeaveByResult = document.getElementById('leave-by-result');
const btnRefresh      = document.getElementById('btn-refresh');
const btnLocate       = document.getElementById('btn-locate');

// ── Direction filter ──────────────────────────────────────────────────────────
document.querySelectorAll('.dir-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    dirFilter = btn.dataset.dir;
    document.querySelectorAll('.dir-btn').forEach(b => b.classList.remove('dir-btn-active'));
    btn.classList.add('dir-btn-active');
    render(lastData);
  });
});

const HUBS = ['HITEC City', 'Financial District'];

function applyDirFilter(routes) {
  if (dirFilter === 'to')
    return routes.filter(r => HUBS.some(h => r.description.endsWith('→ ' + h)));
  if (dirFilter === 'from')
    return routes.filter(r => HUBS.some(h => r.description.startsWith(h + ' →')));
  return routes;
}

// ── Fetch — runs regardless of map state ──────────────────────────────────────
async function fetchWithBbox(bbox) {
  setStatus('loading');
  const wakeTimer = setTimeout(() => {
    elGoBanner.textContent = '⏳ Server waking up — this takes ~30 sec on first visit…';
    elGoBanner.className   = 'banner banner-loading';
  }, 6000);
  try {
    const ctrl = new AbortController();
    const tid  = setTimeout(() => ctrl.abort(), 25000);
    const res  = await fetch(`/api/incidents?bbox=${bbox}`, { signal: ctrl.signal });
    clearTimeout(tid);
    clearTimeout(wakeTimer);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();

    prevData = Object.fromEntries(lastData.map(r => [r.description, r.traffic_mins]));
    lastData = json.incidents || [];
    render(lastData);
    setStatus('ok');
    elLastUpdated.textContent = 'Updated ' + new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  } catch (err) {
    clearTimeout(wakeTimer);
    setStatus('error');
    elRouteList.innerHTML = `<div class="empty-state">Could not load traffic data.<br><small style="color:#7d8590">${err.message}</small></div>`;
    console.error('fetch failed:', err);
  }
}

// Boot: fetch immediately with full corridor bbox — no map dependency
fetchWithBbox(CORRIDOR_BBOX);

// ── Map init (best-effort — data loading works without it) ────────────────────
function initMap() {
  if (typeof mapboxgl === 'undefined') {
    console.warn('Mapbox GL not available');
    return;
  }
  mapboxgl.accessToken = window.MAPBOX_TOKEN || '';
  map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/dark-v11',
    center: MAP_CENTER,
    zoom: MAP_ZOOM,
    attributionControl: false,
  });
  map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');
  map.addControl(new mapboxgl.AttributionControl({ compact: true }), 'bottom-right');
  map.on('moveend', () => {
    const b    = map.getBounds();
    const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]
      .map(n => n.toFixed(4)).join(',');
    fetchWithBbox(bbox);
  });
  map.on('load', () => {
    map.resize(); // ensure canvas fills container correctly on mobile
    // Mapbox traffic layer — shows live road colours even when API data is unavailable
    map.addSource('mapbox-traffic', {
      type: 'vector',
      url: 'mapbox://mapbox.mapbox-traffic-v1',
    });
    map.addLayer({
      id: 'traffic-flow',
      type: 'line',
      source: 'mapbox-traffic',
      'source-layer': 'traffic',
      paint: {
        'line-width': 2.5,
        'line-color': [
          'match', ['get', 'congestion'],
          'low',    '#3fb950',
          'moderate','#d29922',
          'heavy',  '#f85149',
          'severe', '#b91c1c',
          '#7d8590',
        ],
        'line-opacity': 0.8,
      },
    });
    if (lastData.length) lastData.forEach(addMarker);
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initMap);
} else {
  initMap();
}

// ── Render ────────────────────────────────────────────────────────────────────
function render(routes) {
  clearMarkers();
  const filtered = applyDirFilter(routes);
  updateSummary(filtered);
  updateBanner(filtered);
  buildTripSelect(filtered);
  buildRouteList(filtered);
  if (map) routes.forEach(addMarker);
}

function updateSummary(routes) {
  elNumClear.textContent   = routes.filter(r => normSev(r.severity) === 'clear').length;
  elNumSlow.textContent    = routes.filter(r => normSev(r.severity) === 'slow').length;
  elNumHeavy.textContent   = routes.filter(r => normSev(r.severity) === 'heavy').length;
  elRouteCount.textContent = routes.length;
  const label = dirFilter === 'to' ? 'Inbound' : dirFilter === 'from' ? 'Outbound' : 'All routes';
  document.querySelector('.routes-section .section-title').childNodes[0].textContent = label + ' ';
}

function updateBanner(routes) {
  if (!routes.length) {
    elGoBanner.className   = 'banner banner-loading';
    elGoBanner.textContent = 'No routes found in view';
    return;
  }
  const heavy = routes.filter(r => normSev(r.severity) === 'heavy').length;
  const clear = routes.filter(r => normSev(r.severity) === 'clear').length;
  if (heavy >= Math.ceil(routes.length / 2)) {
    elGoBanner.className   = 'banner banner-heavy';
    elGoBanner.textContent = '🔴 Heavy jams on ' + heavy + ' route' + (heavy > 1 ? 's' : '') + ' — consider waiting';
  } else if (clear >= Math.ceil(routes.length * 0.7)) {
    elGoBanner.className   = 'banner banner-clear';
    elGoBanner.textContent = '🟢 Corridor is moving well — good time to head out';
  } else {
    elGoBanner.className   = 'banner banner-slow';
    elGoBanner.textContent = '🟡 Some slowdowns — add 10–15 min buffer';
  }
}

function bestRoute(routes) {
  if (!routes.length) return null;
  return routes.slice().sort((a, b) => a.traffic_mins - b.traffic_mins)[0];
}

function buildRouteList(routes) {
  elRouteList.innerHTML = '';
  if (!routes.length) {
    elRouteList.innerHTML = '<div class="empty-state">No routes found.<br>Try refreshing.</div>';
    return;
  }

  if (dirFilter === 'to' || dirFilter === 'from') {
    const best = bestRoute(routes);
    if (best) {
      const sev = normSev(best.severity);
      const statusLabel = best.delay_mins > 0 ? `+${best.delay_mins} min delay` : 'On time';
      const card = document.createElement('div');
      card.className = 'best-route-card';
      card.innerHTML = `
        <div class="best-route-label">⚡ Best right now</div>
        <div class="best-route-name">${best.description}</div>
        <div class="best-route-meta">${best.traffic_mins} min · ${statusLabel}</div>
      `;
      card.addEventListener('click', () => {
        const idx = lastData.indexOf(best);
        if (idx >= 0) { elTripSelect.value = idx; showTripResult(); }
        if (map) map.flyTo({ center: [best.lng, best.lat], zoom: 13 });
      });
      elRouteList.appendChild(card);
    }
  }

  const favRoutes   = routes.filter(r => favourites.has(r.description));
  const otherRoutes = routes.filter(r => !favourites.has(r.description));

  if (favRoutes.length) {
    const label = document.createElement('div');
    label.className = 'fav-section-label';
    label.textContent = 'FAVOURITES';
    elRouteList.appendChild(label);
    favRoutes.forEach(r => elRouteList.appendChild(buildRouteCard(r)));
    if (otherRoutes.length) {
      const sep = document.createElement('div');
      sep.className = 'fav-section-label';
      sep.textContent = 'ALL ROUTES';
      elRouteList.appendChild(sep);
    }
  }

  otherRoutes.forEach(r => elRouteList.appendChild(buildRouteCard(r)));
}

function trendBadge(r) {
  const prev = prevData[r.description];
  if (prev === undefined) return '';
  const diff = r.traffic_mins - prev;
  if (diff >= 2)  return '<span class="trend trend-worse">↑ worse</span>';
  if (diff <= -2) return '<span class="trend trend-better">↓ better</span>';
  return '';
}

function buildRouteCard(r) {
  const sev   = normSev(r.severity);
  const isFav = favourites.has(r.description);
  const div   = document.createElement('div');
  div.className = `route-card sev-${sev}`;
  div.innerHTML = `
    <div class="route-card-body">
      <div class="route-name">${r.description}</div>
      <div class="route-sub">
        ${r.delay_mins > 0 ? 'Normal: ' + r.normal_mins + ' min' : ''}
        ${trendBadge(r)}
      </div>
    </div>
    <div class="route-card-time">
      <div class="route-mins">${r.traffic_mins}</div>
      <div class="route-mins-label">min</div>
      ${r.delay_mins > 0 ? `<div class="route-delay">+${r.delay_mins} min</div>` : '<div class="route-ok">On time</div>'}
    </div>
    <button class="fav-btn" title="Favourite">${isFav ? '★' : '☆'}</button>
  `;
  div.querySelector('.fav-btn').addEventListener('click', e => {
    e.stopPropagation();
    if (favourites.has(r.description)) {
      favourites.delete(r.description);
    } else {
      favourites.add(r.description);
    }
    localStorage.setItem('cyberroute-favs', JSON.stringify([...favourites]));
    render(lastData);
  });
  div.addEventListener('click', () => {
    const idx = lastData.indexOf(r);
    if (idx >= 0) { elTripSelect.value = idx; showTripResult(); }
    if (map) map.flyTo({ center: [r.lng, r.lat], zoom: 13 });
  });
  return div;
}

function buildTripSelect(routes) {
  const prev = elTripSelect.value;
  elTripSelect.innerHTML = '<option value="">Choose your route…</option>';
  routes.forEach((r, i) => {
    const idx = lastData.indexOf(r);
    const opt = document.createElement('option');
    opt.value = idx >= 0 ? idx : i;
    opt.textContent = r.description;
    elTripSelect.appendChild(opt);
  });
  if (prev !== '') { elTripSelect.value = prev; showTripResult(); }
}

function showTripResult() {
  const idx = elTripSelect.value;
  if (idx === '') { elTripResult.className = 'trip-result hidden'; elLeaveByRow.classList.add('hidden'); return; }
  const r = lastData[parseInt(idx, 10)];
  if (!r) return;

  const sev         = normSev(r.severity);
  const arriveTime  = arrivingByTime(r.traffic_mins);
  const advice      = leaveAdvice(sev);
  const adviceClass = { clear: 'advice-clear', slow: 'advice-slow', heavy: 'advice-heavy' }[sev];
  const shareMsg    = encodeURIComponent(
    `CyberRoute: ${r.description} — ${r.traffic_mins} min now` +
    (r.delay_mins > 0 ? ` (+${r.delay_mins} min delay)` : ' (on time)') +
    `. ETA ${arriveTime}. ${advice}`
  );

  // Show leave-by calculator
  elLeaveByRow.classList.remove('hidden');
  updateLeaveBy(r);

  elTripResult.className = 'trip-result';
  elTripResult.innerHTML = `
    <div class="trip-eta-hero">
      <div>
        <div class="trip-eta-mins">${r.traffic_mins}</div>
        <div class="trip-eta-label">minutes to destination</div>
      </div>
      <div class="trip-arrive-time">
        <div class="arrive-label">Arrive by</div>
        <div class="arrive-val">${arriveTime}</div>
      </div>
    </div>
    <div class="trip-rows">
      <div class="trip-row"><span>Normal time</span><strong>${r.normal_mins} min</strong></div>
      <div class="trip-row"><span>Extra delay</span><strong>${r.delay_mins > 0 ? '+' + r.delay_mins + ' min' : 'None'}</strong></div>
    </div>
    <div class="trip-advice ${adviceClass}">${advice}</div>
    <a class="btn-share" href="https://wa.me/?text=${shareMsg}" target="_blank" rel="noopener">📲 Share on WhatsApp</a>
  `;
}

function updateLeaveBy(r) {
  if (!elArriveByInput.value) { elLeaveByResult.textContent = ''; return; }
  const [h, m]     = elArriveByInput.value.split(':').map(Number);
  const arriveMs   = new Date().setHours(h, m, 0, 0);
  const leaveMs    = arriveMs - r.traffic_mins * 60 * 1000;
  const leaveTime  = new Date(leaveMs).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  const minsToGo   = Math.round((leaveMs - Date.now()) / 60000);
  if (minsToGo < 0) {
    elLeaveByResult.textContent = `⚠️ You needed to leave ${Math.abs(minsToGo)} min ago`;
    elLeaveByResult.className   = 'leave-by-result leave-late';
  } else if (minsToGo <= 10) {
    elLeaveByResult.textContent = `🚗 Leave now! Depart by ${leaveTime}`;
    elLeaveByResult.className   = 'leave-by-result leave-now';
  } else {
    elLeaveByResult.textContent = `⏰ Leave by ${leaveTime} (in ${minsToGo} min)`;
    elLeaveByResult.className   = 'leave-by-result leave-ok';
  }
}

function leaveAdvice(sev) {
  if (sev === 'clear') return '✅ Roads are clear — leave now for the best run.';
  if (sev === 'heavy') return '⏳ Heavy traffic. If flexible, wait 20–30 min.';
  return '🟡 Manageable slowdown — leave now but add buffer time.';
}

function arrivingByTime(mins) {
  const d = new Date(Date.now() + mins * 60 * 1000);
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

// ── Markers ───────────────────────────────────────────────────────────────────
function addMarker(r) {
  if (!map) return;
  const sev = normSev(r.severity);
  const el  = document.createElement('div');
  el.className = 'map-dot' + (sev === 'heavy' ? ' pulsing' : '');
  el.style.background = SEV_COLOR[sev] || '#7d8590';

  const popup = new mapboxgl.Popup({ offset: 14, closeButton: false, maxWidth: '220px' })
    .setHTML(
      `<strong>${r.description}</strong><br>${r.traffic_mins} min` +
      (r.delay_mins > 0 ? ` · <span style="color:#f85149">+${r.delay_mins} min</span>` : ' · <span style="color:#3fb950">On time</span>')
    );

  markersLayer.push(new mapboxgl.Marker(el).setLngLat([r.lng, r.lat]).setPopup(popup).addTo(map));
}

function clearMarkers() {
  markersLayer.forEach(m => m.remove());
  markersLayer = [];
}

function normSev(s) {
  if (s === 'clear' || s === 'light')    return 'clear';
  if (s === 'heavy' || s === 'moderate') return 'heavy';
  return 'slow';
}

// ── Status / Toast ────────────────────────────────────────────────────────────
function setStatus(state) {
  const labels  = { loading: '…', ok: 'Live', error: 'Error' };
  const classes = { loading: 'pill pill-loading', ok: 'pill pill-ok', error: 'pill pill-error' };
  elStatusPill.textContent = labels[state]  || '…';
  elStatusPill.className   = classes[state] || 'pill pill-loading';
}

function showToast(msg, ms = 3500) {
  elToast.textContent = msg;
  elToast.className   = 'toast';
  clearTimeout(elToast._t);
  elToast._t = setTimeout(() => { elToast.className = 'toast hidden'; }, ms);
}

// ── Buttons ───────────────────────────────────────────────────────────────────
btnRefresh.addEventListener('click', () => {
  btnRefresh.disabled = true;
  const bbox = map
    ? [map.getBounds().getWest(), map.getBounds().getSouth(),
       map.getBounds().getEast(), map.getBounds().getNorth()].map(n => n.toFixed(4)).join(',')
    : CORRIDOR_BBOX;
  fetchWithBbox(bbox).finally(() => { btnRefresh.disabled = false; });
});

btnLocate.addEventListener('click', () => {
  if (!navigator.geolocation) { showToast('Geolocation not supported'); return; }
  navigator.geolocation.getCurrentPosition(
    pos => {
      if (map) map.flyTo({ center: [pos.coords.longitude, pos.coords.latitude], zoom: 13 });
      else showToast('Map not available');
    },
    () => showToast('Location access denied'),
    { timeout: 8000 }
  );
});

elTripSelect.addEventListener('change', showTripResult);

elArriveByInput.addEventListener('input', () => {
  const idx = elTripSelect.value;
  if (idx === '') return;
  const r = lastData[parseInt(idx, 10)];
  if (r) updateLeaveBy(r);
});

