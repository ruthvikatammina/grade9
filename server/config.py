"""
TGTraffic — server configuration.
"""

import os
from typing import List, Tuple
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
TOMTOM_API_KEY      = os.getenv('TOMTOM_API_KEY')
MAPBOX_TOKEN        = os.getenv('MAPBOX_ACCESS_TOKEN')
PORT                = int(os.getenv('PORT', '3000'))

# ── Hyderabad IT-corridor routes ──────────────────────────────────────────────
# Format: (origin_lat, origin_lng, dest_lat, dest_lng, "Display name")
# ─────────────────────────────────────────────────────────────────────────────

FIN_DIST = (17.4150, 78.3481)   # Financial District / Nanakramguda junction
HITEC     = (17.4454, 78.3794)  # HITEC City / Madhapur junction

HYDERABAD_ROUTES: List[Tuple[float, float, float, float, str]] = [
    # ── Inbound to HITEC City ─────────────────────────────────────────────────
    (17.4399, 78.4983, *HITEC, "Secunderabad → HITEC City"),
    (17.4479, 78.3996, *HITEC, "Kukatpally → HITEC City"),
    (17.4374, 78.4487, *HITEC, "Ameerpet → HITEC City"),
    (17.3850, 78.4867, *HITEC, "Nampally → HITEC City"),
    (17.3452, 78.5534, *HITEC, "LB Nagar → HITEC City"),
    (17.3688, 78.5263, *HITEC, "Dilsukhnagar → HITEC City"),
    (17.5507, 78.4880, *HITEC, "Kompally → HITEC City"),
    (17.2403, 78.4294, *HITEC, "Airport → HITEC City"),

    # ── Inbound to Financial District ─────────────────────────────────────────
    (17.4399, 78.4983, *FIN_DIST, "Secunderabad → Financial District"),
    (17.4374, 78.4487, *FIN_DIST, "Ameerpet → Financial District"),
    (17.3850, 78.4867, *FIN_DIST, "Nampally → Financial District"),
    (17.3452, 78.5534, *FIN_DIST, "LB Nagar → Financial District"),
    (17.2403, 78.4294, *FIN_DIST, "Airport → Financial District"),

    # ── Between hubs ──────────────────────────────────────────────────────────
    (*HITEC,    *FIN_DIST, "HITEC City → Financial District"),
    (*FIN_DIST, *HITEC,    "Financial District → HITEC City"),

    # ── Evening outbound ──────────────────────────────────────────────────────
    (*HITEC,    17.3850, 78.4867, "HITEC City → Nampally"),
    (*FIN_DIST, 17.3850, 78.4867, "Financial District → Nampally"),
    (*HITEC,    17.2403, 78.4294, "HITEC City → Airport"),

    # ── Other corridor ────────────────────────────────────────────────────────
    (17.3850, 78.4867, 17.4175, 78.4237, "Nampally → Banjara Hills"),
    (17.4401, 78.3489, *HITEC,            "Gachibowli → HITEC City"),
]

# ── Congestion thresholds (ratio of traffic time / normal time) ───────────────
CONGESTION_THRESHOLDS = {
    'heavy':    1.5,
    'moderate': 1.2,
    'slowdown': 1.0,
}

# ── API settings ──────────────────────────────────────────────────────────────
GOOGLE_MAPS_API_TIMEOUT   = 8.0
GOOGLE_MAPS_TOTAL_TIMEOUT = 25.0

# 5-minute cache — matches the manual refresh expectation
CACHE_TTL_SECONDS = 300

# Viewport tolerance so routes near the map edge are included
BBOX_TOLERANCE = 0.3
