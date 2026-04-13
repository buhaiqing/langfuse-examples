"""WebSocket 测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from backend.api.websocket_handler import (
    WebSocketManager,
    WebSocketConnection,
    websocket_manager,
    broadcast_escalation,
    notify_session_update,
)


class TestWebSocketManager:
    """WebSocket 管理器测试"""

    @pytest.fixture
    def manager(self):
        """创建 WebSocket 管理器实例"""
        return WebSocketManager()

    def test_init(self, manager):
        """测试初始化"""
        assert len(manager.active_connections) == 0
        assert len(manager.agent_connections) == 0
        assert len(manager.user_connections) == 0
        assert manager.heartbeat_timeout == 30
        assert manager.max_missed_heartbeats == 3

    @pytest.mark.asyncio
    async def test_connect_agent(self, manager):
        """测试客服连接"""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_json = AsyncMock()

        success = await manager.connect(mock_websocket, "agent_001", is_agent=True)

        assert success is True
        assert "agent_001" in manager.active_connections
        assert "agent_001" in manager.agent_connections
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_user(self, manager):
        """测试用户连接"""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_json = AsyncMock()

        success = await manager.connect(mock_websocket, "user_123", is_agent=False)

        assert success is True
        assert "user_123" in manager.active_connections
        assert "user_123" in manager.user_connections

    def test_disconnect(self, manager):
        """测试断开连接"""
        # 先添加连接
        mock_websocket = AsyncMock()
        manager.active_connections["agent_001"] = WebSocketConnection(
            websocket=mock_websocket,
            client_id="agent_001",
            connection_time=datetime.utcnow(),
            last_heartbeat=datetime.utcnow(),
            is_agent=True,
        )
        manager.agent_connections.add("agent_001")

        # 断开
        manager.disconnect("agent_001")

        assert "agent_001" not in manager.active_connections
        assert "agent_001" not in manager.agent_connections

    @pytest.mark.asyncio
    async def test_send_personal_message(self, manager):
        """测试发送个人消息"""
        mock_websocket = AsyncMock()
        manager.active_connections["agent_001"] = WebSocketConnection(
            websocket=mock_websocket,
            client_id="agent_001",
            connection_time=datetime.utcnow(),
            last_heartbeat=datetime.utcnow(),
            is_agent=True,
        )

        await manager.send_personal_message(mock_websocket, {"type": "test", "data": "value"})

        mock_websocket.send_json.assert_called_once_with({"type": "test", "data": "value"})

    @pytest.mark.asyncio
    async def test_broadcast_to_agents(self, manager):
        """测试广播到所有客服"""
        # 添加多个客服连接
        for i in range(3):
            agent_id = f"agent_{i}"
            manager.active_connections[agent_id] = WebSocketConnection(
                websocket=AsyncMock(),
                client_id=agent_id,
                connection_time=datetime.utcnow(),
                last_heartbeat=datetime.utcnow(),
                is_agent=True,
            )
            manager.agent_connections.add(agent_id)

        message = {"type": "broadcast", "data": "test"}
        await manager.broadcast_to_agents(message)

        # 验证所有客服都收到了消息
        for agent_id in manager.agent_connections:
            connection = manager.active_connections[agent_id]
            connection.websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_agents_with_exclude(self, manager):
        """测试带排除的广播"""
        # 添加客服连接
        for i in range(3):
            agent_id = f"agent_{i}"
            manager.active_connections[agent_id] = WebSocketConnection(
                websocket=AsyncMock(),
                client_id=agent_id,
                connection_time=datetime.utcnow(),
                last_heartbeat=datetime.utcnow(),
                is_agent=True,
            )
            manager.agent_connections.add(agent_id)

        message = {"type": "broadcast", "data": "test"}
        await manager.broadcast_to_agents(message, exclude={"agent_0"})

        # agent_0 不应该收到消息
        assert manager.active_connections["agent_0"].websocket.send_json.call_count == 0

        # 其他客服应该收到
        for i in range(1, 3):
            agent_id = f"agent_{i}"
            manager.active_connections[agent_id].websocket.send_json.assert_called_once_with(
                message
            )

    @pytest.mark.asyncio
    async def test_handle_heartbeat(self, manager):
        """测试心跳处理"""
        old_time = datetime.utcnow()
        manager.active_connections["agent_001"] = WebSocketConnection(
            websocket=AsyncMock(),
            client_id="agent_001",
            connection_time=old_time,
            last_heartbeat=old_time,
            is_agent=True,
        )

        await manager.handle_heartbeat("agent_001")

        assert manager.active_connections["agent_001"].last_heartbeat > old_time

    @pytest.mark.asyncio
    async def test_check_heartbeats(self, manager):
        """测试心跳检查"""
        # 添加一个超时连接
        old_time = datetime.utcnow()
        manager.active_connections["agent_001"] = WebSocketConnection(
            websocket=AsyncMock(),
            client_id="agent_001",
            connection_time=old_time,
            last_heartbeat=old_time,
            is_agent=True,
        )

        # 等待超时
        import asyncio

        await asyncio.sleep(35)  # 超过 30 秒超时

        await manager.check_heartbeats()

        # 超时连接应该被断开
        assert "agent_001" not in manager.active_connections

    def test_get_stats(self, manager):
        """测试获取统计信息"""
        # 添加一些连接
        for i in range(2):
            agent_id = f"agent_{i}"
            manager.active_connections[agent_id] = WebSocketConnection(
                websocket=AsyncMock(),
                client_id=agent_id,
                connection_time=datetime.utcnow(),
                last_heartbeat=datetime.utcnow(),
                is_agent=True,
            )
            manager.agent_connections.add(agent_id)

        stats = manager.get_stats()

        assert stats["total_connections"] == 2
        assert stats["agent_connections"] == 2
        assert stats["user_connections"] == 0


class TestBroadcastEscalation:
    """广播升级测试"""

    @pytest.mark.asyncio
    async def test_broadcast_escalation(self):
        """测试广播升级通知"""
        escalation_data = {
            "session_id": "sess_123",
            "priority_level": "critical",
            "trigger_reasons": ["negative_sentiment"],
        }

        with patch("backend.api.websocket_handler.websocket_manager") as mock_manager:
            await broadcast_escalation(escalation_data)

            mock_manager.broadcast_to_agents.assert_called_once()


class TestNotifySessionUpdate:
    """会话更新通知测试"""

    @pytest.mark.asyncio
    async def test_notify_session_update(self):
        """测试通知会话更新"""
        update_data = {
            "status": "active",
            "message_count": 10,
        }

        with patch("backend.api.websocket_handler.websocket_manager") as mock_manager:
            await notify_session_update("sess_123", update_data)

            mock_manager.broadcast_to_agents.assert_called_once()
