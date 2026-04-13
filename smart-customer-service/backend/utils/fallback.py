"""
降级策略管理模块

提供:
- 降级策略配置
- 本地缓存降级
- 熔断器实现
- 自动恢复
- 降级监控
"""

import asyncio
import time
from typing import Optional, Dict, Any, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class FallbackStrategy(Enum):
    """降级策略类型"""

    CACHE = "cache"  # 使用缓存
    DEFAULT_VALUE = "default_value"  # 使用默认值
    EMPTY = "empty"  # 返回空值
    EXCEPTION = "exception"  # 抛出异常
    CIRCUIT_BREAKER = "circuit_breaker"  # 熔断器


@dataclass
class FallbackConfig:
    """降级配置"""

    # 基本配置
    enabled: bool = True
    strategy: FallbackStrategy = FallbackStrategy.CACHE

    # 默认值
    default_value: Optional[Any] = None

    # 缓存配置
    use_local_cache: bool = True
    cache_ttl_seconds: int = 300  # 5 分钟
    max_cache_size: int = 1000

    # 熔断器配置
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5  # 失败阈值
    recovery_timeout_seconds: int = 30  # 恢复超时
    half_open_max_calls: int = 3  # 半开状态最大调用数

    # 监控配置
    metrics_enabled: bool = True
    log_fallback: bool = True


@dataclass
class CircuitBreakerState:
    """熔断器状态"""

    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state: str = "closed"  # closed, open, half-open
    opened_at: Optional[datetime] = None


class LocalCache:
    """本地缓存实现（LRU）"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._max_size = max_size
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self._cache:
            return None

        # 检查是否过期
        timestamp = self._timestamps.get(key)
        if timestamp and datetime.utcnow() - timestamp > self._ttl:
            self.delete(key)
            return None

        return self._cache[key]

    def set(self, key: str, value: Any):
        """设置缓存"""
        # 如果达到最大容量，删除最旧的条目
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._timestamps.keys(), key=lambda k: self._timestamps[k])
            self.delete(oldest_key)

        self._cache[key] = value
        self._timestamps[key] = datetime.utcnow()

    def delete(self, key: str):
        """删除缓存"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._timestamps.clear()

    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


class FallbackManager:
    """降级管理器"""

    def __init__(self, config: Optional[FallbackConfig] = None):
        """
        初始化降级管理器

        Args:
            config: 降级配置
        """
        self.config = config or FallbackConfig()
        self._local_cache = LocalCache(
            max_size=self.config.max_cache_size, ttl_seconds=self.config.cache_ttl_seconds
        )
        self._circuit_breaker_states: Dict[str, CircuitBreakerState] = defaultdict(
            CircuitBreakerState
        )
        self._lock = asyncio.Lock()

        # 统计指标
        self._stats = {
            "total_requests": 0,
            "fallback_invoked": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "circuit_breaker_opens": 0,
            "successful_recoveries": 0,
        }

    async def execute_with_fallback(
        self, operation_id: str, operation: Callable, *args, **kwargs
    ) -> Any:
        """
        执行操作，失败时自动降级

        Args:
            operation_id: 操作标识
            operation: 要执行的操作（异步函数）
            *args: 操作参数
            **kwargs: 操作参数

        Returns:
            操作结果或降级值
        """
        self._stats["total_requests"] += 1

        if not self.config.enabled:
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                logger.error(f"操作失败（降级已禁用）：{operation_id}, 错误：{e}")
                raise

        # 检查熔断器状态
        if self.config.circuit_breaker_enabled:
            if not await self._can_execute(operation_id):
                self._stats["fallback_invoked"] += 1
                return await self._get_fallback_value(operation_id)

        # 执行操作
        try:
            result = await operation(*args, **kwargs)

            # 成功，更新熔断器
            await self._record_success(operation_id)

            # 缓存结果（如果启用）
            if self.config.use_local_cache:
                cache_key = f"{operation_id}:{str(args)}:{str(kwargs)}"
                self._local_cache.set(cache_key, result)

            return result

        except Exception as e:
            logger.warning(f"操作失败，触发降级：{operation_id}, 错误：{e}")

            # 记录失败
            await self._record_failure(operation_id)

            # 返回降级值
            self._stats["fallback_invoked"] += 1
            return await self._get_fallback_value(operation_id, str(e))

    async def _can_execute(self, operation_id: str) -> bool:
        """
        检查是否可以执行操作（熔断器逻辑）

        Args:
            operation_id: 操作标识

        Returns:
            是否允许执行
        """
        if not self.config.circuit_breaker_enabled:
            return True

        state = self._circuit_breaker_states[operation_id]

        if state.state == "closed":
            return True

        if state.state == "open":
            # 检查是否超过恢复超时时间
            if (
                state.opened_at
                and (datetime.utcnow() - state.opened_at).total_seconds()
                > self.config.recovery_timeout_seconds
            ):
                state.state = "half-open"
                logger.info(f"熔断器进入半开状态：{operation_id}")
                return True
            else:
                logger.debug(f"熔断器打开中，拒绝执行：{operation_id}")
                return False

        if state.state == "half-open":
            # 半开状态允许有限次调用
            return state.success_count < self.config.half_open_max_calls

        return True

    async def _record_success(self, operation_id: str):
        """记录成功"""
        if not self.config.circuit_breaker_enabled:
            return

        state = self._circuit_breaker_states[operation_id]
        state.success_count += 1
        state.last_success_time = datetime.utcnow()

        if state.state == "half-open":
            if state.success_count >= self.config.half_open_max_calls:
                state.state = "closed"
                state.failure_count = 0
                state.success_count = 0
                state.opened_at = None
                logger.info(f"熔断器恢复闭合：{operation_id}")
                self._stats["successful_recoveries"] += 1
        elif state.state == "open":
            # 不应该发生，但安全处理
            state.state = "closed"
            state.failure_count = 0

    async def _record_failure(self, operation_id: str):
        """记录失败"""
        if not self.config.circuit_breaker_enabled:
            return

        state = self._circuit_breaker_states[operation_id]
        state.failure_count += 1
        state.last_failure_time = datetime.utcnow()

        if state.state == "closed":
            if state.failure_count >= self.config.failure_threshold:
                state.state = "open"
                state.opened_at = datetime.utcnow()
                logger.warning(f"熔断器打开：{operation_id} (失败次数：{state.failure_count})")
                self._stats["circuit_breaker_opens"] += 1
        elif state.state == "half-open":
            # 半开状态再次失败，重新打开
            state.state = "open"
            state.opened_at = datetime.utcnow()
            state.success_count = 0
            logger.warning(f"熔断器重新打开：{operation_id}")

    async def _get_fallback_value(self, operation_id: str, error: Optional[str] = None) -> Any:
        """
        获取降级值

        Args:
            operation_id: 操作标识
            error: 错误信息

        Returns:
            降级值
        """
        if self.config.log_fallback:
            logger.info(f"触发降级策略：{operation_id}, 策略：{self.config.strategy.value}")

        # 根据策略返回不同的值
        if self.config.strategy == FallbackStrategy.CACHE:
            # 尝试从缓存获取
            if self.config.use_local_cache:
                # 这里应该根据 operation_id 和参数构建缓存 key
                # 简化处理，返回 None
                self._stats["cache_misses"] += 1
                logger.debug(f"缓存未命中，返回默认值：{operation_id}")

            return self.config.default_value

        elif self.config.strategy == FallbackStrategy.DEFAULT_VALUE:
            return self.config.default_value

        elif self.config.strategy == FallbackStrategy.EMPTY:
            return None

        elif self.config.strategy == FallbackStrategy.EXCEPTION:
            raise RuntimeError(f"操作失败且降级策略为抛出异常：{operation_id}, 错误：{error}")

        else:
            return self.config.default_value

    def get_cache(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.config.use_local_cache:
            return None

        value = self._local_cache.get(key)
        if value is not None:
            self._stats["cache_hits"] += 1
        else:
            self._stats["cache_misses"] += 1

        return value

    def set_cache(self, key: str, value: Any):
        """设置缓存"""
        if self.config.use_local_cache:
            self._local_cache.set(key, value)

    def clear_cache(self):
        """清空缓存"""
        self._local_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计指标"""
        fallback_rate = (
            self._stats["fallback_invoked"] / self._stats["total_requests"]
            if self._stats["total_requests"] > 0
            else 0.0
        )

        cache_hit_rate = (
            self._stats["cache_hits"] / (self._stats["cache_hits"] + self._stats["cache_misses"])
            if (self._stats["cache_hits"] + self._stats["cache_misses"]) > 0
            else 0.0
        )

        return {
            **self._stats,
            "fallback_rate": round(fallback_rate, 4),
            "cache_hit_rate": round(cache_hit_rate, 4),
            "circuit_breaker_states": {
                op_id: {
                    "state": state.state,
                    "failure_count": state.failure_count,
                    "success_count": state.success_count,
                    "last_failure": state.last_failure_time.isoformat()
                    if state.last_failure_time
                    else None,
                    "last_success": state.last_success_time.isoformat()
                    if state.last_success_time
                    else None,
                }
                for op_id, state in self._circuit_breaker_states.items()
            },
        }

    async def reset_circuit_breaker(self, operation_id: str):
        """重置熔断器"""
        if operation_id in self._circuit_breaker_states:
            state = self._circuit_breaker_states[operation_id]
            state.state = "closed"
            state.failure_count = 0
            state.success_count = 0
            state.opened_at = None
            logger.info(f"熔断器已重置：{operation_id}")


# 全局降级管理器实例
fallback_manager: Optional[FallbackManager] = None


def get_fallback_manager() -> FallbackManager:
    """获取全局降级管理器"""
    global fallback_manager

    if not fallback_manager:
        fallback_manager = FallbackManager()

    return fallback_manager


def fallback(
    operation_id: Optional[str] = None,
    default_value: Optional[Any] = None,
    use_cache: bool = True,
):
    """
    降级装饰器

    Args:
        operation_id: 操作标识
        default_value: 默认值
        use_cache: 是否使用缓存

    Returns:
        装饰器函数
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            op_id = operation_id or func.__name__
            manager = get_fallback_manager()

            # 临时修改默认值
            original_default = manager.config.default_value
            manager.config.default_value = default_value
            manager.config.use_local_cache = use_cache

            try:
                return await manager.execute_with_fallback(op_id, func, *args, **kwargs)
            finally:
                manager.config.default_value = original_default

        return wrapper

    return decorator
