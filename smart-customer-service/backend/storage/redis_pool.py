"""Redis 连接池管理模块（兼容层）

此模块已合并至 storage.redis_client，保留此文件仅为向后兼容。
RedisClient 已内置连接池管理、健康检查和监控指标。
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from storage.redis_client import (
    redis_client,
)

logger = logging.getLogger(__name__)


@dataclass
class RedisPoolConfig:
    """Redis 连接池配置（兼容旧接口）"""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    max_connections: int = 100
    min_idle_connections: int = 10
    connection_timeout: float = 30.0
    socket_timeout: float = 5.0
    socket_keepalive: bool = True
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    max_health_check_failures: int = 3
    enable_fallback: bool = True
    fallback_enabled: bool = True


@dataclass
class PoolMetrics:
    """连接池指标（兼容旧接口）"""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    avg_acquire_time_ms: float = 0.0
    max_acquire_time_ms: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    health_check_failures: int = 0
    last_health_check: datetime | None = None
    is_healthy: bool = True
    is_degraded: bool = False
    fallback_active: bool = False
    last_failure_time: datetime | None = None


class RedisPoolManager:
    """Redis 连接池管理器（兼容层，委托给 RedisClient）"""

    def __init__(self, config: RedisPoolConfig | None = None):
        self.config = config or RedisPoolConfig()
        self.metrics = PoolMetrics()
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化连接（委托给全局 RedisClient）"""
        try:
            await redis_client.connect()
            self._initialized = True
            self.metrics.is_healthy = True
            return True
        except Exception as e:
            logger.error("Redis 连接池初始化失败：%s", e)
            self.metrics.is_healthy = False
            return False

    async def get_client(self):
        """获取 Redis 客户端"""
        if not self._initialized:
            await self.initialize()
        return await redis_client.get_client()

    async def execute_command(
        self, command: str, *args, fallback: Any | None = None, **kwargs
    ) -> Any:
        """执行 Redis 命令"""
        client = await self.get_client()
        if not client:
            if fallback is not None:
                return fallback
            raise ConnectionError("Redis 连接不可用")
        return await client.execute_command(command, *args)

    async def close(self):
        """关闭连接"""
        await redis_client.close()
        self._initialized = False

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "initialized": self._initialized,
            "is_healthy": self.metrics.is_healthy,
            "total_requests": self.metrics.total_requests,
            "failed_requests": self.metrics.failed_requests,
        }


_redis_pool_manager: RedisPoolManager | None = None


async def get_redis_pool() -> RedisPoolManager:
    """获取全局 Redis 连接池"""
    global _redis_pool_manager
    if not _redis_pool_manager:
        _redis_pool_manager = RedisPoolManager()
        await _redis_pool_manager.initialize()
    return _redis_pool_manager


async def init_redis_pool(config: RedisPoolConfig | None = None):
    """初始化全局 Redis 连接池"""
    global _redis_pool_manager
    if _redis_pool_manager and _redis_pool_manager._initialized:
        logger.warning("Redis 连接池已初始化，跳过")
        return _redis_pool_manager
    _redis_pool_manager = RedisPoolManager(config)
    await _redis_pool_manager.initialize()
    return _redis_pool_manager
