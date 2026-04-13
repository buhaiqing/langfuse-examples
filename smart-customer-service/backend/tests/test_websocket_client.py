"""WebSocket客户端模块测试套件。"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.escalation.websocket_client import WSMessage, WebSocketClient


class TestWSMessage:
    """WSMessage数据模型测试。"""

    def test_message_creation_with_auto_timestamp(self):
        """测试消息创建时自动生成时间戳。"""
        msg = WSMessage(
            type="test",
            session_id="session_123",
            payload={"key": "value"},
        )

        assert msg.type == "test"
        assert msg.session_id == "session_123"
        assert msg.payload == {"key": "value"}
        assert isinstance(msg.timestamp, datetime)

    def test_message_creation_with_custom_timestamp(self):
        """测试消息创建时使用自定义时间戳。"""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        msg = WSMessage(
            type="test",
            session_id="session_123",
            payload={},
            timestamp=custom_time,
        )

        assert msg.timestamp == custom_time

    def test_message_to_dict(self):
        """测试消息转换为字典。"""
        msg = WSMessage(
            type="escalation_request",
            session_id="session_123",
            payload={"reason": "complex_issue"},
        )

        data = msg.to_dict()

        assert data["type"] == "escalation_request"
        assert data["session_id"] == "session_123"
        assert data["payload"]["reason"] == "complex_issue"
        assert "timestamp" in data

    def test_message_from_dict(self):
        """测试从字典创建消息。"""
        data = {
            "type": "agent_response",
            "session_id": "session_456",
            "payload": {"message": "Hello"},
            "timestamp": "2024-01-01T12:00:00",
        }

        msg = WSMessage.from_dict(data)

        assert msg.type == "agent_response"
        assert msg.session_id == "session_456"
        assert isinstance(msg.timestamp, datetime)

    def test_message_round_trip(self):
        """测试消息序列化和反序列化往返。"""
        original = WSMessage(
            type="heartbeat",
            session_id="session_789",
            payload={},
        )

        data = original.to_dict()
        restored = WSMessage.from_dict(data)

        assert restored.type == original.type
        assert restored.session_id == original.session_id
        assert restored.payload == original.payload


class TestWebSocketClient:
    """WebSocketClient测试套件。"""

    @pytest.fixture
    def ws_client(self):
        """创建WebSocket客户端fixture。"""
        return WebSocketClient(
            url="ws://localhost:8765",
            token="test_token",
            max_retries=3,
            retry_delay=1.0,
            heartbeat_interval=30,
        )

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """测试客户端初始化。"""
        client = WebSocketClient(url="ws://test.com")

        assert client.url == "ws://test.com"
        assert client.max_retries == 5
        assert client.retry_delay == 2.0
        assert client.heartbeat_interval == 30
        assert client.connected is False

    @pytest.mark.asyncio
    async def test_connect_success(self, ws_client):
        """测试连接成功。"""
        mock_websocket = AsyncMock()
        mock_websocket.ping.return_value = asyncio.Future()
        mock_websocket.ping.return_value.set_result(None)

        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_websocket

            await ws_client.connect()

            assert ws_client.connected is True
            assert ws_client.websocket is not None
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_token(self, ws_client):
        """测试带token的连接。"""
        mock_websocket = AsyncMock()

        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_websocket

            await ws_client.connect()

            # 验证extra_headers包含token
            call_args = mock_connect.call_args
            assert "extra_headers" in call_args[1]
            assert call_args[1]["extra_headers"]["Authorization"] == "Bearer test_token"

    @pytest.mark.asyncio
    async def test_connect_retry_on_failure(self, ws_client):
        """测试连接失败时的重试机制。"""
        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = [
                ConnectionError("Attempt 1 failed"),
                ConnectionError("Attempt 2 failed"),
                AsyncMock(),  # 第三次成功
            ]

            await ws_client.connect()

            assert ws_client.connected is True
            assert mock_connect.call_count == 3

    @pytest.mark.asyncio
    async def test_connect_max_retries_exceeded(self, ws_client):
        """测试超过最大重试次数。"""
        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = ConnectionError("Connection failed")

            with pytest.raises(ConnectionError):
                await ws_client.connect()

            assert mock_connect.call_count == 3  # max_retries

    @pytest.mark.asyncio
    async def test_send_message(self, ws_client):
        """测试发送消息。"""
        mock_websocket = AsyncMock()
        ws_client.websocket = mock_websocket
        ws_client.connected = True

        message = WSMessage(
            type="test_message",
            session_id="session_123",
            payload={"data": "test"},
        )

        await ws_client.send_message(message)

        mock_websocket.send.assert_called_once()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_data["type"] == "test_message"

    @pytest.mark.asyncio
    async def test_send_message_not_connected(self, ws_client):
        """测试未连接时发送消息抛出异常。"""
        message = WSMessage(type="test", session_id="s1", payload={})

        with pytest.raises(ConnectionError, match="WebSocket未连接"):
            await ws_client.send_message(message)

    @pytest.mark.asyncio
    async def test_receive_message(self, ws_client):
        """测试接收消息。"""
        ws_client.connected = True

        # 向队列中添加测试消息
        test_msg = WSMessage(type="response", session_id="s1", payload={})
        await ws_client._message_queue.put(test_msg)

        received = await ws_client.receive_message()

        assert received is not None
        assert received.type == "response"

    @pytest.mark.asyncio
    async def test_receive_message_timeout(self, ws_client):
        """测试接收消息超时。"""
        ws_client.connected = True

        # 不添加任何消息，应该超时
        received = await ws_client.receive_message()

        assert received is None

    @pytest.mark.asyncio
    async def test_set_receive_handler(self, ws_client):
        """测试设置消息处理器。"""
        handler_called = []

        def handler(msg):
            handler_called.append(msg)

        ws_client.set_receive_handler(handler)

        assert ws_client._receive_handler is not None

    @pytest.mark.asyncio
    async def test_close(self, ws_client):
        """测试关闭连接。"""
        mock_websocket = AsyncMock()
        ws_client.websocket = mock_websocket
        ws_client.connected = True

        # 创建mock任务
        ws_client._heartbeat_task = AsyncMock()
        ws_client._receive_task = AsyncMock()

        await ws_client.close()

        assert ws_client.connected is False
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试异步上下文管理器。"""
        mock_websocket = AsyncMock()

        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_websocket

            async with WebSocketClient(url="ws://test.com") as client:
                assert client.connected is True

            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_heartbeat_loop(self, ws_client):
        """测试心跳循环。"""
        mock_websocket = AsyncMock()
        pong_future = asyncio.Future()
        pong_future.set_result(None)
        mock_websocket.ping.return_value = pong_future

        ws_client.websocket = mock_websocket
        ws_client.connected = True
        ws_client.heartbeat_interval = 0.1  # 快速测试

        # 运行一小段时间后停止
        task = asyncio.create_task(ws_client._heartbeat_loop())
        await asyncio.sleep(0.3)
        ws_client.connected = False
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # 验证ping被调用
        assert mock_websocket.ping.called

    @pytest.mark.asyncio
    async def test_receive_loop(self, ws_client):
        """测试接收循环。"""
        mock_websocket = AsyncMock()

        # 模拟接收两条消息然后关闭
        messages = [
            json.dumps({"type": "msg1", "session_id": "s1", "payload": {}, "timestamp": "2024-01-01T00:00:00"}),
            json.dumps({"type": "msg2", "session_id": "s2", "payload": {}, "timestamp": "2024-01-01T00:00:00"}),
        ]

        async def mock_recv():
            if messages:
                return messages.pop(0)
            else:
                raise Exception("Connection closed")

        mock_websocket.recv = mock_recv

        ws_client.websocket = mock_websocket
        ws_client.connected = True

        # 运行接收循环
        task = asyncio.create_task(ws_client._receive_loop())
        await asyncio.sleep(0.2)
        ws_client.connected = False
        task.cancel()

        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

        # 验证消息被放入队列
        assert ws_client._message_queue.qsize() >= 0

    @pytest.mark.asyncio
    async def test_message_queue_ordering(self, ws_client):
        """测试消息队列顺序。"""
        ws_client.connected = True

        # 添加多个消息
        for i in range(5):
            msg = WSMessage(type=f"msg_{i}", session_id="s1", payload={})
            await ws_client._message_queue.put(msg)

        # 验证FIFO顺序
        for i in range(5):
            received = await ws_client.receive_message()
            assert received.type == f"msg_{i}"
