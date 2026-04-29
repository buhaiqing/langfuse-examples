"""
Cache utilities for metrics collection optimization.

Provides TTL-based caching decorator to reduce redundant API calls
and improve performance of metrics collection.
"""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any


class TTLCache:
    """
    Thread-safe TTL cache with configurable expiration.

    Attributes:
        ttl: Time-to-live in seconds for cache entries.
        max_size: Maximum number of entries in cache.

    Example:
        >>> cache = TTLCache(ttl=300, max_size=128)
        >>> cache.set("key", "value")
        >>> cache.get("key")
        'value'
    """

    def __init__(self, ttl: int = 300, max_size: int = 128):
        """
        Initialize TTL cache.

        Args:
            ttl: Cache entry lifetime in seconds (default: 5 minutes).
            max_size: Maximum cache entries (default: 128).
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: dict[str, tuple[Any, float]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if expired/missing.
        """
        if key not in self._cache:
            self._misses += 1
            return None

        value, timestamp = self._cache[key]
        if time.time() - timestamp > self.ttl:
            # Entry expired
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set cache entry with current timestamp.

        Args:
            key: Cache key.
            value: Value to cache.
        """
        # Evict oldest entry if at capacity
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        self._cache[key] = (value, time.time())

    def invalidate(self, key: str) -> None:
        """
        Remove specific cache entry.

        Args:
            key: Cache key to remove.
        """
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def hit_rate(self) -> float:
        """
        Calculate cache hit rate.

        Returns:
            Hit rate as float between 0.0 and 1.0.
        """
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    @property
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


def cache_result(ttl: int = 300, max_size: int = 128):
    """
    Decorator to cache function results with TTL.

    Args:
        ttl: Cache lifetime in seconds.
        max_size: Maximum cache entries.

    Returns:
        Decorated function with caching.

    Example:
        @cache_result(ttl=600, max_size=256)
        def expensive_api_call(param: str) -> dict:
            # Expensive operation
            return fetch_from_api(param)
    """
    cache = TTLCache(ttl=ttl, max_size=max_size)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key from function name and arguments
            key = f"{func.__name__}:{args!s}:{sorted(kwargs.items())!s}"

            # Check cache
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result

        # Expose cache for monitoring/invalidation
        wrapper.cache = cache  # type: ignore[attr-defined]
        return wrapper

    return decorator
