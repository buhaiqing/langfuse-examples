"""
存储层模块

提供:
- Redis 客户端（会话缓存）
- PostgreSQL 客户端（持久化存储）
- ChromaDB 客户端（向量数据库）
- MinIO 客户端（文档存储）
- Redis 降级预案
"""

from storage.redis_client import (
    RedisClient,
    redis_client,
    get_redis_client,
    ConversationState,
    RedisKeys,
)

from storage.redis_pool import (
    RedisPoolManager,
    RedisPoolConfig,
    PoolMetrics,
    get_redis_pool,
    init_redis_pool,
)

from storage.redis_fallback import (
    CircuitState,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitStats,
    LocalCache,
    FallbackStrategy,
    FallbackConfig,
    RedisFallbackManager,
    with_redis_fallback,
    get_redis_fallback_manager,
    init_redis_fallback,
)

from storage.redis_fallback_client import (
    FallbackRedisClient,
    get_fallback_redis_client,
    init_fallback_redis_client,
)

__all__ = [
    # Redis 客户端
    "RedisClient",
    "redis_client",
    "get_redis_client",
    "ConversationState",
    "RedisKeys",
    # Redis 连接池
    "RedisPoolManager",
    "RedisPoolConfig",
    "PoolMetrics",
    "get_redis_pool",
    "init_redis_pool",
    # Redis 降级
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
    # 降级客户端
    "FallbackRedisClient",
    "get_fallback_redis_client",
    "init_fallback_redis_client",
]