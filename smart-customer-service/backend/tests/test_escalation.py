"""
Tests for WebSocket client and queue manager
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.escalation.websocket_client import (
    WebSocketClient,
    EscalationWebSocketClient,
    WSMessage,
    create_escalation_websocket,
)
from modules.escalation.queue_manager import (
    QueueManager,
    ContextPackager,
    EscalationContext,
    create_queue_manager,
    create_context_packager,
)


class TestWSMessage:
    """Test WSMessage dataclass"""

    def test_create_message(self):
        msg = WSMessage(
            type="test",
            session_id="session_123",
            payload={"key": "value"},
        )
        assert msg.type == "test"
        assert msg.session_id == "session_123"
        assert msg.payload == {"key": "value"}
        assert msg.message_id is not None

    def test_message_to_dict(self):
        msg = WSMessage(
            type="test",
            session_id="session_123",
            payload={"key": "value"},
        )
        data = msg.to_dict()
        assert data["type"] == "test"
        assert data["session_id"] == "session_123"
        assert "timestamp" in data

    def test_message_from_dict(self):
        data = {
            "type": "test",
            "session_id": "session_123",
            "payload": {"key": "value"},
            "timestamp": "2026-04-13T10:00:00",
            "message_id": "msg_123",
        }
        msg = WSMessage.from_dict(data)
        assert msg.type == "test"
        assert msg.session_id == "session_123"
        assert msg.message_id == "msg_123"


class TestWebSocketClient:
    """Test WebSocket client"""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value = mock_ws

            client = WebSocketClient("ws://test.com", "session_123")
            result = await client.connect()

            assert result is True
            assert client._is_connected is True
            assert client._ws is not None

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        with patch("websockets.connect", side_effect=Exception("Connection failed")):
            client = WebSocketClient("ws://test.com", "session_123")
            result = await client.connect()

            assert result is False
            assert client._is_connected is False

    @pytest.mark.asyncio
    async def test_send_message_connected(self):
        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value = mock_ws

            client = WebSocketClient("ws://test.com", "session_123")
            await client.connect()

            msg = WSMessage(
                type="test",
                session_id="session_123",
                payload={"key": "value"},
            )
            result = await client.send_message(msg)

            assert result is True
            mock_ws.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_not_connected(self):
        client = WebSocketClient("ws://test.com", "session_123")
        msg = WSMessage(
            type="test",
            session_id="session_123",
            payload={"key": "value"},
        )

        result = await client.send_message(msg)

        assert result is False
        assert not client._message_queue.empty()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value = mock_ws

            client = WebSocketClient("ws://test.com", "session_123")
            await client.connect()

            await client.disconnect()

            assert client._is_connected is False
            mock_ws.close.assert_called_once()


class TestEscalationWebSocketClient:
    """Test escalation-specific WebSocket client"""

    @pytest.mark.asyncio
    async def test_request_escalation(self):
        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value = mock_ws

            client = EscalationWebSocketClient("ws://test.com", "session_123")
            await client.connect()

            context = {
                "dialogue_history": [],
                "collected_slots": {},
                "attempted_solutions": [],
            }
            result = await client.request_escalation(
                reason="low_confidence",
                context=context,
                priority=1,
            )

            assert result is True
            mock_ws.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_user_message(self):
        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value = mock_ws

            client = EscalationWebSocketClient("ws://test.com", "session_123")
            await client.connect()

            result = await client.send_user_message("Hello")

            assert result is True

    @pytest.mark.asyncio
    async def test_send_bot_message(self):
        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value = mock_ws

            client = EscalationWebSocketClient("ws://test.com", "session_123")
            await client.connect()

            result = await client.send_bot_message(
                "Bot response",
                metadata={"confidence": 0.9},
            )

            assert result is True


class TestEscalationContext:
    """Test EscalationContext dataclass"""

    def test_create_context(self):
        context = EscalationContext(
            session_id="session_123",
            user_id="user_456",
            user_profile={"name": "Test User"},
            dialogue_history=[{"role": "user", "content": "Hello"}],
            collected_slots={"ticket_id": "TKT-123"},
            attempted_solutions=["Solution 1"],
            escalation_reason="complex_issue",
            sentiment_score=-0.5,
            priority=1,
        )

        assert context.session_id == "session_123"
        assert context.user_id == "user_456"
        assert context.priority == 1

    def test_context_to_dict(self):
        context = EscalationContext(
            session_id="session_123",
            user_id="user_456",
            user_profile={},
            dialogue_history=[],
            collected_slots={},
            attempted_solutions=[],
            escalation_reason="test",
            sentiment_score=0.0,
        )

        data = context.to_dict()
        assert data["session_id"] == "session_123"
        assert "created_at" in data

    def test_context_from_dict(self):
        data = {
            "session_id": "session_123",
            "user_id": "user_456",
            "user_profile": {},
            "dialogue_history": [],
            "collected_slots": {},
            "attempted_solutions": [],
            "escalation_reason": "test",
            "sentiment_score": 0.0,
            "created_at": "2026-04-13T10:00:00",
            "priority": 0,
        }

        context = EscalationContext.from_dict(data)
        assert context.session_id == "session_123"
        assert context.escalation_reason == "test"


class TestQueueManager:
    """Test queue manager"""

    @pytest.mark.asyncio
    async def test_enqueue(self):
        manager = create_queue_manager()

        context = EscalationContext(
            session_id="session_123",
            user_id="user_456",
            user_profile={},
            dialogue_history=[],
            collected_slots={},
            attempted_solutions=[],
            escalation_reason="test",
            sentiment_score=0.0,
        )

        queue_id = await manager.enqueue(context)

        assert queue_id is not None
        assert len(manager._queue) == 1

    @pytest.mark.asyncio
    async def test_dequeue(self):
        manager = create_queue_manager()

        context = EscalationContext(
            session_id="session_123",
            user_id="user_456",
            user_profile={},
            dialogue_history=[],
            collected_slots={},
            attempted_solutions=[],
            escalation_reason="test",
            sentiment_score=0.0,
        )

        queue_id = await manager.enqueue(context)
        entry = await manager.dequeue()

        assert entry is not None
        assert entry.queue_id == queue_id
        assert len(manager._queue) == 0

    @pytest.mark.asyncio
    async def test_get_position(self):
        manager = create_queue_manager()

        context = EscalationContext(
            session_id="session_123",
            user_id="user_456",
            user_profile={},
            dialogue_history=[],
            collected_slots={},
            attempted_solutions=[],
            escalation_reason="test",
            sentiment_score=0.0,
        )

        queue_id = await manager.enqueue(context)
        position = await manager.get_position(queue_id)

        assert position == 1

    @pytest.mark.asyncio
    async def test_priority_queue(self):
        manager = create_queue_manager()

        context1 = EscalationContext(
            session_id="session_1",
            user_id="user_1",
            user_profile={},
            dialogue_history=[],
            collected_slots={},
            attempted_solutions=[],
            escalation_reason="test",
            sentiment_score=0.0,
            priority=0,
        )

        context2 = EscalationContext(
            session_id="session_2",
            user_id="user_2",
            user_profile={},
            dialogue_history=[],
            collected_slots={},
            attempted_solutions=[],
            escalation_reason="test",
            sentiment_score=0.0,
            priority=2,
        )

        queue_id1 = await manager.enqueue(context1)
        queue_id2 = await manager.enqueue(context2)

        entry = await manager.dequeue()
        assert entry.queue_id == queue_id2

    @pytest.mark.asyncio
    async def test_assign_agent(self):
        manager = create_queue_manager()

        context = EscalationContext(
            session_id="session_123",
            user_id="user_456",
            user_profile={},
            dialogue_history=[],
            collected_slots={},
            attempted_solutions=[],
            escalation_reason="test",
            sentiment_score=0.0,
        )

        queue_id = await manager.enqueue(context)
        result = await manager.assign_agent(queue_id, "agent_0")

        assert result is True
        entry = manager._queue_map[queue_id]
        assert entry.assigned_agent == "agent_0"

    @pytest.mark.asyncio
    async def test_get_queue_stats(self):
        manager = create_queue_manager()

        context = EscalationContext(
            session_id="session_123",
            user_id="user_456",
            user_profile={},
            dialogue_history=[],
            collected_slots={},
            attempted_solutions=[],
            escalation_reason="test",
            sentiment_score=0.0,
        )

        await manager.enqueue(context)
        stats = await manager.get_queue_stats()

        assert stats["queue_length"] == 1
        assert stats["available_agents"] == 5
        assert stats["total_agents"] == 5


class TestContextPackager:
    """Test context packager"""

    def test_package_context(self):
        packager = create_context_packager()

        conversation_state = MagicMock()
        conversation_state.history = [
            {"role": "user", "content": "Hello", "timestamp": "2026-04-13T10:00:00"},
            {"role": "assistant", "content": "Hi", "timestamp": "2026-04-13T10:00:01"},
        ]
        conversation_state.collected_slots = {"ticket_id": "TKT-123"}
        conversation_state.attempted_solutions = ["Solution 1"]
        conversation_state.intent = "api_error"
        conversation_state.turn_count = 2
        conversation_state.entities = {"email": "test@example.com"}

        context = packager.package_context(
            session_id="session_123",
            user_id="user_456",
            conversation_state=conversation_state,
            escalation_reason="complex_issue",
            sentiment_score=-0.5,
            priority=1,
        )

        assert context.session_id == "session_123"
        assert len(context.dialogue_history) == 2
        assert context.collected_slots == {"ticket_id": "TKT-123"}
        assert len(context.attempted_solutions) == 1
        assert context.priority == 1


class TestFactoryFunctions:
    """Test factory functions"""

    def test_create_queue_manager(self):
        manager = create_queue_manager(
            max_queue_size=50,
            base_wait_time=60,
            agent_count=3,
        )

        assert manager.max_queue_size == 50
        assert manager.base_wait_time == 60
        assert len(manager._agent_status) == 3

    def test_create_context_packager(self):
        packager = create_context_packager(max_history_length=10)
        assert packager.max_history_length == 10

    def test_create_escalation_websocket(self):
        client = create_escalation_websocket(
            url="ws://test.com",
            session_id="session_123",
            max_reconnect_attempts=3,
        )

        assert client.url == "ws://test.com"
        assert client.session_id == "session_123"
        assert client.max_reconnect_attempts == 3
