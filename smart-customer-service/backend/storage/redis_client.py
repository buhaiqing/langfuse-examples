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
