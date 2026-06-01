"""
Utility functions for traffic data processing.

This module contains helper functions for calculating congestion levels
and classifying traffic conditions.

Learning objective: Functions with clear purpose, type hints, and docstrings.
"""

from typing import Dict, Optional
from server.config import CONGESTION_THRESHOLDS


def calculate_congestion(duration_in_traffic: int, normal_duration: int) -> Dict[str, any]:
    """Calculate congestion level and classify traffic intensity.

    Compares actual travel time (with traffic) to normal travel time to determine
    how congested a route is. Uses thresholds defined in config.py.

    Args:
        duration_in_traffic: Actual travel time in seconds (including traffic delay)
        normal_duration: Normal travel time in seconds (no traffic)

    Returns:
        Dictionary with keys:
            - 'delay_ratio': float (duration_in_traffic / normal_duration)
            - 'event_type': str (classification: 'Heavy congestion', 'Moderate congestion', etc.)
            - 'severity': str (short code: 'heavy', 'moderate', 'slowdown', 'light')

    Examples:
        >>> calculate_congestion(300, 200)  # 1.5x normal time
        {'delay_ratio': 1.5, 'event_type': 'Heavy congestion', 'severity': 'heavy'}

        >>> calculate_congestion(200, 200)  # Same as normal
        {'delay_ratio': 1.0, 'event_type': 'Light traffic', 'severity': 'light'}
    """
    if normal_duration <= 0:
        # Can't calculate ratio with zero or negative normal duration
        return {
            'delay_ratio': 0,
            'event_type': 'Unknown',
            'severity': 'unknown'
        }

    delay_ratio = duration_in_traffic / normal_duration

    # Classify based on thresholds
    if delay_ratio > CONGESTION_THRESHOLDS['heavy']:
        event_type = 'Heavy congestion'
        severity = 'heavy'
    elif delay_ratio > CONGESTION_THRESHOLDS['moderate']:
        event_type = 'Moderate congestion'
        severity = 'moderate'
    elif delay_ratio > CONGESTION_THRESHOLDS['slowdown']:
        event_type = 'Slowdown'
        severity = 'slowdown'
    else:
        event_type = 'Light traffic'
        severity = 'light'

    return {
        'delay_ratio': delay_ratio,
        'event_type': event_type,
        'severity': severity
    }


def is_route_in_bbox(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    tolerance: float = 0.05
) -> bool:
    """Check if a route's center point is within/near the bounding box.

    Used to filter which routes we query based on the map viewport.

    Args:
        origin_lat, origin_lng: Starting point coordinates
        dest_lat, dest_lng: Ending point coordinates
        min_lat, min_lng, max_lat, max_lng: Bounding box corners
        tolerance: Degrees of buffer around bbox (default 0.05°)

    Returns:
        True if route center is within bbox + tolerance, False otherwise
    """
    route_center_lng = (origin_lng + dest_lng) / 2
    route_center_lat = (origin_lat + dest_lat) / 2

    return (
        min_lng - tolerance <= route_center_lng <= max_lng + tolerance and
        min_lat - tolerance <= route_center_lat <= max_lat + tolerance
    )
