"""Redis 会话存储后端 - 连接池优化版

使用 Redis 连接池提高性能和可靠性
支持连接健康检查、自动重连和连接数监控
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from functools import wraps
from typing import Any

from core.config import settings
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError, TimeoutError
from utils import utcnow

logger = logging.getLogger(__name__)


# ==================== 数据模型 ====================
@dataclass
class ConversationState:
    """会话状态"""

    session_id: str
    user_id: str
    current_intent: str | None = None
    collected_slots: dict[str, Any] = None
    turn_count: int = 0
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.collected_slots is None:
            self.collected_slots = {}
        if self.created_at is None:
            self.created_at = utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = utcnow().isoformat()


# ==================== Redis 键前缀 ====================
class RedisKeys:
    """Redis 键命名规范"""

    SESSION_STATE = "session:{session_id}:state"
    SESSION_HISTORY = "session:{session_id}:history"
    USER_PROFILE = "user:{user_id}:profile"
    CACHE_PRODUCT = "cache:product:{product_id}:info"
    QUEUE_ESCALATION = "queue:escalation"
    METRICS_REALTIME = "metrics:realtime"

    # 限流相关
    RATE_LIMIT = "rate_limit:{client_id}"
    RATE_LIMIT_WINDOW = "rate_limit:{client_id}:window"

    # WebSocket 相关
    WEBSOCKET_CONNECTIONS = "websocket:connections"
    WEBSOCKET_AGENTS = "websocket:agents"
    WEBSOCKET_USERS = "websocket:users"
    WEBSOCKET_CHANNEL = "websocket:broadcast"

    # 客服状态
    AGENT_STATUS = "agent:{agent_id}:status"

    @classmethod
    def session_state(cls, session_id: str) -> str:
        return cls.SESSION_STATE.format(session_id=session_id)

    @classmethod
    def session_history(cls, session_id: str) -> str:
        return cls.SESSION_HISTORY.format(session_id=session_id)

    @classmethod
    def user_profile(cls, user_id: str) -> str:
        return cls.USER_PROFILE.format(user_id=user_id)

    @classmethod
    def cache_product(cls, product_id: str) -> str:
        return cls.CACHE_PRODUCT.format(product_id=product_id)


# ==================== 连接池配置 ====================
@dataclass
class RedisPoolConfig:
    """Redis 连接池配置"""

    max_connections: int = 100
    min_idle_connections: int = 10
    connection_timeout: float = 30.0
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    socket_keepalive: bool = True
    health_check_interval: int = 30
    retry_on_timeout: bool = True


def with_retry(max_retries: int = 3, retry_delay: float = 0.1):
    """重试装饰器"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(self, *args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Redis 操作失败，第 {attempt + 1} 次重试: {e}")
                        await asyncio.sleep(retry_delay * (2**attempt))
                        # 尝试重新连接
                        await self._reconnect()
                    else:
                        raise
            raise last_exception

        return wrapper

    return decorator


# ==================== Redis 客户端 ====================
class RedisClient:
    """Redis 客户端封装 - 连接池优化版"""

    def __init__(self, config: RedisPoolConfig | None = None):
        self.config = config or RedisPoolConfig(
            max_connections=settings.redis_max_connections,
            min_idle_connections=settings.redis_min_idle_connections,
            connection_timeout=settings.redis_connection_timeout,
            socket_timeout=settings.redis_socket_timeout,
        )
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None
        self._ttl_seconds = settings.redis_ttl_hours * 3600
        self._connected = False
        self._connection_lock = asyncio.Lock()
        self._health_check_task: asyncio.Task | None = None

    async def connect(self) -> None:
        """初始化 Redis 连接池"""
        async with self._connection_lock:
            if self._connected:
                return

            try:
                # 构建连接 URL
                if settings.redis_url:
                    connection_url = settings.redis_url
                else:
                    password_part = (
                        f":{settings.redis_password}@" if settings.redis_password else ""
                    )
                    connection_url = (
                        f"redis://{password_part}{settings.redis_host}"
                        f":{settings.redis_port}/{settings.redis_db}"
                    )

                # 创建连接池
                self._pool = ConnectionPool.from_url(
                    connection_url,
                    max_connections=self.config.max_connections,
                    socket_timeout=self.config.socket_timeout,
                    socket_connect_timeout=self.config.socket_connect_timeout,
                    socket_keepalive=self.config.socket_keepalive,
                    health_check_interval=self.config.health_check_interval,
                    retry_on_timeout=self.config.retry_on_timeout,
                )

                # 创建客户端
                self._client = Redis(connection_pool=self._pool)

                # 测试连接
                await self._client.ping()

                self._connected = True
                logger.info(f"Redis 连接池初始化成功 (max={self.config.max_connections})")

                # 启动健康检查
                self._start_health_check()

            except Exception as e:
                logger.error(f"Redis 连接失败: {e}")
                raise

    async def _reconnect(self) -> None:
        """重新连接"""
        async with self._connection_lock:
            if self._connected:
                try:
                    await self._client.ping()
                    return  # 连接正常
                except Exception:
                    pass
            await self._close_connection()

            # 重新连接
            try:
                await self.connect()
                logger.info("Redis 重连成功")
            except Exception as e:
                logger.error(f"Redis 重连失败: {e}")
                raise

    async def _close_connection(self) -> None:
        """关闭连接"""
        self._connected = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        if self._client:
            await self._client.close()
            self._client = None

        if self._pool:
            await self._pool.disconnect()
            self._pool = None

    async def close(self) -> None:
        """关闭连接池"""
        await self._close_connection()
        logger.info("Redis 连接池已关闭")

    async def ping(self) -> bool:
        """检查连接"""
        if not self._connected or not self._client:
            return False
        try:
            return await self._client.ping()
        except Exception:
            return False

    def _start_health_check(self) -> None:
        """启动健康检查任务"""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self._connected:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                if self._client:
                    await self._client.ping()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Redis 健康检查失败: {e}")
                try:
                    await self._reconnect()
                except Exception:
                    pass

    def _get_ttl(self, custom_ttl: int | None = None) -> int:
        """获取 TTL"""
        return custom_ttl if custom_ttl is not None else self._ttl_seconds

    # ==================== 会话状态管理 ====================
    @with_retry(max_retries=3)
    async def save_session_state(self, state: ConversationState, ttl: int | None = None) -> None:
        """保存会话状态"""
        key = RedisKeys.session_state(state.session_id)
        data = asdict(state)
        await self._client.setex(key, self._get_ttl(ttl), json.dumps(data, ensure_ascii=False))

    @with_retry(max_retries=3)
    async def get_session_state(self, session_id: str) -> ConversationState | None:
        """获取会话状态"""
        key = RedisKeys.session_state(session_id)
        data = await self._client.get(key)
        return ConversationState(**json.loads(data)) if data else None

    @with_retry(max_retries=3)
    async def delete_session_state(self, session_id: str) -> None:
        """删除会话状态"""
        key = RedisKeys.session_state(session_id)
        await self._client.delete(key)

    # ==================== 会话历史管理 ====================
    @with_retry(max_retries=3)
    async def add_message_to_history(
        self, session_id: str, role: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """添加消息到会话历史"""
        key = RedisKeys.session_history(session_id)
        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": utcnow().isoformat(),
        }
        await self._client.rpush(key, json.dumps(message, ensure_ascii=False))
        await self._client.expire(key, self._ttl_seconds)

    @with_retry(max_retries=3)
    async def get_session_history(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """获取会话历史"""
        key = RedisKeys.session_history(session_id)
        messages = await self._client.lrange(key, -limit, -1)
        return [json.loads(msg) for msg in messages]

    @with_retry(max_retries=3)
    async def clear_session_history(self, session_id: str) -> None:
        """清除会话历史"""
        key = RedisKeys.session_history(session_id)
        await self._client.delete(key)

    # ==================== 用户画像管理 ====================
    @with_retry(max_retries=3)
    async def save_user_profile(
        self, user_id: str, profile: dict[str, Any], ttl: int | None = None
    ) -> None:
        """保存用户画像"""
        key = RedisKeys.user_profile(user_id)
        ttl = ttl or (7 * 24 * 3600)  # 7 天
        await self._client.setex(key, ttl, json.dumps(profile, ensure_ascii=False))

    @with_retry(max_retries=3)
    async def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        """获取用户画像"""
        key = RedisKeys.user_profile(user_id)
        data = await self._client.get(key)
        return json.loads(data) if data else None

    @with_retry(max_retries=3)
    async def update_user_profile(self, user_id: str, updates: dict[str, Any]) -> None:
        """更新用户画像"""
        current = await self.get_user_profile(user_id) or {}
        current.update(updates)
        await self.save_user_profile(user_id, current)

    # ==================== 缓存管理 ====================
    @with_retry(max_retries=3)
    async def cache_set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """设置缓存"""
        await self._client.setex(key, ttl_seconds, json.dumps(value, ensure_ascii=False))

    @with_retry(max_retries=3)
    async def cache_get(self, key: str) -> Any | None:
        """获取缓存"""
        data = await self._client.get(key)
        return json.loads(data) if data else None

    @with_retry(max_retries=3)
    async def cache_delete(self, key: str) -> None:
        """删除缓存"""
        await self._client.delete(key)

    # ==================== 速率限制管理 ====================
    @with_retry(max_retries=3)
    async def check_rate_limit(
        self, client_id: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """检查速率限制（滑动窗口）"""
        key = RedisKeys.RATE_LIMIT.format(client_id=client_id)
        current_time = time.time()
        window_start = current_time - window_seconds

        pipe = self._client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {f"{current_time}": current_time})
        pipe.zcard(key)
        pipe.expire(key, window_seconds * 2)
        results = await pipe.execute()

        request_count = results[2]

        if request_count > max_requests:
            oldest_request = await self._client.zrange(key, 0, 0, withscores=True)
            if oldest_request:
                retry_after = int(oldest_request[0][1] + window_seconds - current_time) + 1
                return False, max(retry_after, 1)
            return False, 1

        return True, 0

    @with_retry(max_retries=3)
    async def get_rate_limit_count(self, client_id: str, window_seconds: int) -> int:
        """获取当前窗口内的请求数"""
        key = RedisKeys.RATE_LIMIT.format(client_id=client_id)
        window_start = time.time() - window_seconds
        return await self._client.zcount(key, window_start, time.time())

    @with_retry(max_retries=3)
    async def reset_rate_limit(self, client_id: str) -> None:
        """重置速率限制"""
        key = RedisKeys.RATE_LIMIT.format(client_id=client_id)
        await self._client.delete(key)

    # ==================== WebSocket 连接管理 ====================
    @with_retry(max_retries=3)
    async def add_websocket_connection(self, client_id: str, connection_data: dict) -> None:
        """添加 WebSocket 连接"""
        pipe = self._client.pipeline()
        pipe.hset(
            RedisKeys.WEBSOCKET_CONNECTIONS,
            client_id,
            json.dumps(connection_data, ensure_ascii=False),
        )
        if connection_data.get("is_agent"):
            pipe.sadd(RedisKeys.WEBSOCKET_AGENTS, client_id)
        else:
            pipe.sadd(RedisKeys.WEBSOCKET_USERS, client_id)
        await pipe.execute()

    @with_retry(max_retries=3)
    async def remove_websocket_connection(self, client_id: str) -> None:
        """移除 WebSocket 连接"""
        pipe = self._client.pipeline()
        pipe.hdel(RedisKeys.WEBSOCKET_CONNECTIONS, client_id)
        pipe.srem(RedisKeys.WEBSOCKET_AGENTS, client_id)
        pipe.srem(RedisKeys.WEBSOCKET_USERS, client_id)
        await pipe.execute()

    @with_retry(max_retries=3)
    async def get_websocket_connection(self, client_id: str) -> dict | None:
        """获取 WebSocket 连接信息"""
        data = await self._client.hget(RedisKeys.WEBSOCKET_CONNECTIONS, client_id)
        return json.loads(data) if data else None

    @with_retry(max_retries=3)
    async def get_websocket_agents(self) -> set:
        """获取所有客服 WebSocket 连接"""
        return await self._client.smembers(RedisKeys.WEBSOCKET_AGENTS)

    @with_retry(max_retries=3)
    async def get_websocket_users(self) -> set:
        """获取所有用户 WebSocket 连接"""
        return await self._client.smembers(RedisKeys.WEBSOCKET_USERS)

    @with_retry(max_retries=3)
    async def get_websocket_stats(self) -> dict:
        """获取 WebSocket 连接统计"""
        pipe = self._client.pipeline()
        pipe.hlen(RedisKeys.WEBSOCKET_CONNECTIONS)
        pipe.scard(RedisKeys.WEBSOCKET_AGENTS)
        pipe.scard(RedisKeys.WEBSOCKET_USERS)
        results = await pipe.execute()
        return {
            "total_connections": results[0],
            "agent_connections": results[1],
            "user_connections": results[2],
        }

    @with_retry(max_retries=3)
    async def publish_websocket_message(self, channel: str, message: dict) -> int:
        """发布 WebSocket 消息到频道"""
        return await self._client.publish(
            f"{RedisKeys.WEBSOCKET_CHANNEL}:{channel}", json.dumps(message, ensure_ascii=False)
        )

    # ==================== 客服状态管理 ====================
    @with_retry(max_retries=3)
    async def set_agent_status(self, agent_id: str, status: str, concurrent_chats: int) -> None:
        """设置客服状态"""
        await self._client.hset(
            RedisKeys.AGENT_STATUS.format(agent_id=agent_id),
            mapping={
                "status": status,
                "concurrent_chats": str(concurrent_chats),
                "updated_at": utcnow().isoformat(),
            },
        )
        await self._client.expire(
            RedisKeys.AGENT_STATUS.format(agent_id=agent_id),
            3600,  # 1 小时过期
        )

    @with_retry(max_retries=3)
    async def get_agent_status(self, agent_id: str) -> dict | None:
        """获取客服状态"""
        data = await self._client.hgetall(RedisKeys.AGENT_STATUS.format(agent_id=agent_id))
        if not data:
            return None
        return {
            "status": data.get("status", "offline"),
            "concurrent_chats": int(data.get("concurrent_chats", 0)),
            "updated_at": data.get("updated_at", ""),
        }

    @with_retry(max_retries=3)
    async def get_multiple_agent_status(self, agent_ids: list[str]) -> dict[str, dict]:
        """
        批量获取多个客服状态

        使用 Pipeline 优化，避免 N+1 问题

        Args:
            agent_ids: 客服 ID 列表

        Returns:
            客服状态字典 {agent_id: status_dict}
        """
        if not agent_ids:
            return {}

        # 使用 Pipeline 批量查询
        pipe = self._client.pipeline()
        for agent_id in agent_ids:
            pipe.hgetall(RedisKeys.AGENT_STATUS.format(agent_id=agent_id))

        results = await pipe.execute()

        # 解析结果
        status_dict = {}
        for i, agent_id in enumerate(agent_ids):
            data = results[i]
            if data:
                status_dict[agent_id] = {
                    "status": data.get("status", "offline"),
                    "concurrent_chats": int(data.get("concurrent_chats", 0)),
                    "updated_at": data.get("updated_at", ""),
                }
            else:
                status_dict[agent_id] = {
                    "status": "offline",
                    "concurrent_chats": 0,
                    "updated_at": "",
                }

        return status_dict

    async def get_client(self) -> Redis | None:
        """获取底层 Redis 客户端"""
        return self._client

    # ==================== 升级队列管理 ====================
    @with_retry(max_retries=3)
    async def add_to_escalation_queue(self, conversation_id: str, priority_score: float) -> None:
        """添加到升级队列"""
        await self._client.zadd(RedisKeys.QUEUE_ESCALATION, {conversation_id: priority_score})

    @with_retry(max_retries=3)
    async def get_next_escalation(self) -> str | None:
        """获取下一个升级会话 (最高优先级)"""
        result = await self._client.zpopmax(RedisKeys.QUEUE_ESCALATION, count=1)
        return result[0][0] if result else None

    @with_retry(max_retries=3)
    async def get_escalation_queue_size(self) -> int:
        """获取升级队列大小"""
        return await self._client.zcard(RedisKeys.QUEUE_ESCALATION)

    # ==================== 实时指标管理 ====================
    @with_retry(max_retries=3)
    async def increment_metric(self, metric_name: str, value: int = 1) -> None:
        """增加指标计数"""
        key = f"{RedisKeys.METRICS_REALTIME}:{metric_name}"
        await self._client.incrby(key, value)

    @with_retry(max_retries=3)
    async def get_metric(self, metric_name: str) -> int:
        """获取指标值"""
        key = f"{RedisKeys.METRICS_REALTIME}:{metric_name}"
        value = await self._client.get(key)
        return int(value) if value else 0

    @with_retry(max_retries=3)
    async def reset_metric(self, metric_name: str) -> None:
        """重置指标"""
        key = f"{RedisKeys.METRICS_REALTIME}:{metric_name}"
        await self._client.delete(key)

    # ==================== 连接池监控 ====================
    async def get_pool_stats(self) -> dict:
        """获取连接池统计信息"""
        if not self._pool:
            return {}

        try:
            # 获取连接池信息
            return {
                "max_connections": self._pool.max_connections,
                "available_connections": len(self._pool.available_connections),
                "in_use_connections": len(self._pool._in_use_connections),
                "connection_class": self._pool.connection_class.__name__,
            }
        except Exception as e:
            logger.error(f"获取连接池统计失败: {e}")
            return {}


# 全局 Redis 客户端实例
redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    """获取 Redis 客户端"""
    return redis_client
