"""
Simple in-memory caching module for traffic incidents.

This module demonstrates caching concepts: storing expensive API results
temporarily to avoid unnecessary external calls.

Learning objectives:
- Data structures (dictionaries, time tracking)
- TTL (Time To Live) concepts
- Cache hit/miss patterns
"""

import time
from typing import Dict, Optional, Any

class SimpleCache:
    """A simple key-value cache with TTL (Time To Live) support.

    When you ask for cached data, it checks if it's still fresh (TTL not expired).
    If expired, returns None so you know to fetch fresh data.

    Learning objective: Understanding cache patterns in real applications.

    Attributes:
        store: Dictionary storing cached data
        ttls: Dictionary storing expiration times for each key
    """

    def __init__(self):
        """Initialize empty cache."""
        self.store: Dict[str, Any] = {}
        self.ttls: Dict[str, float] = {}

    def set(self, key: str, value: Any, ttl_seconds: int = 30) -> None:
        """Store value in cache with TTL.

        Args:
            key: Cache key (e.g., "incidents_bbox_123")
            value: Data to cache
            ttl_seconds: How long to keep this data (default 30 seconds)

        Example:
            >>> cache = SimpleCache()
            >>> cache.set("my_key", {"data": [1, 2, 3]}, ttl_seconds=60)
        """
        self.store[key] = value
        self.ttls[key] = time.time() + ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if it hasn't expired.

        Args:
            key: Cache key to look up

        Returns:
            Cached value if key exists and TTL not expired, None otherwise

        Example:
            >>> cache.get("my_key")
            {'data': [1, 2, 3]}
            >>> cache.get("missing_key")
            None
        """
        if key not in self.store:
            return None

        # Check if TTL expired
        if time.time() > self.ttls[key]:
            # Clean up expired entry
            del self.store[key]
            del self.ttls[key]
            return None

        return self.store[key]

    def clear(self) -> None:
        """Clear all cached data."""
        self.store.clear()
        self.ttls.clear()

    def size(self) -> int:
        """Return number of cached items."""
        return len(self.store)


# Global cache instance (used by main.py)
incidents_cache = SimpleCache()
