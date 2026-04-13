"""
Redis 连接池管理模块

提供:
- 连接池配置管理
- 连接健康检查
- 连接复用
- 故障转移
- 监控指标
"""

import asyncio
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

import redis.asyncio as redis
from core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RedisPoolConfig:
    """Redis 连接池配置"""

    host: str = field(default_factory=lambda: settings.redis_host)
    port: int = field(default_factory=lambda: settings.redis_port)
    db: int = field(default_factory=lambda: settings.redis_db)
    password: Optional[str] = field(default_factory=lambda: settings.redis_password)

    # 连接池配置
    max_connections: int = 100
    min_idle_connections: int = 10
    connection_timeout: float = 30.0
    socket_timeout: float = 5.0
    socket_keepalive: bool = True
    retry_on_timeout: bool = True

    # 健康检查
    health_check_interval: int = 30  # 秒
    max_health_check_failures: int = 3

    # 降级配置
    enable_fallback: bool = True
    fallback_enabled: bool = True


@dataclass
class PoolMetrics:
    """连接池指标"""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0

    # 性能指标
    avg_acquire_time_ms: float = 0.0
    max_acquire_time_ms: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0

    # 健康状态
    health_check_failures: int = 0
    last_health_check: Optional[datetime] = None
    is_healthy: bool = True

    # 降级状态
    is_degraded: bool = False
    fallback_active: bool = False
    last_failure_time: Optional[datetime] = None


class RedisPoolManager:
    """Redis 连接池管理器"""

    def __init__(self, config: Optional[RedisPoolConfig] = None):
        """
        初始化连接池管理器

        Args:
            config: 连接池配置
        """
        self.config = config or RedisPoolConfig()
        self.pool: Optional[redis.ConnectionPool] = None
        self.client: Optional[redis.Redis] = None
        self.metrics = PoolMetrics()
        self._health_check_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> bool:
        """
        初始化连接池

        Returns:
            是否初始化成功
        """
        async with self._lock:
            if self._initialized:
                return True

            try:
                # 创建连接池
                self.pool = redis.ConnectionPool(
                    host=self.config.host,
                    port=self.config.port,
                    db=self.config.db,
                    password=self.config.password,
                    max_connections=self.config.max_connections,
                    decode_responses=True,
                    socket_timeout=self.config.socket_timeout,
                    socket_keepalive=self.config.socket_keepalive,
                    retry_on_timeout=self.config.retry_on_timeout,
                )

                # 创建 Redis 客户端
                self.client = redis.Redis(connection_pool=self.pool)

                # 验证连接
                await self._health_check()

                # 启动健康检查后台任务
                self._health_check_task = asyncio.create_task(self._health_check_loop())

                self._initialized = True
                logger.info(
                    f"Redis 连接池初始化成功 (max_connections={self.config.max_connections})"
                )

                return True

            except Exception as e:
                logger.error(f"Redis 连接池初始化失败：{e}")
                self.metrics.is_healthy = False
                return False

    async def _health_check(self) -> bool:
        """
        健康检查

        Returns:
            是否健康
        """
        try:
            if not self.client:
                return False

            # PING 测试
            await self.client.ping()

            # 更新指标
            self.metrics.health_check_failures = 0
            self.metrics.last_health_check = datetime.utcnow()
            self.metrics.is_healthy = True

            return True

        except Exception as e:
            logger.warning(f"Redis 健康检查失败：{e}")
            self.metrics.health_check_failures += 1
            self.metrics.last_health_check = datetime.utcnow()

            if self.metrics.health_check_failures >= self.config.max_health_check_failures:
                self.metrics.is_healthy = False
                logger.error("Redis 健康检查多次失败，标记为不健康")

            return False

    async def _health_check_loop(self):
        """健康检查后台循环"""
        while True:
            await asyncio.sleep(self.config.health_check_interval)

            if not self._initialized:
                continue

            await self._health_check()

    async def get_client(self) -> Optional[redis.Redis]:
        """
        获取 Redis 客户端

        Returns:
            Redis 客户端，失败时返回 None
        """
        if not self._initialized:
            await self.initialize()

        if not self.metrics.is_healthy:
            logger.warning("Redis 连接池不健康，尝试恢复")
            # 尝试重新初始化
            await self.close()
            self._initialized = False
            if not await self.initialize():
                return None

        return self.client

    async def execute_command(
        self, command: str, *args, fallback: Optional[Any] = None, timeout: Optional[float] = None
    ) -> Any:
        """
        执行 Redis 命令

        Args:
            command: Redis 命令
            *args: 命令参数
            fallback: 降级时的默认值
            timeout: 命令超时时间

        Returns:
            命令执行结果，失败时返回 fallback 或抛出异常
        """
        start_time = time.time()

        try:
            client = await self.get_client()
            if not client:
                if fallback is not None:
                    logger.warning(f"Redis 命令执行失败，使用降级值：{command}")
                    return fallback
                raise ConnectionError("Redis 连接不可用")

            # 执行命令
            if timeout:
                result = await asyncio.wait_for(
                    client.execute_command(command, *args), timeout=timeout
                )
            else:
                result = await client.execute_command(command, *args)

            # 更新指标
            acquire_time = (time.time() - start_time) * 1000
            self._update_metrics(success=True, acquire_time_ms=acquire_time)

            return result

        except asyncio.TimeoutError:
            self._update_metrics(success=False)
            logger.warning(f"Redis 命令超时：{command}")

            if fallback is not None:
                return fallback
            raise

        except Exception as e:
            self._update_metrics(success=False)
            logger.error(f"Redis 命令执行失败：{command}, 错误：{e}")

            if fallback is not None and self.config.enable_fallback:
                logger.info(f"使用降级值：{command}")
                return fallback

            raise

    def _update_metrics(self, success: bool, acquire_time_ms: float = 0.0):
        """更新连接池指标"""
        self.metrics.total_requests += 1

        if success:
            self.metrics.active_connections += 1
            if acquire_time_ms > self.metrics.max_acquire_time_ms:
                self.metrics.max_acquire_time_ms = acquire_time_ms

            # 计算平均获取时间
            total = self.metrics.total_requests
            avg = self.metrics.avg_acquire_time_ms
            self.metrics.avg_acquire_time_ms = ((avg * (total - 1)) + acquire_time_ms) / total
        else:
            self.metrics.failed_requests += 1
            self.metrics.failed_connections += 1
            self.metrics.last_failure_time = datetime.utcnow()

    async def close(self):
        """关闭连接池"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        if self.pool:
            await self.pool.disconnect()
            self.pool = None

        self.client = None
        self._initialized = False
        logger.info("Redis 连接池已关闭")

    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        return {
            "initialized": self._initialized,
            "is_healthy": self.metrics.is_healthy,
            "is_degraded": self.metrics.is_degraded,
            "fallback_active": self.metrics.fallback_active,
            "total_connections": self.metrics.total_connections,
            "active_connections": self.metrics.active_connections,
            "idle_connections": self.metrics.idle_connections,
            "failed_connections": self.metrics.failed_connections,
            "total_requests": self.metrics.total_requests,
            "failed_requests": self.metrics.failed_requests,
            "avg_acquire_time_ms": round(self.metrics.avg_acquire_time_ms, 2),
            "max_acquire_time_ms": round(self.metrics.max_acquire_time_ms, 2),
            "health_check_failures": self.metrics.health_check_failures,
            "last_health_check": self.metrics.last_health_check.isoformat()
            if self.metrics.last_health_check
            else None,
            "last_failure_time": self.metrics.last_failure_time.isoformat()
            if self.metrics.last_failure_time
            else None,
        }


# 全局连接池实例
redis_pool_manager: Optional[RedisPoolManager] = None


async def get_redis_pool() -> RedisPoolManager:
    """获取全局 Redis 连接池"""
    global redis_pool_manager

    if not redis_pool_manager:
        redis_pool_manager = RedisPoolManager()
        await redis_pool_manager.initialize()

    return redis_pool_manager


async def init_redis_pool(config: Optional[RedisPoolConfig] = None):
    """初始化全局 Redis 连接池"""
    global redis_pool_manager

    if redis_pool_manager and redis_pool_manager._initialized:
        logger.warning("Redis 连接池已初始化，跳过")
        return

    redis_pool_manager = RedisPoolManager(config)
    success = await redis_pool_manager.initialize()

    if not success:
        logger.error("Redis 连接池初始化失败")

    return redis_pool_manager
