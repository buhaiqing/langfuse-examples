"""
Redis 降级预案模块

提供:
- 熔断器 (Circuit Breaker): 自动断开故障服务请求，防止雪崩
- 本地缓存 (Local Cache): Redis 不可用时的降级缓存
- 自动恢复 (Auto Recovery): 定期尝试恢复 Redis 连接
- 降级策略管理: 可配置的降级策略和阈值
"""

import asyncio
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any

from utils import utcnow

logger = logging.getLogger(__name__)


# ==================== 熔断器状态 ====================
class CircuitState(Enum):
    """熔断器状态"""

    CLOSED = "closed"  # 正常状态，允许请求通过
    OPEN = "open"  # 熔断状态，拒绝所有请求
    HALF_OPEN = "half_open"  # 半开状态，允许部分请求测试恢复


@dataclass
class CircuitStats:
    """熔断器统计"""

    total_requests: int = 0
    success_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: datetime | None = None
    last_success_time: datetime | None = None
    last_state_change: datetime | None = None


# ==================== 熔断器配置 ====================
@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""

    # 熔断阈值
    failure_threshold: int = 5  # 连续失败次数阈值，触发熔断
    failure_rate_threshold: float = 0.5  # 失败率阈值 (50%)，触发熔断
    min_requests_for_rate: int = 10  # 计算失败率的最小请求数

    # 恢复配置
    recovery_timeout: int = 30  # 熔断后等待恢复的时间（秒）
    half_open_max_calls: int = 3  # 半开状态最大测试调用数
    success_threshold: int = 2  # 半开状态连续成功次数，恢复为关闭

    # 超时配置
    call_timeout: float = 5.0  # 单次调用超时时间（秒）

    # 监控配置
    stats_window_seconds: int = 60  # 统计窗口时间（秒）


# ==================== 熔断器实现 ====================
class CircuitBreaker:
    """
    熔断器实现

    状态转换:
    CLOSED -> OPEN: 连续失败达到阈值 或 失败率超过阈值
    OPEN -> HALF_OPEN: 等待恢复超时后
    HALF_OPEN -> CLOSED: 连续成功达到阈值
    HALF_OPEN -> OPEN: 再次失败
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()
        self._lock = asyncio.Lock()
        self._half_open_calls = 0
        self._opened_at: float | None = None

    async def can_execute(self) -> bool:
        """检查是否允许执行请求"""
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                # 检查是否到达恢复时间
                if self._should_attempt_recovery():
                    self._transition_to_half_open()
                    return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                # 半开状态限制调用次数
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return False

    def _should_attempt_recovery(self) -> bool:
        """检查是否应该尝试恢复"""
        if not self._opened_at:
            return False
        elapsed = time.time() - self._opened_at
        return elapsed >= self.config.recovery_timeout

    def _transition_to_open(self):
        """转换到熔断状态"""
        if self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            self._opened_at = time.time()
            self.stats.last_state_change = utcnow()
            self._half_open_calls = 0
            logger.warning(
                f"熔断器 [{self.name}] 打开 - 连续失败 {self.stats.consecutive_failures}"
            )

    def _transition_to_half_open(self):
        """转换到半开状态"""
        self.state = CircuitState.HALF_OPEN
        self.stats.last_state_change = utcnow()
        self._half_open_calls = 0
        logger.info(f"熔断器 [{self.name}] 半开 - 尝试恢复")

    def _transition_to_closed(self):
        """转换到正常状态"""
        if self.state != CircuitState.CLOSED:
            self.state = CircuitState.CLOSED
            self._opened_at = None
            self.stats.last_state_change = utcnow()
            self._half_open_calls = 0
            self.stats.consecutive_failures = 0
            logger.info(f"熔断器 [{self.name}] 关闭 - 服务恢复")

    async def record_success(self):
        """记录成功"""
        async with self._lock:
            self.stats.total_requests += 1
            self.stats.success_requests += 1
            self.stats.consecutive_successes += 1
            self.stats.consecutive_failures = 0
            self.stats.last_success_time = utcnow()

            if self.state == CircuitState.HALF_OPEN:
                # 半开状态下，连续成功达到阈值则恢复
                if self.stats.consecutive_successes >= self.config.success_threshold:
                    self._transition_to_closed()

    async def record_failure(self, error: Exception | None = None):
        """记录失败"""
        async with self._lock:
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.consecutive_failures += 1
            self.stats.consecutive_successes = 0
            self.stats.last_failure_time = utcnow()

            if self.state == CircuitState.HALF_OPEN:
                # 半开状态下失败，立即熔断
                self._transition_to_open()
                logger.warning(f"熔断器 [{self.name}] 半开状态失败，重新熔断")

            elif self.state == CircuitState.CLOSED:
                # 检查是否需要熔断
                if self._should_open():
                    self._transition_to_open()

    def _should_open(self) -> bool:
        """判断是否应该熔断"""
        # 连续失败达到阈值
        if self.stats.consecutive_failures >= self.config.failure_threshold:
            return True

        # 失败率超过阈值（需要足够请求数）
        if self.stats.total_requests >= self.config.min_requests_for_rate:
            failure_rate = self.stats.failed_requests / self.stats.total_requests
            if failure_rate >= self.config.failure_rate_threshold:
                return True

        return False

    def get_state(self) -> CircuitState:
        """获取当前状态"""
        return self.state

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_requests": self.stats.total_requests,
            "success_requests": self.stats.success_requests,
            "failed_requests": self.stats.failed_requests,
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "failure_rate": (
                self.stats.failed_requests / self.stats.total_requests
                if self.stats.total_requests > 0
                else 0
            ),
            "last_failure_time": (
                self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None
            ),
            "last_success_time": (
                self.stats.last_success_time.isoformat() if self.stats.last_success_time else None
            ),
            "last_state_change": (
                self.stats.last_state_change.isoformat() if self.stats.last_state_change else None
            ),
            "opened_at": self._opened_at,
            "recovery_timeout": self.config.recovery_timeout,
        }

    async def reset(self):
        """重置熔断器"""
        async with self._lock:
            self.state = CircuitState.CLOSED
            self.stats = CircuitStats()
            self._opened_at = None
            self._half_open_calls = 0
            logger.info(f"熔断器 [{self.name}] 已重置")


# ==================== 本地缓存实现 ====================
class LocalCache:
    """
    线程安全的本地内存缓存

    特性:
    - TTL 过期清理
    - LRU 淘汰策略
    - 最大容量限制
    - 统计信息
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict = OrderedDict()
        self._ttl: dict[str, float] = {}
        self._lock = threading.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expired": 0,
            "sets": 0,
        }

    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        with self._lock:
            # 检查过期
            if key in self._ttl and time.time() > self._ttl[key]:
                self._remove(key)
                self._stats["expired"] += 1
                self._stats["misses"] += 1
                return None

            if key in self._cache:
                # LRU: 移到末尾
                self._cache.move_to_end(key)
                self._stats["hits"] += 1
                return self._cache[key]

            self._stats["misses"] += 1
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """设置缓存值"""
        with self._lock:
            ttl = ttl or self.default_ttl

            # 如果已存在，先删除
            if key in self._cache:
                self._remove(key)

            # 检查容量，淘汰最旧的
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                self._remove(oldest_key)
                self._stats["evictions"] += 1

            # 添加新值
            self._cache[key] = value
            self._ttl[key] = time.time() + ttl
            self._stats["sets"] += 1

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                self._remove(key)
                return True
            return False

    def _remove(self, key: str):
        """内部删除方法"""
        self._cache.pop(key, None)
        self._ttl.pop(key, None)

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._ttl.clear()

    def cleanup_expired(self):
        """清理过期缓存"""
        current_time = time.time()
        with self._lock:
            expired_keys = [key for key, expiry in self._ttl.items() if current_time > expiry]
            for key in expired_keys:
                self._remove(key)
                self._stats["expired"] += 1

            if expired_keys:
                logger.debug(f"清理过期缓存: {len(expired_keys)} 个")

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": round(hit_rate, 4),
                "evictions": self._stats["evictions"],
                "expired": self._stats["expired"],
                "sets": self._stats["sets"],
            }

    def keys(self) -> list:
        """获取所有键"""
        with self._lock:
            return list(self._cache.keys())


# ==================== 降级策略 ====================
class FallbackStrategy(Enum):
    """降级策略"""

    CACHE = "cache"  # 使用本地缓存
    DEFAULT_VALUE = "default"  # 使用默认值
    EMPTY = "empty"  # 返回空值
    RAISE = "raise"  # 抛出异常


@dataclass
class FallbackConfig:
    """降级配置"""

    strategy: FallbackStrategy = FallbackStrategy.CACHE
    default_value: Any | None = None
    cache_ttl: int = 300  # 本地缓存 TTL（秒）
    cache_max_size: int = 1000  # 本地缓存最大容量

    # 自动恢复配置
    auto_recovery_enabled: bool = True
    recovery_check_interval: int = 30  # 恢复检查间隔（秒）
    recovery_max_attempts: int = 3  # 最大恢复尝试次数


# ==================== Redis 降级管理器 ====================
class RedisFallbackManager:
    """
    Redis 降级管理器

    整合熔断器、本地缓存和自动恢复机制
    """

    def __init__(
        self,
        circuit_config: CircuitBreakerConfig | None = None,
        fallback_config: FallbackConfig | None = None,
    ):
        self.circuit_breaker = CircuitBreaker(
            name="redis",
            config=circuit_config or CircuitBreakerConfig(),
        )
        self.fallback_config = fallback_config or FallbackConfig()
        self.local_cache = LocalCache(
            max_size=self.fallback_config.cache_max_size,
            default_ttl=self.fallback_config.cache_ttl,
        )

        self._recovery_task: asyncio.Task | None = None
        self._recovery_attempts = 0
        self._is_degraded = False
        self._degraded_at: datetime | None = None

    async def execute_with_fallback(
        self,
        operation: Callable[[], Awaitable[Any]],
        key: str | None = None,
        fallback_value: Any | None = None,
        cache_ttl: int | None = None,
    ) -> Any:
        """
        执行操作，支持降级

        Args:
            operation: Redis 操作函数
            key: 缓存键（用于本地缓存）
            fallback_value: 降级默认值
            cache_ttl: 缓存 TTL

        Returns:
            操作结果或降级值
        """
        # 检查熔断器状态
        if not await self.circuit_breaker.can_execute():
            logger.warning("Redis 熔断器打开，使用降级策略")
            return self._apply_fallback(key, fallback_value)

        try:
            # 执行 Redis 操作（带超时）
            result = await asyncio.wait_for(
                operation(),
                timeout=self.circuit_breaker.config.call_timeout,
            )

            # 记录成功
            await self.circuit_breaker.record_success()

            # 更新本地缓存
            if key and self.fallback_config.strategy == FallbackStrategy.CACHE:
                self.local_cache.set(key, result, ttl=cache_ttl)

            # 如果之前是降级状态，现在恢复了
            if self._is_degraded:
                self._is_degraded = False
                logger.info("Redis 服务已恢复，退出降级状态")

            return result

        except asyncio.TimeoutError as e:
            await self.circuit_breaker.record_failure(e)
            logger.warning("Redis 操作超时，使用降级策略")
            return self._apply_fallback(key, fallback_value)

        except Exception as e:
            await self.circuit_breaker.record_failure(e)
            logger.error(f"Redis 操作失败: {e}，使用降级策略")
            return self._apply_fallback(key, fallback_value)

    def _apply_fallback(
        self,
        key: str | None,
        fallback_value: Any | None,
    ) -> Any:
        """应用降级策略"""
        if not self._is_degraded:
            self._is_degraded = True
            self._degraded_at = utcnow()
            logger.warning("进入 Redis 降级状态")

        strategy = self.fallback_config.strategy

        if strategy == FallbackStrategy.CACHE:
            # 尝试从本地缓存获取
            if key:
                cached = self.local_cache.get(key)
                if cached is not None:
                    logger.debug(f"使用本地缓存: {key}")
                    return cached
            # 缓存未命中，使用默认值
            return self._get_default_value(fallback_value)

        elif strategy == FallbackStrategy.DEFAULT_VALUE:
            return self._get_default_value(fallback_value)

        elif strategy == FallbackStrategy.EMPTY:
            return None

        elif strategy == FallbackStrategy.RAISE:
            raise ConnectionError("Redis 服务不可用")

        return None

    def _get_default_value(self, fallback_value: Any | None) -> Any:
        """获取默认值"""
        if fallback_value is not None:
            return fallback_value
        return self.fallback_config.default_value

    async def start_auto_recovery(self, check_func: Callable[[], Awaitable[bool]]):
        """
        启动自动恢复检查

        Args:
            check_func: 检查 Redis 是否恢复的函数
        """
        if not self.fallback_config.auto_recovery_enabled:
            return

        self._recovery_task = asyncio.create_task(self._recovery_loop(check_func))
        logger.info("启动 Redis 自动恢复检查")

    async def _recovery_loop(self, check_func: Callable[[], Awaitable[bool]]):
        """恢复检查循环"""
        while True:
            await asyncio.sleep(self.fallback_config.recovery_check_interval)

            # 只有在降级状态才检查恢复
            if not self._is_degraded:
                continue

            if self._recovery_attempts >= self.fallback_config.recovery_max_attempts:
                logger.warning("达到最大恢复尝试次数，停止自动恢复")
                continue

            try:
                is_recovered = await check_func()

                if is_recovered:
                    # 重置熔断器
                    await self.circuit_breaker.reset()
                    self._is_degraded = False
                    self._recovery_attempts = 0
                    logger.info("Redis 服务已恢复，熔断器重置")
                else:
                    self._recovery_attempts += 1
                    logger.debug(f"Redis 恢复检查失败，尝试次数: {self._recovery_attempts}")

            except Exception as e:
                logger.error(f"恢复检查异常: {e}")
                self._recovery_attempts += 1

    async def stop_auto_recovery(self):
        """停止自动恢复检查"""
        if self._recovery_task:
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass
            self._recovery_task = None
            logger.info("停止 Redis 自动恢复检查")

    def cleanup_cache(self):
        """清理过期缓存"""
        self.local_cache.cleanup_expired()

    def get_status(self) -> dict[str, Any]:
        """获取降级状态"""
        return {
            "is_degraded": self._is_degraded,
            "degraded_at": (self._degraded_at.isoformat() if self._degraded_at else None),
            "recovery_attempts": self._recovery_attempts,
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "local_cache": self.local_cache.get_stats(),
            "fallback_strategy": self.fallback_config.strategy.value,
        }

    async def reset(self):
        """重置降级管理器"""
        await self.circuit_breaker.reset()
        self.local_cache.clear()
        self._is_degraded = False
        self._degraded_at = None
        self._recovery_attempts = 0
        logger.info("Redis 降级管理器已重置")


# ==================== 装饰器 ====================
def with_redis_fallback(
    key: str | None = None,
    fallback_value: Any | None = None,
    cache_ttl: int | None = None,
):
    """
    Redis 操作降级装饰器

    使用示例:
    ```python
    @with_redis_fallback(key="user:{user_id}", fallback_value={})
    async def get_user_profile(user_id: str):
        return await redis_client.get_user_profile(user_id)
    ```
    """

    def decorator(func: Callable[[], Awaitable[Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取全局降级管理器
            manager = get_redis_fallback_manager()

            return await manager.execute_with_fallback(
                operation=lambda: func(*args, **kwargs),
                key=key,
                fallback_value=fallback_value,
                cache_ttl=cache_ttl,
            )

        return wrapper

    return decorator


# ==================== 全局实例 ====================
_redis_fallback_manager: RedisFallbackManager | None = None


def get_redis_fallback_manager() -> RedisFallbackManager:
    """获取全局 Redis 降级管理器"""
    global _redis_fallback_manager

    if _redis_fallback_manager is None:
        _redis_fallback_manager = RedisFallbackManager()

    return _redis_fallback_manager


def init_redis_fallback(
    circuit_config: CircuitBreakerConfig | None = None,
    fallback_config: FallbackConfig | None = None,
) -> RedisFallbackManager:
    """初始化 Redis 降级管理器"""
    global _redis_fallback_manager

    _redis_fallback_manager = RedisFallbackManager(
        circuit_config=circuit_config,
        fallback_config=fallback_config,
    )

    logger.info("Redis 降级管理器已初始化")
    return _redis_fallback_manager


# ==================== 导出 ====================
__all__ = [
    "CircuitState",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitStats",
    "LocalCache",
    "FallbackStrategy",
    "FallbackConfig",
    "RedisFallbackManager",
    "with_redis_fallback",
    "get_redis_fallback_manager",
    "init_redis_fallback",
]
