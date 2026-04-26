"""Redis 降级与连接池测试

测试:
- 熔断器状态转换（P1-7 修复验证）
- 本地缓存功能
- 降级策略管理
- 连接池兼容层（P1-8 修复验证）
"""

import time

import pytest
from storage.redis_fallback import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    FallbackConfig,
    FallbackStrategy,
    LocalCache,
)


class TestCircuitBreaker:
    """熔断器测试"""

    def test_initial_state_is_closed(self):
        """初始状态为 CLOSED"""
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_transitions_to_open_on_failures(self):
        """连续失败后转换为 OPEN"""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(name="test", config=config)

        for _i in range(3):
            await cb.record_failure()

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_remains_closed_below_threshold(self):
        """失败次数未达阈值时保持 CLOSED"""
        config = CircuitBreakerConfig(failure_threshold=5)
        cb = CircuitBreaker(name="test", config=config)

        for _i in range(4):
            await cb.record_failure()

        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_success_resets_consecutive_failures(self):
        """成功重置连续失败计数"""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(name="test", config=config)

        await cb.record_failure()
        await cb.record_failure()
        await cb.record_success()

        assert cb.stats.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_half_open_allows_limited_requests(self):
        """HALF_OPEN 状态允许有限请求"""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0)
        cb = CircuitBreaker(name="test", config=config)

        await cb.record_failure()
        await cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb._transition_to_half_open()
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        """HALF_OPEN 状态下成功关闭熔断器"""
        config = CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout=0, half_open_max_calls=3, success_threshold=1
        )
        cb = CircuitBreaker(name="test", config=config)

        await cb.record_failure()
        await cb.record_failure()
        cb._transition_to_half_open()
        await cb.record_success()

        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self):
        """HALF_OPEN 状态下失败重新打开熔断器"""
        config = CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout=0, half_open_max_calls=3
        )
        cb = CircuitBreaker(name="test", config=config)

        await cb.record_failure()
        await cb.record_failure()
        cb._transition_to_half_open()
        await cb.record_failure()

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_can_execute_closed(self):
        """CLOSED 状态允许请求"""
        cb = CircuitBreaker(name="test")
        assert await cb.can_execute() is True

    @pytest.mark.asyncio
    async def test_can_execute_open(self):
        """OPEN 状态拒绝请求"""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker(name="test", config=config)
        await cb.record_failure()
        assert await cb.can_execute() is False

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """统计信息追踪"""
        cb = CircuitBreaker(name="test")
        await cb.record_success()
        await cb.record_success()
        await cb.record_failure()

        assert cb.stats.success_requests == 2
        assert cb.stats.failed_requests == 1
        assert cb.stats.total_requests == 3


class TestLocalCache:
    """本地缓存测试"""

    def test_set_and_get(self):
        """设置和获取缓存"""
        cache = LocalCache(max_size=100, default_ttl=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self):
        """获取不存在的键返回 None"""
        cache = LocalCache(max_size=100, default_ttl=60)
        assert cache.get("nonexistent") is None

    def test_cache_eviction(self):
        """缓存满时淘汰旧数据"""
        cache = LocalCache(max_size=3, default_ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")

        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

    def test_cache_ttl_expiry(self):
        """缓存 TTL 过期"""
        cache = LocalCache(max_size=100, default_ttl=0)
        cache.set("key1", "value1")
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_cache_delete(self):
        """删除缓存项"""
        cache = LocalCache(max_size=100, default_ttl=60)
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_cache_clear(self):
        """清空缓存"""
        cache = LocalCache(max_size=100, default_ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestFallbackConfig:
    """降级配置测试"""

    def test_default_config(self):
        """默认配置值"""
        config = FallbackConfig()
        assert config.strategy == FallbackStrategy.CACHE
        assert config.cache_ttl == 300
        assert config.cache_max_size == 1000

    def test_custom_config(self):
        """自定义配置"""
        config = FallbackConfig(
            strategy=FallbackStrategy.DEFAULT_VALUE,
            cache_ttl=600,
            cache_max_size=500,
        )
        assert config.strategy == FallbackStrategy.DEFAULT_VALUE
        assert config.cache_ttl == 600
        assert config.cache_max_size == 500


class TestRedisPoolCompatibility:
    """Redis 连接池兼容层测试（P1-8 修复验证）"""

    def test_redis_pool_config_exists(self):
        """RedisPoolConfig 类存在"""
        from storage.redis_pool import RedisPoolConfig

        config = RedisPoolConfig()
        assert config.max_connections == 100

    def test_pool_metrics_exists(self):
        """PoolMetrics 类存在"""
        from storage.redis_pool import PoolMetrics

        metrics = PoolMetrics()
        assert metrics.is_healthy is True

    def test_redis_pool_manager_delegates(self):
        """RedisPoolManager 委托给 RedisClient"""
        from storage.redis_pool import RedisPoolManager

        manager = RedisPoolManager()
        assert manager._initialized is False


class TestFallbackCompatibility:
    """降级模块兼容层测试（P1-7 修复验证）"""

    def test_utils_fallback_reexports(self):
        """utils.fallback 重新导出 storage.redis_fallback 的类"""
        from storage.redis_fallback import (
            CircuitBreaker as StorageCB,
        )
        from storage.redis_fallback import (
            CircuitBreakerConfig as StorageCBConfig,
        )
        from storage.redis_fallback import (
            CircuitState as StorageCS,
        )
        from storage.redis_fallback import (
            FallbackConfig as StorageFC,
        )
        from storage.redis_fallback import (
            LocalCache as StorageLC,
        )
        from storage.redis_fallback import (
            RedisFallbackManager as StorageRFM,
        )
        from utils.fallback import (
            CircuitBreaker as UtilsCB,
        )
        from utils.fallback import (
            CircuitBreakerConfig as UtilsCBConfig,
        )
        from utils.fallback import (
            CircuitState as UtilsCS,
        )
        from utils.fallback import (
            FallbackConfig as UtilsFC,
        )
        from utils.fallback import (
            LocalCache as UtilsLC,
        )
        from utils.fallback import (
            RedisFallbackManager as UtilsRFM,
        )

        assert UtilsCB is StorageCB
        assert UtilsCBConfig is StorageCBConfig
        assert UtilsCS is StorageCS
        assert UtilsLC is StorageLC
        assert UtilsFC is StorageFC
        assert UtilsRFM is StorageRFM
