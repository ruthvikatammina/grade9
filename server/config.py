"""
Configuration module for Hyderabad Traffic Dashboard.

This module centralizes all hardcoded values, constants, and environment variables.
Learning objective: Understanding configuration management in Python.
"""

import os
from typing import List, Tuple
from dotenv import load_dotenv

load_dotenv()

# API Keys from environment variables
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
MAPBOX_TOKEN = os.getenv('MAPBOX_ACCESS_TOKEN')
PORT = int(os.getenv('PORT', '3000'))

# Hyderabad major routes for traffic monitoring
# Each route is: (origin_lat, origin_lng, dest_lat, dest_lng, route_name)
HYDERABAD_ROUTES: List[Tuple[float, float, float, float, str]] = [
    (17.3850, 78.4867, 17.4454, 78.3794, "Hyderabad Center to HITEC City"),
    (17.3850, 78.4867, 17.4175, 78.4237, "Hyderabad Center to Banjara Hills"),
    (17.4454, 78.3794, 17.4175, 78.4237, "HITEC City to Banjara Hills"),
    (17.4479, 78.4202, 17.3850, 78.4867, "Kukatpally to Hyderabad Center"),
    (17.4404, 78.4010, 17.3850, 78.4867, "Gachibowli to Hyderabad Center"),
    (17.3850, 78.4867, 17.2993, 78.5404, "Hyderabad Center to Begumpet"),
]

# Congestion classification thresholds
# These determine how we classify traffic based on delay ratio
CONGESTION_THRESHOLDS = {
    'heavy': 1.5,      # > 1.5x normal time = heavy congestion
    'moderate': 1.2,   # > 1.2x normal time = moderate congestion
    'slowdown': 1.0,   # > 1.0x normal time = slowdown
}

# Google Maps API settings
GOOGLE_MAPS_API_TIMEOUT = 5.0  # seconds per request
GOOGLE_MAPS_TOTAL_TIMEOUT = 15.0  # seconds for all requests

# Bounding box tolerance (degrees) for filtering routes
BBOX_TOLERANCE = 0.05
