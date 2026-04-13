"""
WebSocket客户端模块 - 实现与客服工作台的实时双向通信。

提供连接管理、消息发送接收、断线重连、心跳检测等功能。
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import websockets
from langfuse import observe

logger = logging.getLogger(__name__)


@dataclass
class WSMessage:
    """WebSocket消息数据模型。

    Attributes:
        type: 消息类型 (escalation_request, agent_response, heartbeat, etc.)
        session_id: 会话ID
        payload: 消息负载数据
        timestamp: 时间戳
    """

    type: str
    session_id: str
    payload: Dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        """初始化后设置时间戳（如果未提供）。"""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。

        Returns:
            消息字典表示
        """
        return {
            "type": self.type,
            "session_id": self.session_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WSMessage":
        """从字典创建消息对象。

        Args:
            data: 消息字典

        Returns:
            WSMessage实例
        """
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class WebSocketClient:
    """WebSocket客户端 - 实现与客服工作台的实时通信。

    支持自动重连、心跳检测、消息队列等功能。

    Attributes:
        url: WebSocket服务器URL
        max_retries: 最大重连次数
        retry_delay: 重连延迟（秒）
        heartbeat_interval: 心跳间隔（秒）
    """

    def __init__(
        self,
        url: str,
        token: Optional[str] = None,
        max_retries: int = 5,
        retry_delay: float = 2.0,
        heartbeat_interval: int = 30,
    ):
        """初始化WebSocket客户端。

        Args:
            url: WebSocket服务器URL (ws:// or wss://)
            token: 认证令牌（可选）
            max_retries: 最大重连次数
            retry_delay: 重连延迟（秒）
            heartbeat_interval: 心跳间隔（秒）
        """
        self.url = url
        self.token = token
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.heartbeat_interval = heartbeat_interval

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._receive_handler: Optional[Callable] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None

        logger.info(f"WebSocketClient initialized: url={url}")

    @observe(name="websocket_connect", as_type="span")
    async def connect(self) -> None:
        """建立WebSocket连接。

        Raises:
            ConnectionError: 连接失败
        """
        retry_count = 0

        while retry_count < self.max_retries:
            try:
                headers = {}
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"

                logger.info(f"Connecting to WebSocket: {self.url}")

                self.websocket = await websockets.connect(
                    self.url,
                    extra_headers=headers,
                )

                self.connected = True
                logger.info("WebSocket connected successfully")

                # 启动心跳和接收任务
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                self._receive_task = asyncio.create_task(self._receive_loop())

                return

            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"Connection attempt {retry_count} failed: {e}. "
                    f"Retrying in {self.retry_delay * retry_count}s..."
                )

                if retry_count >= self.max_retries:
                    logger.error(f"Failed to connect after {self.max_retries} attempts")
                    raise ConnectionError(
                        f"无法连接到WebSocket服务器: {self.url}"
                    )

                await asyncio.sleep(self.retry_delay * retry_count)

    @observe(name="websocket_send_message", as_type="span")
    async def send_message(self, message: WSMessage) -> None:
        """发送消息到WebSocket服务器。

        Args:
            message: 要发送的消息对象

        Raises:
            ConnectionError: 连接未建立或已断开
        """
        if not self.connected or not self.websocket:
            raise ConnectionError("WebSocket未连接")

        try:
            message_json = json.dumps(message.to_dict())
            await self.websocket.send(message_json)
            logger.debug(f"Message sent: type={message.type}, session={message.session_id}")

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise

    @observe(name="websocket_receive_message", as_type="span")
    async def receive_message(self) -> Optional[WSMessage]:
        """接收来自WebSocket服务器的消息。

        Returns:
            接收到的消息对象，超时时返回None
        """
        try:
            message = await asyncio.wait_for(self._message_queue.get(), timeout=5.0)
            return message
        except asyncio.TimeoutError:
            return None

    def set_receive_handler(self, handler: Callable[[WSMessage], None]) -> None:
        """设置消息接收处理器。

        Args:
            handler: 消息处理回调函数
        """
        self._receive_handler = handler

    @observe(name="websocket_close", as_type="span")
    async def close(self) -> None:
        """关闭WebSocket连接。"""
        self.connected = False

        # 取消心跳和接收任务
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._receive_task:
            self._receive_task.cancel()

        # 关闭WebSocket连接
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket connection closed")

    async def _heartbeat_loop(self) -> None:
        """心跳循环 - 定期发送ping保持连接。"""
        try:
            while self.connected:
                await asyncio.sleep(self.heartbeat_interval)

                if self.websocket and self.connected:
                    try:
                        pong_waiter = await self.websocket.ping()
                        await asyncio.wait_for(pong_waiter, timeout=10)
                        logger.debug("Heartbeat ping successful")
                    except Exception as e:
                        logger.warning(f"Heartbeat failed: {e}")
                        self.connected = False
                        break

        except asyncio.CancelledError:
            logger.debug("Heartbeat loop cancelled")
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")

    async def _receive_loop(self) -> None:
        """消息接收循环 - 持续接收并处理消息。"""
        try:
            while self.connected:
                if not self.websocket:
                    break

                try:
                    message_text = await self.websocket.recv()
                    message_data = json.loads(message_text)
                    message = WSMessage.from_dict(message_data)

                    # 放入消息队列
                    await self._message_queue.put(message)

                    # 调用处理器（如果设置了）
                    if self._receive_handler:
                        self._receive_handler(message)

                    logger.debug(f"Message received: type={message.type}")

                except websockets.ConnectionClosed:
                    logger.warning("WebSocket connection closed by server")
                    self.connected = False
                    break

                except Exception as e:
                    logger.error(f"Error receiving message: {e}")

        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
        except Exception as e:
            logger.error(f"Receive loop error: {e}")

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口。"""
        await self.close()
