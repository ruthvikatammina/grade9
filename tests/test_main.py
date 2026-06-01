"""
Unit tests for traffic data calculations.

Testing is crucial for ensuring our code works correctly. This file demonstrates:
- Writing testable code (pure functions)
- Using pytest framework
- Testing edge cases and error conditions

Learning objectives:
- Understanding unit testing
- Writing assertions to verify behavior
- Testing pure functions vs. side effects

To run these tests:
    pytest tests/test_main.py -v
"""

import pytest
from server.utils import calculate_congestion, is_route_in_bbox
from server.cache import SimpleCache


class TestCalculateCongestion:
    """Test suite for congestion calculation function."""

    def test_heavy_congestion(self):
        """Test classification of heavy congestion (> 1.5x normal time)."""
        result = calculate_congestion(duration_in_traffic=1501, normal_duration=1000)
        assert result['severity'] == 'heavy'
        assert result['event_type'] == 'Heavy congestion'
        assert abs(result['delay_ratio'] - 1.501) < 0.01

    def test_moderate_congestion(self):
        """Test classification of moderate congestion (1.2x - 1.5x)."""
        result = calculate_congestion(duration_in_traffic=1300, normal_duration=1000)
        assert result['severity'] == 'moderate'
        assert result['event_type'] == 'Moderate congestion'
        assert abs(result['delay_ratio'] - 1.3) < 0.01

    def test_slowdown(self):
        """Test classification of slowdown (1.0x - 1.2x)."""
        result = calculate_congestion(duration_in_traffic=1100, normal_duration=1000)
        assert result['severity'] == 'slowdown'
        assert result['event_type'] == 'Slowdown'
        assert abs(result['delay_ratio'] - 1.1) < 0.01

    def test_light_traffic(self):
        """Test light traffic when actual time equals normal time."""
        result = calculate_congestion(duration_in_traffic=1000, normal_duration=1000)
        assert result['severity'] == 'light'
        assert result['event_type'] == 'Light traffic'
        assert result['delay_ratio'] == 1.0

    def test_zero_duration(self):
        """Test error handling for zero normal duration."""
        result = calculate_congestion(duration_in_traffic=100, normal_duration=0)
        assert result['event_type'] == 'Unknown'
        assert result['severity'] == 'unknown'

    def test_negative_duration(self):
        """Test error handling for negative duration."""
        result = calculate_congestion(duration_in_traffic=100, normal_duration=-50)
        assert result['event_type'] == 'Unknown'
        assert result['severity'] == 'unknown'

    def test_extreme_congestion(self):
        """Test very high congestion ratio (2x normal time)."""
        result = calculate_congestion(duration_in_traffic=2000, normal_duration=1000)
        assert result['severity'] == 'heavy'
        assert result['delay_ratio'] == 2.0


class TestIsRouteInBbox:
    """Test suite for bounding box filtering function."""

    def test_route_inside_bbox(self):
        """Test that route within bbox returns True."""
        inside = is_route_in_bbox(
            origin_lat=17.0, origin_lng=78.0,
            dest_lat=17.1, dest_lng=78.1,
            min_lat=16.5, min_lng=77.5,
            max_lat=17.5, max_lng=78.5,
            tolerance=0
        )
        assert inside is True

    def test_route_outside_bbox(self):
        """Test that route outside bbox returns False."""
        outside = is_route_in_bbox(
            origin_lat=18.0, origin_lng=79.0,
            dest_lat=18.1, dest_lng=79.1,
            min_lat=16.5, min_lng=77.5,
            max_lat=17.5, max_lng=78.5,
            tolerance=0
        )
        assert outside is False

    def test_route_at_bbox_edge(self):
        """Test route exactly at bbox boundary."""
        at_edge = is_route_in_bbox(
            origin_lat=16.5, origin_lng=77.5,
            dest_lat=17.5, dest_lng=78.5,
            min_lat=16.5, min_lng=77.5,
            max_lat=17.5, max_lng=78.5,
            tolerance=0
        )
        assert at_edge is True

    def test_route_with_tolerance(self):
        """Test that tolerance allows slightly outside routes."""
        near = is_route_in_bbox(
            origin_lat=17.5, origin_lng=78.5,
            dest_lat=17.6, dest_lng=78.6,
            min_lat=16.5, min_lng=77.5,
            max_lat=17.5, max_lng=78.5,
            tolerance=0.2  # Allow 0.2 degrees outside
        )
        assert near is True


class TestSimpleCache:
    """Test suite for cache functionality."""

    def test_cache_set_and_get(self):
        """Test basic cache set and get."""
        cache = SimpleCache()
        cache.set("key1", {"data": [1, 2, 3]}, ttl_seconds=60)
        value = cache.get("key1")
        assert value == {"data": [1, 2, 3]}

    def test_cache_miss(self):
        """Test getting non-existent key returns None."""
        cache = SimpleCache()
        value = cache.get("nonexistent")
        assert value is None

    def test_cache_expiration(self):
        """Test that expired cache returns None.

        Note: This test uses a very short TTL to avoid long test times.
        In production, use longer TTLs (30+ seconds).
        """
        import time
        cache = SimpleCache()
        cache.set("key1", "value1", ttl_seconds=1)  # Expire in 1 second
        assert cache.get("key1") == "value1"  # Fresh cache
        time.sleep(1.1)
        assert cache.get("key1") is None  # Expired

    def test_cache_clear(self):
        """Test clearing all cache."""
        cache = SimpleCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2
        cache.clear()
        assert cache.size() == 0

    def test_cache_multiple_keys(self):
        """Test storing multiple keys in cache."""
        cache = SimpleCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.size() == 3


# Run tests with: pytest tests/test_main.py -v
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
