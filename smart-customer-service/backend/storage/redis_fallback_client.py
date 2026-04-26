"""
Redis 客户端降级包装器

将降级机制集成到现有 RedisClient，提供透明的降级支持
"""

import logging
from typing import Any

from storage.redis_client import ConversationState, RedisClient, RedisKeys
from storage.redis_fallback import (
    RedisFallbackManager,
    get_redis_fallback_manager,
)

logger = logging.getLogger(__name__)


# ==================== 降级 Redis 客户端 ====================
class FallbackRedisClient:
    """
    支持降级的 Redis 客户端包装器

    在 RedisClient 基础上增加:
    - 熔断器保护
    - 本地缓存降级
    - 自动恢复机制
    """

    def __init__(
        self,
        redis_client: RedisClient,
        fallback_manager: RedisFallbackManager | None = None,
    ):
        self.redis_client = redis_client
        self.fallback_manager = fallback_manager or get_redis_fallback_manager()
        self._recovery_started = False

    async def connect(self) -> bool:
        """连接 Redis，启动降级机制"""
        try:
            await self.redis_client.connect()

            # 启动自动恢复检查
            if not self._recovery_started:
                await self.fallback_manager.start_auto_recovery(check_func=self._check_recovery)
                self._recovery_started = True

            return True

        except Exception as e:
            logger.warning(f"Redis 连接失败，启用降级模式: {e}")
            # 即使连接失败，也允许继续工作（降级模式）
            return False

    async def _check_recovery(self) -> bool:
        """检查 Redis 是否恢复"""
        try:
            return await self.redis_client.ping()
        except Exception:
            return False

    async def close(self) -> None:
        """关闭连接"""
        await self.fallback_manager.stop_auto_recovery()
        await self.redis_client.close()
        self._recovery_started = False

    async def ping(self) -> bool:
        """检查连接状态"""
        # ping 不需要降级，直接检查
        try:
            return await self.redis_client.ping()
        except Exception:
            return False

    # ==================== 会话状态（带降级） ====================
    async def save_session_state(
        self,
        state: ConversationState,
        ttl: int | None = None,
    ) -> bool:
        """保存会话状态（带降级）"""
        key = RedisKeys.session_state(state.session_id)

        return await self.fallback_manager.execute_with_fallback(
            operation=lambda: self.redis_client.save_session_state(state, ttl),
            key=key,
            fallback_value=True,  # 降级时假设成功
            cache_ttl=ttl or 3600,
        )

    async def get_session_state(
        self,
        session_id: str,
    ) -> ConversationState | None:
        """获取会话状态（带降级）"""
        key = RedisKeys.session_state(session_id)

        result = await self.fallback_manager.execute_with_fallback(
            operation=lambda: self.redis_client.get_session_state(session_id),
            key=key,
            fallback_value=None,
            cache_ttl=3600,
        )

        if result and isinstance(result, dict):
            return ConversationState(**result)
        return result

    async def delete_session_state(self, session_id: str) -> bool:
        """删除会话状态"""
        try:
            await self.redis_client.delete_session_state(session_id)
            # 同时清理本地缓存
            key = RedisKeys.session_state(session_id)
            self.fallback_manager.local_cache.delete(key)
            return True
        except Exception as e:
            logger.warning(f"删除会话状态失败: {e}")
            # 清理本地缓存
            key = RedisKeys.session_state(session_id)
            self.fallback_manager.local_cache.delete(key)
            return True  # 降级时假设成功

    # ==================== 会话历史（带降级） ====================
    async def add_message_to_history(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """添加消息到历史"""
        try:
            await self.redis_client.add_message_to_history(session_id, role, content, metadata)
            return True
        except Exception as e:
            logger.warning(f"添加消息到历史失败，降级处理: {e}")
            # 降级时假设成功（本地缓存会在读取时处理）
            return True

    async def get_session_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """获取会话历史（带降级）"""
        key = f"history:{session_id}"

        return await self.fallback_manager.execute_with_fallback(
            operation=lambda: self.redis_client.get_session_history(session_id, limit),
            key=key,
            fallback_value=[],  # 降级时返回空历史
            cache_ttl=1800,
        )

    # ==================== 用户画像（带降级） ====================
    async def save_user_profile(
        self,
        user_id: str,
        profile: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """保存用户画像"""
        key = RedisKeys.user_profile(user_id)

        return await self.fallback_manager.execute_with_fallback(
            operation=lambda: self.redis_client.save_user_profile(user_id, profile, ttl),
            key=key,
            fallback_value=True,
            cache_ttl=ttl or 7 * 24 * 3600,
        )

    async def get_user_profile(
        self,
        user_id: str,
    ) -> dict[str, Any] | None:
        """获取用户画像"""
        key = RedisKeys.user_profile(user_id)

        return await self.fallback_manager.execute_with_fallback(
            operation=lambda: self.redis_client.get_user_profile(user_id),
            key=key,
            fallback_value=None,
            cache_ttl=3600,
        )

    # ==================== 缓存操作（带降级） ====================
    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
    ) -> bool:
        """设置缓存"""
        return await self.fallback_manager.execute_with_fallback(
            operation=lambda: self.redis_client.cache_set(key, value, ttl_seconds),
            key=key,
            fallback_value=True,
            cache_ttl=ttl_seconds,
        )

    async def cache_get(self, key: str) -> Any | None:
        """获取缓存"""
        return await self.fallback_manager.execute_with_fallback(
            operation=lambda: self.redis_client.cache_get(key),
            key=key,
            fallback_value=None,
            cache_ttl=3600,
        )

    async def cache_delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            await self.redis_client.cache_delete(key)
            self.fallback_manager.local_cache.delete(key)
            return True
        except Exception:
            self.fallback_manager.local_cache.delete(key)
            return True

    # ==================== 速率限制（带降级） ====================
    async def check_rate_limit(
        self,
        client_id: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """检查速率限制"""
        # 速率限制降级策略：假设允许通过
        return await self.fallback_manager.execute_with_fallback(
            operation=lambda: self.redis_client.check_rate_limit(
                client_id, max_requests, window_seconds
            ),
            key=None,
            fallback_value=(True, 0),  # 降级时允许请求
        )

    # ==================== WebSocket 连接管理 ====================
    async def add_websocket_connection(
        self,
        client_id: str,
        connection_data: dict,
    ) -> bool:
        """添加 WebSocket 连接"""
        try:
            await self.redis_client.add_websocket_connection(client_id, connection_data)
            return True
        except Exception as e:
            logger.warning(f"添加 WebSocket 连接失败: {e}")
            return True  # 降级时假设成功

    async def remove_websocket_connection(self, client_id: str) -> bool:
        """移除 WebSocket 连接"""
        try:
            await self.redis_client.remove_websocket_connection(client_id)
            return True
        except Exception:
            return True

    async def get_websocket_stats(self) -> dict:
        """获取 WebSocket 统计"""
        return await self.fallback_manager.execute_with_fallback(
            operation=lambda: self.redis_client.get_websocket_stats(),
            key=None,
            fallback_value={
                "total_connections": 0,
                "agent_connections": 0,
                "user_connections": 0,
            },
        )

    # ==================== 升级队列管理 ====================
    async def add_to_escalation_queue(
        self,
        conversation_id: str,
        priority_score: float,
    ) -> bool:
        """添加到升级队列"""
        try:
            await self.redis_client.add_to_escalation_queue(conversation_id, priority_score)
            return True
        except Exception as e:
            logger.warning(f"添加升级队列失败: {e}")
            return True

    async def get_next_escalation(self) -> str | None:
        """获取下一个升级"""
        return await self.fallback_manager.execute_with_fallback(
            operation=lambda: self.redis_client.get_next_escalation(),
            key=None,
            fallback_value=None,
        )

    async def get_escalation_queue_size(self) -> int:
        """获取升级队列大小"""
        return await self.fallback_manager.execute_with_fallback(
            operation=lambda: self.redis_client.get_escalation_queue_size(),
            key=None,
            fallback_value=0,
        )

    # ==================== 客服状态管理 ====================
    async def set_agent_status(
        self,
        agent_id: str,
        status: str,
        concurrent_chats: int,
    ) -> bool:
        """设置客服状态"""
        try:
            await self.redis_client.set_agent_status(agent_id, status, concurrent_chats)
            return True
        except Exception:
            return True

    async def get_agent_status(self, agent_id: str) -> dict | None:
        """获取客服状态"""
        key = f"agent:{agent_id}:status"

        return await self.fallback_manager.execute_with_fallback(
            operation=lambda: self.redis_client.get_agent_status(agent_id),
            key=key,
            fallback_value={"status": "offline", "concurrent_chats": 0},
            cache_ttl=300,
        )

    # ==================== 指标管理 ====================
    async def increment_metric(self, metric_name: str, value: int = 1) -> bool:
        """增加指标"""
        try:
            await self.redis_client.increment_metric(metric_name, value)
            return True
        except Exception:
            return True

    async def get_metric(self, metric_name: str) -> int:
        """获取指标"""
        return await self.fallback_manager.execute_with_fallback(
            operation=lambda: self.redis_client.get_metric(metric_name),
            key=None,
            fallback_value=0,
        )

    # ==================== 状态检查 ====================
    def get_fallback_status(self) -> dict[str, Any]:
        """获取降级状态"""
        return self.fallback_manager.get_status()

    def is_degraded(self) -> bool:
        """是否处于降级状态"""
        return self.fallback_manager._is_degraded

    def cleanup_local_cache(self):
        """清理本地缓存"""
        self.fallback_manager.cleanup_cache()


# ==================== 全局实例 ====================
_fallback_redis_client: FallbackRedisClient | None = None


async def get_fallback_redis_client() -> FallbackRedisClient:
    """获取支持降级的 Redis 客户端"""
    global _fallback_redis_client

    if _fallback_redis_client is None:
        from storage.redis_client import redis_client

        _fallback_redis_client = FallbackRedisClient(redis_client)
        await _fallback_redis_client.connect()

    return _fallback_redis_client


async def init_fallback_redis_client() -> FallbackRedisClient:
    """初始化降级 Redis 客户端"""
    global _fallback_redis_client

    from storage.redis_client import redis_client

    _fallback_redis_client = FallbackRedisClient(redis_client)
    await _fallback_redis_client.connect()

    return _fallback_redis_client


# ==================== 导出 ====================
__all__ = [
    "FallbackRedisClient",
    "get_fallback_redis_client",
    "init_fallback_redis_client",
]
