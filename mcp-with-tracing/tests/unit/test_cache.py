"""
Unit tests for TTL cache and metrics collector caching.

Tests verify:
- TTL expiration behavior
- Cache hit/miss tracking
- MetricsCollector cache integration
- Cache invalidation
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from src.observability.cache import TTLCache, cache_result


class TestTTLCache:
    """Test TTL cache functionality."""

    def test_basic_set_and_get(self):
        """Test basic cache set and get."""
        cache = TTLCache(ttl=300, max_size=128)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_miss_returns_none(self):
        """Test that missing key returns None."""
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = TTLCache(ttl=1)  # 1 second TTL
        cache.set("key", "value")

        # Should hit
        assert cache.get("key") == "value"

        # Wait for expiration
        time.sleep(1.1)

        # Should miss (expired)
        assert cache.get("key") is None

    def test_cache_overwrite(self):
        """Test that setting same key updates value."""
        cache = TTLCache()
        cache.set("key", "value1")
        cache.set("key", "value2")
        assert cache.get("key") == "value2"

    def test_max_size_eviction(self):
        """Test that oldest entries are evicted when at capacity."""
        cache = TTLCache(ttl=300, max_size=3)

        cache.set("key1", "value1")
        time.sleep(0.01)
        cache.set("key2", "value2")
        time.sleep(0.01)
        cache.set("key3", "value3")
        time.sleep(0.01)

        # Add 4th entry - should evict oldest (key1)
        cache.set("key4", "value4")

        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_hit_rate_tracking(self):
        """Test cache hit rate calculation."""
        cache = TTLCache()
        cache.set("key", "value")

        # 2 hits
        cache.get("key")
        cache.get("key")

        # 1 miss
        cache.get("nonexistent")

        assert cache.hit_rate == pytest.approx(2 / 3, rel=0.01)

    def test_clear_resets_stats(self):
        """Test that clear() resets hit/miss counters."""
        cache = TTLCache()
        cache.set("key", "value")
        cache.get("key")
        cache.get("missing")

        assert cache._hits > 0
        assert cache._misses > 0

        cache.clear()

        assert cache._hits == 0
        assert cache._misses == 0
        assert cache.size == 0

    def test_invalidate_specific_key(self):
        """Test invalidation of specific cache entry."""
        cache = TTLCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.invalidate("key1")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_size_property(self):
        """Test cache size tracking."""
        cache = TTLCache()
        assert cache.size == 0

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.size == 2


class TestCacheResultDecorator:
    """Test cache_result decorator."""

    def test_decorator_caches_results(self):
        """Test that decorator caches function results."""
        call_count = 0

        @cache_result(ttl=300, max_size=128)
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - should execute
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

    def test_decorator_different_args(self):
        """Test that different arguments create separate cache entries."""
        call_count = 0

        @cache_result(ttl=300)
        def add(a: int, b: int) -> int:
            nonlocal call_count
            call_count += 1
            return a + b

        add(1, 2)  # Call 1
        add(3, 4)  # Call 2 (different args)
        add(1, 2)  # Cache hit

        assert call_count == 2

    def test_decorator_exposes_cache(self):
        """Test that decorator exposes cache for monitoring."""

        @cache_result(ttl=300)
        def func():
            return 42

        assert hasattr(func, "cache")
        assert isinstance(func.cache, TTLCache)


class TestMetricsCollectorCaching:
    """Test MetricsCollector cache integration."""

    @pytest.fixture
    def mock_traces(self):
        """Create mock trace data."""
        traces = MagicMock()
        traces.data = [
            MagicMock(status="OK", duration=100),
            MagicMock(status="OK", duration=200),
            MagicMock(status="ERROR", duration=300),
        ]
        return traces

    def test_fetch_traces_uses_cache(self, mock_traces):
        """Test that _fetch_traces caches API results."""
        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector(window_minutes=10, cache_ttl=300)

        with patch.object(collector, "_get_client") as mock_client:
            mock_client.return_value = MagicMock()
            mock_client.return_value.get_traces.return_value = mock_traces

            # First call - API call
            traces1 = collector._fetch_traces()
            assert len(traces1) == 3
            assert mock_client.return_value.get_traces.call_count == 1

            # Second call - cache hit
            traces2 = collector._fetch_traces()
            assert len(traces2) == 3
            # Should NOT call API again
            assert mock_client.return_value.get_traces.call_count == 1

    def test_cache_invalidation(self, mock_traces):
        """Test cache invalidation functionality."""
        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector(cache_ttl=300)

        with patch.object(collector, "_get_client") as mock_client:
            mock_client.return_value = MagicMock()
            mock_client.return_value.get_traces.return_value = mock_traces

            # Fetch and cache
            collector._fetch_traces()
            assert mock_client.return_value.get_traces.call_count == 1

            # Invalidate cache
            collector.invalidate_cache()

            # Fetch again - should call API
            collector._fetch_traces()
            assert mock_client.return_value.get_traces.call_count == 2

    def test_cache_stats(self, mock_traces):
        """Test cache statistics reporting."""
        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector(cache_ttl=300)

        with patch.object(collector, "_get_client") as mock_client:
            mock_client.return_value = MagicMock()
            mock_client.return_value.get_traces.return_value = mock_traces

            # Initial stats
            stats = collector.get_cache_stats()
            assert stats["ttl_seconds"] == 300
            assert stats["max_size"] == 64
            assert stats["size"] == 0

            # Fetch traces
            collector._fetch_traces()
            stats = collector.get_cache_stats()
            assert stats["size"] == 1

            # Fetch again (cache hit)
            collector._fetch_traces()
            stats = collector.get_cache_stats()
            assert stats["hit_rate"] > 0

    def test_session_specific_cache(self, mock_traces):
        """Test that different sessions have separate cache entries."""
        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector(cache_ttl=300)

        with patch.object(collector, "_get_client") as mock_client:
            mock_client.return_value = MagicMock()
            mock_client.return_value.get_traces.return_value = mock_traces

            # Fetch for session 1
            collector._fetch_traces(session_id="session_1")

            # Fetch for session 2
            collector._fetch_traces(session_id="session_2")

            # Should have 2 cache entries
            stats = collector.get_cache_stats()
            assert stats["size"] == 2

    def test_clear_cache(self, mock_traces):
        """Test cache clearing."""
        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector(cache_ttl=300)

        with patch.object(collector, "_get_client") as mock_client:
            mock_client.return_value = MagicMock()
            mock_client.return_value.get_traces.return_value = mock_traces

            # Fill cache
            collector._fetch_traces(session_id="session_1")
            collector._fetch_traces(session_id="session_2")

            stats = collector.get_cache_stats()
            assert stats["size"] == 2

            # Clear cache
            collector.clear_cache()

            stats = collector.get_cache_stats()
            assert stats["size"] == 0
            assert stats["hit_rate"] == 0.0
