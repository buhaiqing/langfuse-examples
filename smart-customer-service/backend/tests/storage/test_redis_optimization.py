"""Redis 连接池和降级策略测试"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import time

from backend.storage.redis_pool import (
    RedisPoolManager,
    RedisPoolConfig,
    PoolMetrics,
    get_redis_pool,
    init_redis_pool,
)

from backend.utils.fallback import (
    FallbackManager,
    FallbackConfig,
    FallbackStrategy,
    CircuitBreakerState,
    LocalCache,
    get_fallback_manager,
    fallback,
)


# ============== Redis 连接池测试 ==============


class TestRedisPoolConfig:
    """Redis 连接池配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = RedisPoolConfig()

        assert config.max_connections == 100
        assert config.min_idle_connections == 10
        assert config.connection_timeout == 30.0
        assert config.socket_timeout == 5.0
        assert config.health_check_interval == 30
        assert config.enable_fallback is True


class TestLocalCache:
    """本地缓存测试"""

    def test_cache_set_get(self):
        """测试缓存设置和获取"""
        cache = LocalCache()

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.get("nonexistent") is None

    def test_cache_ttl(self):
        """测试缓存过期"""
        cache = LocalCache(ttl_seconds=0.1)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # 等待过期
        time.sleep(0.2)
        assert cache.get("key1") is None

    def test_cache_max_size(self):
        """测试缓存最大容量"""
        cache = LocalCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        assert cache.size() == 3

        # 添加第 4 个，应该删除最旧的
        cache.set("key4", "value4")
        assert cache.size() == 3
        assert cache.get("key4") == "value4"

    def test_cache_clear(self):
        """测试清空缓存"""
        cache = LocalCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert cache.size() == 0


class TestRedisPoolManager:
    """Redis 连接池管理器测试"""

    @pytest.fixture
    def pool_config(self):
        """创建测试配置"""
        return RedisPoolConfig(
            max_connections=10,
            health_check_interval=10,
        )

    @pytest.mark.asyncio
    async def test_initialize_success(self, pool_config):
        """测试初始化成功"""
        pool = RedisPoolManager(pool_config)

        # Mock Redis 连接
        with patch("backend.storage.redis_pool.redis.ConnectionPool") as mock_pool:
            with patch.object(pool, "_health_check", new_callable=AsyncMock) as mock_health:
                mock_health.return_value = True

                success = await pool.initialize()

                assert success is True
                assert pool._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_failure(self, pool_config):
        """测试初始化失败"""
        pool = RedisPoolManager(pool_config)

        with patch("backend.storage.redis_pool.redis.ConnectionPool") as mock_pool:
            mock_pool.side_effect = ConnectionError("Redis unavailable")

            success = await pool.initialize()

            assert success is False
            assert pool.metrics.is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_success(self, pool_config):
        """测试健康检查成功"""
        pool = RedisPoolManager(pool_config)
        pool.client = AsyncMock()
        pool.client.ping = AsyncMock()

        result = await pool._health_check()

        assert result is True
        assert pool.metrics.health_check_failures == 0
        assert pool.metrics.is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, pool_config):
        """测试健康检查失败"""
        pool = RedisPoolManager(pool_config)
        pool.client = AsyncMock()
        pool.client.ping = AsyncMock(side_effect=ConnectionError())

        result = await pool._health_check()

        assert result is False
        assert pool.metrics.health_check_failures == 1

    @pytest.mark.asyncio
    async def test_get_client(self, pool_config):
        """测试获取客户端"""
        pool = RedisPoolManager(pool_config)
        pool._initialized = True
        pool.client = AsyncMock()
        pool.metrics.is_healthy = True

        client = await pool.get_client()

        assert client is not None

    @pytest.mark.asyncio
    async def test_execute_command_success(self, pool_config):
        """测试执行命令成功"""
        pool = RedisPoolManager(pool_config)
        pool._initialized = True
        pool.client = AsyncMock()
        pool.client.execute_command = AsyncMock(return_value="OK")

        result = await pool.execute_command("PING")

        assert result == "OK"
        assert pool.metrics.total_requests == 1
        assert pool.metrics.failed_requests == 0

    @pytest.mark.asyncio
    async def test_execute_command_with_fallback(self, pool_config):
        """测试执行命令带降级"""
        pool = RedisPoolManager(pool_config)
        pool._initialized = True
        pool.client = AsyncMock(side_effect=ConnectionError())

        # 设置降级值
        result = await pool.execute_command("GET key", fallback="default_value")

        assert result == "default_value"
        assert pool.metrics.failed_requests == 1

    def test_get_stats(self, pool_config):
        """测试获取统计信息"""
        pool = RedisPoolManager(pool_config)
        pool._initialized = True
        pool.metrics.total_requests = 100
        pool.metrics.failed_requests = 5
        pool.metrics.is_healthy = True

        stats = pool.get_stats()

        assert stats["total_requests"] == 100
        assert stats["failed_requests"] == 5
        assert stats["is_healthy"] is True


# ============== 降级策略测试 ==============


class TestFallbackConfig:
    """降级配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = FallbackConfig()

        assert config.enabled is True
        assert config.strategy == FallbackStrategy.CACHE
        assert config.use_local_cache is True
        assert config.cache_ttl_seconds == 300
        assert config.circuit_breaker_enabled is True
        assert config.failure_threshold == 5
        assert config.recovery_timeout_seconds == 30


class TestCircuitBreaker:
    """熔断器测试"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed(self):
        """测试熔断器闭合状态"""
        manager = FallbackManager(FallbackConfig(failure_threshold=3))

        # 初始状态应该是闭合的
        state = manager._circuit_breaker_states["test_op"]
        assert state.state == "closed"

        # 应该允许执行
        can_execute = await manager._can_execute("test_op")
        assert can_execute is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """测试熔断器在多次失败后打开"""
        config = FallbackConfig(failure_threshold=3, recovery_timeout_seconds=1)
        manager = FallbackManager(config)

        # 记录 3 次失败
        for _ in range(3):
            await manager._record_failure("test_op")

        state = manager._circuit_breaker_states["test_op"]
        assert state.state == "open"
        assert state.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open(self):
        """测试熔断器半开状态"""
        config = FallbackConfig(failure_threshold=2, recovery_timeout_seconds=0.1)
        manager = FallbackManager(config)

        # 打开熔断器
        for _ in range(2):
            await manager._record_failure("test_op")

        # 等待恢复超时
        await asyncio.sleep(0.2)

        # 检查是否进入半开状态
        can_execute = await manager._can_execute("test_op")
        state = manager._circuit_breaker_states["test_op"]

        assert can_execute is True
        assert state.state == "half-open"

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """测试熔断器恢复"""
        config = FallbackConfig(failure_threshold=2, half_open_max_calls=2)
        manager = FallbackManager(config)

        # 打开熔断器
        for _ in range(2):
            await manager._record_failure("test_op")

        # 等待进入半开状态
        await asyncio.sleep(0.1)
        await manager._can_execute("test_op")

        # 记录成功
        for _ in range(2):
            await manager._record_success("test_op")

        state = manager._circuit_breaker_states["test_op"]
        assert state.state == "closed"
        assert state.failure_count == 0


class TestFallbackManager:
    """降级管理器测试"""

    @pytest.mark.asyncio
    async def test_execute_with_fallback_success(self):
        """测试执行成功"""
        manager = FallbackManager()

        async def success_op():
            return "success"

        result = await manager.execute_with_fallback("test_op", success_op)

        assert result == "success"
        assert manager._stats["total_requests"] == 1
        assert manager._stats["fallback_invoked"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_fallback_failure(self):
        """测试执行失败触发降级"""
        config = FallbackConfig(default_value="default")
        manager = FallbackManager(config)

        async def failing_op():
            raise Exception("Error")

        result = await manager.execute_with_fallback("test_op", failing_op)

        assert result == "default"
        assert manager._stats["fallback_invoked"] == 1

    @pytest.mark.asyncio
    async def test_fallback_decorator(self):
        """测试降级装饰器"""

        @fallback(operation_id="decorated_op", default_value="fallback_value")
        async def decorated_function():
            return "success"

        result = await decorated_function()
        assert result == "success"

    def test_get_stats(self):
        """测试获取统计信息"""
        manager = FallbackManager()
        manager._stats["total_requests"] = 100
        manager._stats["fallback_invoked"] = 10
        manager._stats["cache_hits"] = 50
        manager._stats["cache_misses"] = 50

        stats = manager.get_stats()

        assert stats["total_requests"] == 100
        assert stats["fallback_invoked"] == 10
        assert abs(stats["fallback_rate"] - 0.1) < 0.01
        assert abs(stats["cache_hit_rate"] - 0.5) < 0.01

    @pytest.mark.asyncio
    async def test_reset_circuit_breaker(self):
        """测试重置熔断器"""
        manager = FallbackManager()

        # 打开熔断器
        for _ in range(5):
            await manager._record_failure("test_op")

        state = manager._circuit_breaker_states["test_op"]
        assert state.state == "open"

        # 重置
        await manager.reset_circuit_breaker("test_op")

        state = manager._circuit_breaker_states["test_op"]
        assert state.state == "closed"
        assert state.failure_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
