"""Redis 会话存储后端"""

import json
import redis.asyncio as redis
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from core.config import settings


# ==================== 数据模型 ====================
@dataclass
class ConversationState:
    """会话状态"""

    session_id: str
    user_id: str
    current_intent: Optional[str]
    collected_slots: Dict[str, Any]
    turn_count: int
    created_at: str
    updated_at: str


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


# ==================== Redis 客户端 ====================
class RedisClient:
    """Redis 客户端封装"""

    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._ttl_seconds = settings.redis_ttl_hours * 3600

    async def connect(self) -> None:
        """连接 Redis"""
        self.client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True,
        )

    async def close(self) -> None:
        """关闭连接"""
        if self.client:
            await self.client.close()

    async def ping(self) -> bool:
        """检查连接"""
        try:
            return await self.client.ping()
        except Exception:
            return False

    # ==================== 会话状态管理 ====================
    async def save_session_state(self, state: ConversationState) -> None:
        """
        保存会话状态

        Args:
            state: 会话状态对象
        """
        key = RedisKeys.session_state(state.session_id)
        data = asdict(state)
        await self.client.setex(key, self._ttl_seconds, json.dumps(data, ensure_ascii=False))

    async def get_session_state(self, session_id: str) -> Optional[ConversationState]:
        """
        获取会话状态

        Args:
            session_id: 会话 ID

        Returns:
            会话状态或 None
        """
        key = RedisKeys.session_state(session_id)
        data = await self.client.get(key)

        if not data:
            return None

        return ConversationState(**json.loads(data))

    async def delete_session_state(self, session_id: str) -> None:
        """删除会话状态"""
        key = RedisKeys.session_state(session_id)
        await self.client.delete(key)

    # ==================== 会话历史管理 ====================
    async def add_message_to_history(
        self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        添加消息到会话历史

        Args:
            session_id: 会话 ID
            role: 角色 (user/assistant)
            content: 消息内容
            metadata: 元数据
        """
        key = RedisKeys.session_history(session_id)
        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self.client.rpush(key, json.dumps(message, ensure_ascii=False))

        # 设置 TTL
        await self.client.expire(key, self._ttl_seconds)

    async def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取会话历史

        Args:
            session_id: 会话 ID
            limit: 返回条数限制

        Returns:
            消息列表
        """
        key = RedisKeys.session_history(session_id)
        messages = await self.client.lrange(key, -limit, -1)

        return [json.loads(msg) for msg in messages]

    async def clear_session_history(self, session_id: str) -> None:
        """清除会话历史"""
        key = RedisKeys.session_history(session_id)
        await self.client.delete(key)

    # ==================== 用户画像管理 ====================
    async def save_user_profile(self, user_id: str, profile: Dict[str, Any]) -> None:
        """
        保存用户画像

        Args:
            user_id: 用户 ID
            profile: 用户画像数据
        """
        key = RedisKeys.user_profile(user_id)
        ttl = 7 * 24 * 3600  # 7 天

        await self.client.setex(key, ttl, json.dumps(profile, ensure_ascii=False))

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户画像"""
        key = RedisKeys.user_profile(user_id)
        data = await self.client.get(key)

        if not data:
            return None

        return json.loads(data)

    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> None:
        """
        更新用户画像

        Args:
            user_id: 用户 ID
            updates: 更新数据
        """
        current = await self.get_user_profile(user_id) or {}
        current.update(updates)
        await self.save_user_profile(user_id, current)

    # ==================== 缓存管理 ====================
    async def cache_set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """设置缓存"""
        await self.client.setex(key, ttl_seconds, json.dumps(value, ensure_ascii=False))

    async def cache_get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        data = await self.client.get(key)
        return json.loads(data) if data else None

    async def cache_delete(self, key: str) -> None:
        """删除缓存"""
        await self.client.delete(key)

    # ==================== 速率限制管理 ====================
    async def check_rate_limit(
        self, client_id: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """
        检查速率限制（使用 Redis Sorted Set 实现滑动窗口）

        Args:
            client_id: 客户端标识
            max_requests: 最大请求数
            window_seconds: 时间窗口（秒）

        Returns:
            Tuple[bool, int]: (是否允许，重试等待秒数)
        """
        key = RedisKeys.RATE_LIMIT.format(client_id=client_id)
        current_time = time.time()
        window_start = current_time - window_seconds

        # 使用 Redis pipeline
        pipe = self.client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)  # 清理旧记录
        pipe.zadd(key, {f"{current_time}": current_time})  # 添加新记录
        pipe.zcard(key)  # 计数
        pipe.expire(key, window_seconds * 2)  # 设置过期
        results = await pipe.execute()

        request_count = results[2]

        if request_count > max_requests:
            # 计算需要等待的时间
            oldest_request = await self.client.zrange(key, 0, 0, withscores=True)
            if oldest_request:
                retry_after = int(oldest_request[0][1] + window_seconds - current_time) + 1
                return False, max(retry_after, 1)
            return False, 1

        return True, 0

    async def get_rate_limit_count(self, client_id: str, window_seconds: int) -> int:
        """获取当前窗口内的请求数"""
        key = RedisKeys.RATE_LIMIT.format(client_id=client_id)
        window_start = time.time() - window_seconds
        return await self.client.zcount(key, window_start, time.time())

    async def reset_rate_limit(self, client_id: str) -> None:
        """重置速率限制"""
        key = RedisKeys.RATE_LIMIT.format(client_id=client_id)
        await self.client.delete(key)

    # ==================== WebSocket 连接管理 ====================
    async def add_websocket_connection(self, client_id: str, connection_data: dict) -> None:
        """添加 WebSocket 连接"""
        pipe = self.client.pipeline()
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

    async def remove_websocket_connection(self, client_id: str) -> None:
        """移除 WebSocket 连接"""
        pipe = self.client.pipeline()
        pipe.hdel(RedisKeys.WEBSOCKET_CONNECTIONS, client_id)
        pipe.srem(RedisKeys.WEBSOCKET_AGENTS, client_id)
        pipe.srem(RedisKeys.WEBSOCKET_USERS, client_id)
        await pipe.execute()

    async def get_websocket_connection(self, client_id: str) -> Optional[dict]:
        """获取 WebSocket 连接信息"""
        data = await self.client.hget(RedisKeys.WEBSOCKET_CONNECTIONS, client_id)
        return json.loads(data) if data else None

    async def get_websocket_agents(self) -> set[str]:
        """获取所有客服 WebSocket 连接"""
        return await self.client.smembers(RedisKeys.WEBSOCKET_AGENTS)

    async def get_websocket_users(self) -> set[str]:
        """获取所有用户 WebSocket 连接"""
        return await self.client.smembers(RedisKeys.WEBSOCKET_USERS)

    async def get_websocket_stats(self) -> dict:
        """获取 WebSocket 连接统计"""
        pipe = self.client.pipeline()
        pipe.hlen(RedisKeys.WEBSOCKET_CONNECTIONS)
        pipe.scard(RedisKeys.WEBSOCKET_AGENTS)
        pipe.scard(RedisKeys.WEBSOCKET_USERS)
        results = await pipe.execute()

        return {
            "total_connections": results[0],
            "agent_connections": results[1],
            "user_connections": results[2],
        }

    async def publish_websocket_message(self, channel: str, message: dict) -> int:
        """发布 WebSocket 消息到频道"""
        return await self.client.publish(
            f"{RedisKeys.WEBSOCKET_CHANNEL}:{channel}", json.dumps(message, ensure_ascii=False)
        )

    # ==================== 客服状态管理 ====================
    async def set_agent_status(self, agent_id: str, status: str, concurrent_chats: int) -> None:
        """设置客服状态"""
        await self.client.hset(
            RedisKeys.AGENT_STATUS.format(agent_id=agent_id),
            mapping={
                "status": status,
                "concurrent_chats": str(concurrent_chats),
                "updated_at": datetime.utcnow().isoformat(),
            },
        )
        await self.client.expire(
            RedisKeys.AGENT_STATUS.format(agent_id=agent_id),
            3600,  # 1 小时过期
        )

    async def get_agent_status(self, agent_id: str) -> Optional[dict]:
        """获取客服状态"""
        data = await self.client.hgetall(RedisKeys.AGENT_STATUS.format(agent_id=agent_id))
        if not data:
            return None

        return {
            "status": data.get(b"status", b"offline").decode(),
            "concurrent_chats": int(data.get(b"concurrent_chats", 0)),
            "updated_at": data.get(b"updated_at", b"").decode(),
        }

    async def get_multiple_agent_status(self, agent_ids: List[str]) -> Dict[str, Optional[dict]]:
        """
        批量获取客服状态 - 使用 Pipeline 优化性能
        
        Args:
            agent_ids: 客服 ID 列表
            
        Returns:
            Dict[str, Optional[dict]]: 客服 ID -> 状态的字典
        """
        if not agent_ids:
            return {}

        # 使用 Pipeline 批量执行 HGETALL 命令
        pipe = self.client.pipeline()
        for agent_id in agent_ids:
            pipe.hgetall(RedisKeys.AGENT_STATUS.format(agent_id=agent_id))
        
        results = await pipe.execute()
        
        # 解析结果
        status_map = {}
        for agent_id, data in zip(agent_ids, results):
            if data:
                status_map[agent_id] = {
                    "status": data.get(b"status", b"offline").decode(),
                    "concurrent_chats": int(data.get(b"concurrent_chats", 0)),
                    "updated_at": data.get(b"updated_at", b"").decode(),
                }
            else:
                status_map[agent_id] = None
        
        return status_map

    # ==================== 升级队列管理 ====================
    async def add_to_escalation_queue(self, conversation_id: str, priority_score: float) -> None:
        """
        添加到升级队列

        Args:
            conversation_id: 会话 ID
            priority_score: 优先级分数
        """
        await self.client.zadd(RedisKeys.QUEUE_ESCALATION, {conversation_id: priority_score})

    async def get_next_escalation(self) -> Optional[str]:
        """获取下一个升级会话 (最高优先级)"""
        result = await self.client.zpopmax(RedisKeys.QUEUE_ESCALATION, count=1)

        if not result:
            return None

        return result[0][0]

    async def get_escalation_queue_size(self) -> int:
        """获取升级队列大小"""
        return await self.client.zcard(RedisKeys.QUEUE_ESCALATION)

    # ==================== 实时指标管理 ====================
    async def increment_metric(self, metric_name: str, value: int = 1) -> None:
        """增加指标计数"""
        key = f"{RedisKeys.METRICS_REALTIME}:{metric_name}"
        await self.client.incrby(key, value)

    async def get_metric(self, metric_name: str) -> int:
        """获取指标值"""
        key = f"{RedisKeys.METRICS_REALTIME}:{metric_name}"
        value = await self.client.get(key)
        return int(value) if value else 0

    async def reset_metric(self, metric_name: str) -> None:
        """重置指标"""
        key = f"{RedisKeys.METRICS_REALTIME}:{metric_name}"
        await self.client.delete(key)


# 全局 Redis 客户端实例
redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    """获取 Redis 客户端"""
    return redis_client
