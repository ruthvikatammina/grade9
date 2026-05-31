const express = require('express');
const fetch = require('node-fetch');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.static('public'));

app.get('/config', (req, res) => {
  res.json({
    mapboxToken: process.env.MAPBOX_ACCESS_TOKEN || null
  });
});

// Proxy HERE Traffic incidents for a given bbox
// Expect bbox as: minLng,minLat,maxLng,maxLat
app.get('/api/incidents', async (req, res) => {
  try {
    const bbox = req.query.bbox;
    if (!bbox) return res.status(400).json({ error: 'missing bbox query param' });

    const [minLng, minLat, maxLng, maxLat] = bbox.split(',').map(Number);

    const topLeftLat = maxLat;
    const topLeftLon = minLng;
    const bottomRightLat = minLat;
    const bottomRightLon = maxLng;

    const hereKey = process.env.HERE_API_KEY;
    if (!hereKey) return res.status(500).json({ error: 'HERE_API_KEY not set on server' });

    const url = `https://traffic.ls.hereapi.com/traffic/6.3/incidents.json?bbox=${topLeftLat},${topLeftLon};${bottomRightLat},${bottomRightLon}&apiKey=${hereKey}`;

    const resp = await fetch(url);
    const data = await resp.json();
    res.json(data);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'internal error' });
  }
});

app.listen(PORT, () => {
  console.log(`Server listening on http://localhost:${PORT}`);
});
