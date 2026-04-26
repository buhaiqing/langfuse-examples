"""
WebSocket Redis 同步测试

测试:
- Pub/Sub 消息发布订阅
- 多实例消息同步
- 客服状态广播
"""

from unittest.mock import AsyncMock, MagicMock

from services.websocket_sync import (
    PubSubMessage,
    RedisPubSubManager,
    WebSocketSyncService,
    WSMessageType,
)


class TestPubSubMessage:
    """Pub/Sub 消息测试"""

    def test_message_creation(self):
        """测试消息创建"""
        msg = PubSubMessage(
            type=WSMessageType.NEW_MESSAGE,
            payload={"session_id": "test_session"},
            source_instance="instance_1",
        )

        assert msg.type == WSMessageType.NEW_MESSAGE
        assert msg.payload["session_id"] == "test_session"
        assert msg.source_instance == "instance_1"
        assert msg.timestamp is not None

    def test_message_with_target(self):
        """测试定向消息"""
        msg = PubSubMessage(
            type=WSMessageType.AGENT_STATUS_UPDATE,
            payload={"status": "online"},
            source_instance="instance_1",
            target="agent_001",
        )

        assert msg.target == "agent_001"


class TestRedisPubSubManager:
    """Redis Pub/Sub 管理器测试"""

    def test_initial_state(self):
        """测试初始状态"""
        manager = RedisPubSubManager("test_instance")

        assert manager.instance_id == "test_instance"
        assert manager._connected is False
        assert len(manager._local_connections) == 0

    def test_register_local_connection(self):
        """测试注册本地连接"""
        manager = RedisPubSubManager("test_instance")

        mock_connection = MagicMock()
        mock_connection.send_json = AsyncMock()

        manager.register_local_connection(
            client_id="agent_001",
            connection=mock_connection,
            connection_type="agent",
        )

        assert "agent_001" in manager._local_connections
        assert manager._local_connections["agent_001"]["type"] == "agent"

    def test_unregister_local_connection(self):
        """测试取消注册连接"""
        manager = RedisPubSubManager("test_instance")

        manager.register_local_connection(
            client_id="agent_001",
            connection=MagicMock(),
            connection_type="agent",
        )

        manager.unregister_local_connection("agent_001")

        assert "agent_001" not in manager._local_connections

    def test_get_local_connections_count(self):
        """测试获取连接数量"""
        manager = RedisPubSubManager("test_instance")

        # 注册多个连接
        manager.register_local_connection("agent_1", MagicMock(), "agent")
        manager.register_local_connection("agent_2", MagicMock(), "agent")
        manager.register_local_connection("user_1", MagicMock(), "user")

        assert manager.get_local_connections_count() == 3
        assert manager.get_local_connections_count("agent") == 2
        assert manager.get_local_connections_count("user") == 1

    def test_register_handler(self):
        """测试注册消息处理器"""
        manager = RedisPubSubManager("test_instance")

        async def handler(payload, source):
            pass

        manager.register_handler(WSMessageType.NEW_MESSAGE, handler)

        assert WSMessageType.NEW_MESSAGE in manager._message_handlers

    def test_get_stats(self):
        """测试获取统计"""
        manager = RedisPubSubManager("test_instance")

        stats = manager.get_stats()

        assert "instance_id" in stats
        assert "connected" in stats
        assert "local_connections" in stats


class TestWebSocketSyncService:
    """WebSocket 同步服务测试"""

    def test_initial_state(self):
        """测试初始状态"""
        service = WebSocketSyncService("test_instance")

        assert service._initialized is False
        assert service.pubsub_manager is not None

    def test_register_connection(self):
        """测试注册连接"""
        service = WebSocketSyncService("test_instance")

        mock_connection = MagicMock()
        service.register_connection(
            client_id="agent_001",
            connection=mock_connection,
            is_agent=True,
        )

        stats = service.get_stats()
        assert stats["local_agents"] == 1


class TestWSMessageType:
    """WebSocket 消息类型测试"""

    def test_message_types_defined(self):
        """测试消息类型定义"""
        assert WSMessageType.CONNECT == "connect"
        assert WSMessageType.DISCONNECT == "disconnect"
        assert WSMessageType.HEARTBEAT == "heartbeat"
        assert WSMessageType.AGENT_STATUS_UPDATE == "agent_status_update"
        assert WSMessageType.NEW_MESSAGE == "new_message"
        assert WSMessageType.ESCALATION_REQUEST == "escalation_request"
        assert WSMessageType.BROADCAST_AGENTS == "broadcast_agents"
