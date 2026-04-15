"""
Redis 降级机制测试

测试:
- 熔断器状态转换
- 本地缓存功能
- 降级策略应用
- 自动恢复机制
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from storage.redis_fallback import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    LocalCache,
    FallbackStrategy,
    FallbackConfig,
    RedisFallbackManager,
)


# ==================== 熔断器测试 ====================
class TestCircuitBreaker:
    """熔断器测试"""

    def test_initial_state_is_closed(self):
        """测试初始状态为关闭"""
        cb = CircuitBreaker("test", CircuitBreakerConfig())
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_can_execute_when_closed(self):
        """测试关闭状态允许执行"""
        cb = CircuitBreaker("test", CircuitBreakerConfig())
        assert await cb.can_execute() is True

    @pytest.mark.asyncio
    async def test_transitions_to_open_on_failures(self):
        """测试连续失败触发熔断"""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        # 记录失败
        for i in range(3):
            await cb.record_failure(Exception(f"Error {i}"))

        assert cb.state == CircuitState.OPEN
        assert await cb.can_execute() is False

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self):
        """测试超时后转换为半开"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,  # 1秒
        )
        cb = CircuitBreaker("test", config)

        # 触发熔断
        await cb.record_failure(Exception("Error 1"))
        await cb.record_failure(Exception("Error 2"))

        assert cb.state == CircuitState.OPEN

        # 等待恢复超时
        await asyncio.sleep(1.5)

        # 应该允许执行（半开状态）
        assert await cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(self):
        """测试半开状态成功恢复"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,
            success_threshold=2,
        )
        cb = CircuitBreaker("test", config)

        # 触发熔断
        await cb.record_failure(Exception("Error 1"))
        await cb.record_failure(Exception("Error 2"))
        assert cb.state == CircuitState.OPEN

        # 等待恢复超时
        await asyncio.sleep(1.5)
        await cb.can_execute()  # 转换到半开

        # 记录成功
        await cb.record_success()
        await cb.record_success()

        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self):
        """测试半开状态失败重新熔断"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,
        )
        cb = CircuitBreaker("test", config)

        # 触发熔断
        await cb.record_failure(Exception("Error 1"))
        await cb.record_failure(Exception("Error 2"))
        assert cb.state == CircuitState.OPEN

        # 等待恢复超时
        await asyncio.sleep(1.5)
        await cb.can_execute()  # 转换到半开

        # 半开状态下失败
        await cb.record_failure(Exception("Error in half-open"))

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_failure_rate_threshold(self):
        """测试失败率阈值触发熔断"""
        config = CircuitBreakerConfig(
            failure_threshold=10,  # 高阈值，不触发连续失败
            failure_rate_threshold=0.5,
            min_requests_for_rate=10,
        )
        cb = CircuitBreaker("test", config)

        # 10次请求，6次失败（60%失败率）
        for i in range(10):
            if i < 6:
                await cb.record_failure(Exception(f"Error {i}"))
            else:
                await cb.record_success()

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_reset_circuit_breaker(self):
        """测试重置熔断器"""
        cb = CircuitBreaker("test", CircuitBreakerConfig())

        # 触发熔断
        for i in range(5):
            await cb.record_failure(Exception(f"Error {i}"))

        assert cb.state == CircuitState.OPEN

        # 重置
        await cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.stats.consecutive_failures == 0


# ==================== 本地缓存测试 ====================
class TestLocalCache:
    """本地缓存测试"""

    def test_set_and_get(self):
        """测试设置和获取"""
        cache = LocalCache(max_size=100, default_ttl=300)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self):
        """测试获取不存在的键"""
        cache = LocalCache()
        assert cache.get("missing") is None

    def test_ttl_expiration(self):
        """测试 TTL 过期"""
        cache = LocalCache(max_size=100, default_ttl=1)  # 1秒 TTL

        cache.set("key1", "value1", ttl=1)

        # 立即获取应该有值
        assert cache.get("key1") == "value1"

        # 等待过期
        time.sleep(1.5)

        # 过期后应该返回 None
        assert cache.get("key1") is None

    def test_lru_eviction(self):
        """测试 LRU 淘汰"""
        cache = LocalCache(max_size=3, default_ttl=300)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # 应该淘汰最旧的 "a"

        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_lru_access_order(self):
        """测试 LRU 访问顺序"""
        cache = LocalCache(max_size=3, default_ttl=300)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        # 访问 "a"，使其变为最新
        cache.get("a")

        # 添加新项，应该淘汰 "b"（最旧）
        cache.set("d", 4)

        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_delete(self):
        """测试删除"""
        cache = LocalCache()
        cache.set("key1", "value1")

        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_missing(self):
        """测试删除不存在的键"""
        cache = LocalCache()
        assert cache.delete("missing") is False

    def test_clear(self):
        """测试清空"""
        cache = LocalCache()
        cache.set("a", 1)
        cache.set("b", 2)

        cache.clear()

        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_cleanup_expired(self):
        """测试清理过期"""
        cache = LocalCache(default_ttl=1)

        cache.set("a", 1, ttl=1)
        cache.set("b", 2, ttl=1)
        cache.set("c", 3, ttl=10)  # 长 TTL

        time.sleep(1.5)

        cache.cleanup_expired()

        stats = cache.get_stats()
        assert stats["expired"] >= 2

    def test_stats(self):
        """测试统计信息"""
        cache = LocalCache()

        cache.set("a", 1)
        cache.get("a")  # hit
        cache.get("missing")  # miss

        stats = cache.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5


# ==================== 降级管理器测试 ====================
class TestRedisFallbackManager:
    """降级管理器测试"""

    def test_initial_state(self):
        """测试初始状态"""
        manager = RedisFallbackManager()
        assert manager._is_degraded is False
        assert manager.circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_execute_with_fallback_success(self):
        """测试成功执行"""
        manager = RedisFallbackManager()

        async def operation():
            return "success"

        result = await manager.execute_with_fallback(
            operation=operation,
            key="test_key",
            fallback_value="fallback",
        )

        assert result == "success"
        assert manager._is_degraded is False

    @pytest.mark.asyncio
    async def test_execute_with_fallback_on_failure(self):
        """测试失败时降级"""
        config = CircuitBreakerConfig(failure_threshold=1)
        manager = RedisFallbackManager(circuit_config=config)

        async def failing_operation():
            raise Exception("Redis error")

        # 第一次失败
        result = await manager.execute_with_fallback(
            operation=failing_operation,
            key="test_key",
            fallback_value="fallback",
        )

        assert result == "fallback"
        assert manager._is_degraded is True

    @pytest.mark.asyncio
    async def test_fallback_from_cache(self):
        """测试从本地缓存降级"""
        config = FallbackConfig(strategy=FallbackStrategy.CACHE)
        manager = RedisFallbackManager(fallback_config=config)

        # 先成功执行，存入缓存
        async def success_op():
            return "cached_value"

        await manager.execute_with_fallback(
            operation=success_op,
            key="cache_key",
            fallback_value="default",
        )

        # 然后触发熔断
        await manager.circuit_breaker.record_failure(Exception("Error"))
        await manager.circuit_breaker.record_failure(Exception("Error"))
        await manager.circuit_breaker.record_failure(Exception("Error"))
        await manager.circuit_breaker.record_failure(Exception("Error"))
        await manager.circuit_breaker.record_failure(Exception("Error"))

        # 失败操作，应该从缓存获取
        async def failing_op():
            raise Exception("Redis error")

        result = await manager.execute_with_fallback(
            operation=failing_op,
            key="cache_key",
            fallback_value="default",
        )

        assert result == "cached_value"

    @pytest.mark.asyncio
    async def test_fallback_default_value(self):
        """测试使用默认值降级"""
        config = FallbackConfig(
            strategy=FallbackStrategy.DEFAULT_VALUE,
            default_value="default_response",
        )
        manager = RedisFallbackManager(fallback_config=config)

        # 触发熔断
        for i in range(5):
            await manager.circuit_breaker.record_failure(Exception("Error"))

        async def failing_op():
            raise Exception("Redis error")

        result = await manager.execute_with_fallback(
            operation=failing_op,
            key="test_key",
        )

        assert result == "default_response"

    @pytest.mark.asyncio
    async def test_fallback_raise_exception(self):
        """测试抛出异常降级"""
        config = FallbackConfig(strategy=FallbackStrategy.RAISE)
        manager = RedisFallbackManager(fallback_config=config)

        # 触发熔断
        for i in range(5):
            await manager.circuit_breaker.record_failure(Exception("Error"))

        async def failing_op():
            raise Exception("Redis error")

        with pytest.raises(ConnectionError, match="Redis 服务不可用"):
            await manager.execute_with_fallback(
                operation=failing_op,
                key="test_key",
            )

    @pytest.mark.asyncio
    async def test_auto_recovery(self):
        """测试自动恢复"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,
        )
        manager = RedisFallbackManager(circuit_config=config)

        # 触发熔断
        await manager.circuit_breaker.record_failure(Exception("Error 1"))
        await manager.circuit_breaker.record_failure(Exception("Error 2"))

        assert manager.circuit_breaker.state == CircuitState.OPEN

        # 启动自动恢复
        async def check_recovery():
            return True  # 模拟恢复

        await manager.start_auto_recovery(check_recovery)

        # 等待恢复检查
        await asyncio.sleep(2)

        # 检查状态
        assert manager.circuit_breaker.state == CircuitState.CLOSED

        await manager.stop_auto_recovery()

    @pytest.mark.asyncio
    async def test_reset_manager(self):
        """测试重置管理器"""
        manager = RedisFallbackManager()

        # 触发降级
        for i in range(5):
            await manager.circuit_breaker.record_failure(Exception("Error"))

        manager._is_degraded = True

        # 重置
        await manager.reset()

        assert manager.circuit_breaker.state == CircuitState.CLOSED
        assert manager._is_degraded is False

    def test_get_status(self):
        """测试获取状态"""
        manager = RedisFallbackManager()
        status = manager.get_status()

        assert "is_degraded" in status
        assert "circuit_breaker" in status
        assert "local_cache" in status
        assert "fallback_strategy" in status


# ==================== 集成测试 ====================
class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_fallback_flow(self):
        """测试完整降级流程"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=2,
            success_threshold=2,
        )
        fallback_config = FallbackConfig(
            strategy=FallbackStrategy.CACHE,
            cache_ttl=60,
        )
        manager = RedisFallbackManager(
            circuit_config=config,
            fallback_config=fallback_config,
        )

        # 1. 正常执行
        async def normal_op():
            return "normal_result"

        result = await manager.execute_with_fallback(
            operation=normal_op,
            key="test_key",
            fallback_value="default",
        )
        assert result == "normal_result"
        assert manager._is_degraded is False

        # 2. 触发失败
        async def failing_op():
            raise Exception("Redis connection lost")

        for i in range(3):
            await manager.execute_with_fallback(
                operation=failing_op,
                key="test_key",
                fallback_value="default",
            )

        # 3. 熔断生效
        assert manager.circuit_breaker.state == CircuitState.OPEN

        result = await manager.execute_with_fallback(
            operation=failing_op,
            key="test_key",
            fallback_value="default",
        )
        assert result == "normal_result"  # 从缓存获取
        assert manager._is_degraded is True

        # 4. 等待恢复窗口
        await asyncio.sleep(2.5)

        # 5. 半开状态测试
        assert await manager.circuit_breaker.can_execute()

        # 6. 成功恢复
        async def recovery_op():
            return "recovered"

        for i in range(2):
            result = await manager.execute_with_fallback(
                operation=recovery_op,
                key="test_key",
                fallback_value="default",
            )

        # 7. 恢复正常
        assert manager.circuit_breaker.state == CircuitState.CLOSED
        assert manager._is_degraded is False