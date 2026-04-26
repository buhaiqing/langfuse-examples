"""会话管理路由测试

测试:
- 创建会话（P1-10 修复验证）
- 获取会话
- 添加消息
- 获取历史
- 删除会话
- 会话列表
"""

from unittest.mock import AsyncMock, patch

import pytest
from storage.redis_client import ConversationState


def _make_conversation_state(
    session_id="sess_123",
    user_id="user_456",
    current_intent=None,
    collected_slots=None,
    turn_count=0,
):
    """创建测试用 ConversationState"""
    return ConversationState(
        session_id=session_id,
        user_id=user_id,
        current_intent=current_intent,
        collected_slots=collected_slots or {},
        turn_count=turn_count,
    )


class TestConversationModels:
    """会话模型测试"""

    def test_create_conversation_request(self):
        """创建会话请求模型"""
        from api.v1.routes.conversations import CreateConversationRequest

        req = CreateConversationRequest(session_id="sess_1", user_id="user_1")
        assert req.session_id == "sess_1"
        assert req.user_id == "user_1"
        assert req.initial_slots is None

    def test_add_message_request(self):
        """添加消息请求模型"""
        from api.v1.routes.conversations import AddMessageRequest

        req = AddMessageRequest(role="user", content="你好", intent="greeting", confidence=0.9)
        assert req.role == "user"
        assert req.content == "你好"
        assert req.intent == "greeting"
        assert req.confidence == 0.9

    def test_conversation_state_response(self):
        """会话状态响应模型"""
        from api.v1.routes.conversations import ConversationStateResponse

        resp = ConversationStateResponse(
            session_id="sess_1",
            user_id="user_1",
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
            current_intent="greeting",
            collected_slots={"name": "张三"},
            turn_count=3,
        )
        assert resp.session_id == "sess_1"
        assert resp.turn_count == 3

    def test_conversation_response(self):
        """通用会话响应模型"""
        from api.v1.routes.conversations import ConversationResponse

        resp = ConversationResponse(success=True, data={"key": "value"})
        assert resp.success is True
        assert resp.data == {"key": "value"}


class TestConversationStateDataclass:
    """ConversationState 数据类测试"""

    def test_default_values(self):
        """默认值"""
        state = _make_conversation_state()
        assert state.collected_slots == {}
        assert state.turn_count == 0
        assert state.current_intent is None

    def test_auto_timestamps(self):
        """自动生成时间戳"""
        state = _make_conversation_state()
        assert state.created_at is not None
        assert state.updated_at is not None

    def test_custom_slots(self):
        """自定义槽位"""
        state = _make_conversation_state(collected_slots={"product": "手机", "issue": "黑屏"})
        assert state.collected_slots["product"] == "手机"
        assert state.collected_slots["issue"] == "黑屏"


@pytest.mark.asyncio
class TestConversationRoutes:
    """会话路由集成测试（使用 Mock Redis）"""

    async def test_create_conversation_success(self):
        """创建会话成功"""
        from api.v1.routes.conversations import CreateConversationRequest, create_conversation

        with patch("api.v1.routes.conversations.redis_client") as mock_redis:
            mock_redis.get_session_state = AsyncMock(return_value=None)
            mock_redis.save_session_state = AsyncMock()

            req = CreateConversationRequest(session_id="sess_new", user_id="user_1")
            result = await create_conversation(req)

            assert result.success is True
            assert result.data["session_id"] == "sess_new"

    async def test_create_conversation_conflict(self):
        """创建已存在的会话返回 409"""
        from api.v1.routes.conversations import CreateConversationRequest, create_conversation
        from fastapi import HTTPException

        with patch("api.v1.routes.conversations.redis_client") as mock_redis:
            existing_state = _make_conversation_state(session_id="sess_exist")
            mock_redis.get_session_state = AsyncMock(return_value=existing_state)

            req = CreateConversationRequest(session_id="sess_exist", user_id="user_1")
            with pytest.raises(HTTPException) as exc_info:
                await create_conversation(req)
            assert exc_info.value.status_code == 409

    async def test_get_conversation_success(self):
        """获取会话成功"""
        from api.v1.routes.conversations import get_conversation

        with patch("api.v1.routes.conversations.redis_client") as mock_redis:
            state = _make_conversation_state(session_id="sess_123", user_id="user_1")
            mock_redis.get_session_state = AsyncMock(return_value=state)

            result = await get_conversation("sess_123")
            assert result.success is True
            assert result.data["session_id"] == "sess_123"

    async def test_get_conversation_not_found(self):
        """获取不存在的会话返回 404"""
        from api.v1.routes.conversations import get_conversation
        from fastapi import HTTPException

        with patch("api.v1.routes.conversations.redis_client") as mock_redis:
            mock_redis.get_session_state = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_conversation("nonexistent")
            assert exc_info.value.status_code == 404

    async def test_add_message_success(self):
        """添加消息成功"""
        from api.v1.routes.conversations import AddMessageRequest, add_message

        with patch("api.v1.routes.conversations.redis_client") as mock_redis:
            state = _make_conversation_state(session_id="sess_123")
            mock_redis.get_session_state = AsyncMock(return_value=state)
            mock_redis.add_message_to_history = AsyncMock()
            mock_redis.save_session_state = AsyncMock()

            req = AddMessageRequest(role="user", content="你好", intent="greeting", confidence=0.9)
            result = await add_message("sess_123", req)

            assert result.success is True
            mock_redis.add_message_to_history.assert_called_once()

    async def test_delete_conversation_success(self):
        """删除会话成功"""
        from api.v1.routes.conversations import delete_conversation

        with patch("api.v1.routes.conversations.redis_client") as mock_redis:
            state = _make_conversation_state(session_id="sess_123")
            mock_redis.get_session_state = AsyncMock(return_value=state)
            mock_redis.delete_session_state = AsyncMock()
            mock_redis.clear_session_history = AsyncMock()

            result = await delete_conversation("sess_123")
            assert result.success is True
            mock_redis.delete_session_state.assert_called_once_with("sess_123")
            mock_redis.clear_session_history.assert_called_once_with("sess_123")

    async def test_delete_conversation_not_found(self):
        """删除不存在的会话返回 404"""
        from api.v1.routes.conversations import delete_conversation
        from fastapi import HTTPException

        with patch("api.v1.routes.conversations.redis_client") as mock_redis:
            mock_redis.get_session_state = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await delete_conversation("nonexistent")
            assert exc_info.value.status_code == 404

    async def test_get_conversation_history_success(self):
        """获取会话历史成功"""
        from api.v1.routes.conversations import get_conversation_history

        with patch("api.v1.routes.conversations.redis_client") as mock_redis:
            state = _make_conversation_state(session_id="sess_123")
            mock_redis.get_session_state = AsyncMock(return_value=state)
            mock_redis.get_session_history = AsyncMock(
                return_value=[
                    {"role": "user", "content": "你好"},
                    {"role": "assistant", "content": "您好！"},
                ]
            )

            result = await get_conversation_history("sess_123")
            assert result.success is True
            assert result.data["total"] == 2
