"""降级策略管理模块（兼容层）

此模块已迁移至 storage.redis_fallback，保留此文件仅为向后兼容。
所有降级/熔断器功能统一由 storage.redis_fallback 提供。
"""

from storage.redis_fallback import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitStats,
    FallbackConfig,
    FallbackStrategy,
    LocalCache,
    RedisFallbackManager,
    get_redis_fallback_manager,
    init_redis_fallback,
    with_redis_fallback,
)

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "CircuitStats",
    "FallbackConfig",
    "FallbackStrategy",
    "LocalCache",
    "RedisFallbackManager",
    "get_redis_fallback_manager",
    "init_redis_fallback",
    "with_redis_fallback",
]
