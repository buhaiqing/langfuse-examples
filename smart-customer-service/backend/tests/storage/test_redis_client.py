"""Redis 客户端测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from backend.storage.redis_client import (
    RedisClient,
    RedisKeys,
    ConversationState,
)


class TestRedisKeys:
    """Redis 键命名测试"""

    def test_session_state_key(self):
        """测试会话状态键名"""
        key = RedisKeys.session_state("sess_123")
        assert key == "session:sess_123:state"

    def test_session_history_key(self):
        """测试会话历史键名"""
        key = RedisKeys.session_history("sess_456")
        assert key == "session:sess_456:history"

    def test_user_profile_key(self):
        """测试用户画像键名"""
        key = RedisKeys.user_profile("user_789")
        assert key == "user:user_789:profile"

    def test_cache_product_key(self):
        """测试产品缓存键名"""
        key = RedisKeys.cache_product("prod_001")
        assert key == "cache:product:prod_001:info"

    def test_queue_escalation_key(self):
        """测试升级队列键名"""
        assert RedisKeys.QUEUE_ESCALATION == "queue:escalation"


class TestConversationState:
    """会话状态模型测试"""

    def test_create_conversation_state(self):
        """测试创建会话状态"""
        state = ConversationState(
            session_id="sess_123",
            user_id="user_456",
            current_intent="api_error_troubleshooting",
            collected_slots={"error_code": "403"},
            turn_count=5,
            created_at="2026-04-13T10:00:00Z",
            updated_at="2026-04-13T10:05:00Z",
        )

        assert state.session_id == "sess_123"
        assert state.user_id == "user_456"
        assert state.current_intent == "api_error_troubleshooting"
        assert state.collected_slots["error_code"] == "403"
        assert state.turn_count == 5


class TestRedisClient:
    """Redis 客户端测试"""

    @pytest.fixture
    def redis_client(self):
        """创建 Redis 客户端实例"""
        return RedisClient()

    def test_init_default_values(self, redis_client):
        """测试初始化默认值"""
        assert redis_client.client is None
        assert redis_client._ttl_seconds > 0

    @pytest.mark.asyncio
    async def test_connect(self, redis_client):
        """测试连接 Redis"""
        with patch("backend.storage.redis_client.redis.Redis") as mock_redis:
            await redis_client.connect()

            assert redis_client.client is not None
            mock_redis.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_success(self, redis_client):
        """测试 ping 成功"""
        redis_client.client = AsyncMock()
        redis_client.client.ping = AsyncMock(return_value=True)

        result = await redis_client.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_ping_failure(self, redis_client):
        """测试 ping 失败"""
        redis_client.client = None

        result = await redis_client.ping()
        assert result is False

    @pytest.mark.asyncio
    async def test_save_session_state(self, redis_client):
        """测试保存会话状态"""
        redis_client.client = AsyncMock()

        state = ConversationState(
            session_id="sess_123",
            user_id="user_456",
            current_intent=None,
            collected_slots={},
            turn_count=1,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        await redis_client.save_session_state(state)

        redis_client.client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_state_exists(self, redis_client):
        """测试获取存在的会话状态"""
        redis_client.client = AsyncMock()
        redis_client.client.get = AsyncMock(
            return_value='{"session_id":"sess_123","user_id":"user_456","current_intent":null,"collected_slots":{},"turn_count":1,"created_at":"2026-04-13T10:00:00Z","updated_at":"2026-04-13T10:00:00Z"}'
        )

        result = await redis_client.get_session_state("sess_123")

        assert result is not None
        assert result.session_id == "sess_123"

    @pytest.mark.asyncio
    async def test_get_session_state_not_exists(self, redis_client):
        """测试获取不存在的会话状态"""
        redis_client.client = AsyncMock()
        redis_client.client.get = AsyncMock(return_value=None)

        result = await redis_client.get_session_state("sess_999")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_session_state(self, redis_client):
        """测试删除会话状态"""
        redis_client.client = AsyncMock()

        await redis_client.delete_session_state("sess_123")

        redis_client.client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_message_to_history(self, redis_client):
        """测试添加消息到历史"""
        redis_client.client = AsyncMock()

        await redis_client.add_message_to_history(
            session_id="sess_123",
            role="user",
            content="Hello",
            metadata={"intent": "greeting"},
        )

        redis_client.client.rpush.assert_called_once()
        redis_client.client.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_history(self, redis_client):
        """测试获取会话历史"""
        redis_client.client = AsyncMock()
        redis_client.client.lrange = AsyncMock(return_value=['{"role":"user","content":"Hello"}'])

        result = await redis_client.get_session_history("sess_123", limit=10)

        assert len(result) == 1
        assert result[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_cache_set_get(self, redis_client):
        """测试缓存设置和获取"""
        redis_client.client = AsyncMock()
        redis_client.client.get = AsyncMock(return_value='{"key":"value"}')

        await redis_client.cache_set("test_key", {"key": "value"}, ttl_seconds=3600)
        result = await redis_client.cache_get("test_key")

        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_add_to_escalation_queue(self, redis_client):
        """测试添加到升级队列"""
        redis_client.client = AsyncMock()

        await redis_client.add_to_escalation_queue("sess_123", priority_score=85.5)

        redis_client.client.zadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_next_escalation(self, redis_client):
        """测试获取下一个升级"""
        redis_client.client = AsyncMock()
        redis_client.client.zpopmax = AsyncMock(return_value=[("sess_123", 85.5)])

        result = await redis_client.get_next_escalation()

        assert result == "sess_123"

    @pytest.mark.asyncio
    async def test_get_escalation_queue_size(self, redis_client):
        """测试获取队列大小"""
        redis_client.client = AsyncMock()
        redis_client.client.zcard = AsyncMock(return_value=5)

        size = await redis_client.get_escalation_queue_size()

        assert size == 5
