"""
WebSocket client for real-time communication with human agent system
Supports reconnection, heartbeat, and message queuing
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from core.logging_config import LogCategory, get_logger
from core.tracing import add_event, create_span, score_trace

logger = get_logger(LogCategory.ESCALATION)


@dataclass
class WSMessage:
    type: str
    session_id: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "session_id": self.session_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WSMessage":
        return cls(
            type=data["type"],
            session_id=data["session_id"],
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            message_id=data.get("message_id", str(uuid4())),
        )


class WebSocketClient:
    """
    WebSocket client for bidirectional communication with human agent system.
    Features:
    - Automatic reconnection with exponential backoff
    - Heartbeat detection
    - Message queue for reliability
    - Full Langfuse tracing
    """

    def __init__(
        self,
        url: str,
        session_id: str,
        max_reconnect_attempts: int = 5,
        heartbeat_interval: float = 30.0,
        reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 60.0,
    ):
        self.url = url
        self.session_id = session_id
        self.max_reconnect_attempts = max_reconnect_attempts
        self.heartbeat_interval = heartbeat_interval
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._is_connected = False
        self._is_running = False
        self._reconnect_attempts = 0
        self._message_queue: asyncio.Queue[WSMessage] = asyncio.Queue()
        self._receive_queue: asyncio.Queue[WSMessage] = asyncio.Queue()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._send_task: Optional[asyncio.Task] = None
        self._callbacks: Dict[str, List[Callable]] = {}

    async def connect(self) -> bool:
        """
        Establish WebSocket connection with automatic reconnection.

        Returns:
            True if connection successful, False otherwise
        """
        with create_span("websocket_connect", input_data={"url": self.url}) as span:
            try:
                self._ws = await websockets.connect(
                    self.url,
                    ping_interval=self.heartbeat_interval,
                    ping_timeout=10,
                    extra_headers={
                        "X-Session-ID": self.session_id,
                        "X-Client-ID": str(uuid4()),
                    },
                )
                self._is_connected = True
                self._reconnect_attempts = 0
                self._is_running = True

                span.add_event("connection_established", output_data={"session_id": self.session_id})
                score_trace("websocket_connection_success", 1.0)

                await self._start_background_tasks()
                return True

            except Exception as e:
                logger.error(f"WebSocket connection failed: {e}")
                span.add_event("connection_failed", output_data={"error": str(e)})
                score_trace("websocket_connection_success", 0.0)
                return False

    async def disconnect(self) -> None:
        """Gracefully disconnect from WebSocket server"""
        with create_span("websocket_disconnect") as span:
            self._is_running = False

            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass

            if self._receive_task:
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass

            if self._send_task:
                self._send_task.cancel()
                try:
                    await self._send_task
                except asyncio.CancelledError:
                    pass

            if self._ws:
                await self._ws.close()
                self._ws = None

            self._is_connected = False
            span.add_event("connection_closed")

    async def send_message(self, message: WSMessage) -> bool:
        """
        Send a message through WebSocket.
        Queues message if not connected.

        Args:
            message: Message to send

        Returns:
            True if sent successfully
        """
        with create_span("websocket_send_message", input_data={"message_type": message.type}) as span:
            if not self._is_connected:
                logger.warning("WebSocket not connected, queuing message")
                await self._message_queue.put(message)
                return False

            try:
                await self._ws.send(json.dumps(message.to_dict()))
                span.add_event("message_sent", output_data={"message_id": message.message_id})
                score_trace("websocket_send_latency_ms", 0)
                return True
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                await self._message_queue.put(message)
                return False

    async def receive_message(self, timeout: Optional[float] = None) -> Optional[WSMessage]:
        """
        Receive a message from WebSocket.

        Args:
            timeout: Maximum time to wait for message

        Returns:
            Received message or None
        """
        try:
            if timeout:
                return await asyncio.wait_for(self._receive_queue.get(), timeout)
            else:
                return await self._receive_queue.get()
        except asyncio.TimeoutError:
            return None

    def on_message(self, message_type: str, callback: Callable[[WSMessage], None]) -> None:
        """
        Register callback for specific message type.

        Args:
            message_type: Type of message to listen for
            callback: Callback function
        """
        if message_type not in self._callbacks:
            self._callbacks[message_type] = []
        self._callbacks[message_type].append(callback)

    async def _start_background_tasks(self) -> None:
        """Start heartbeat, receive, and send tasks"""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._receive_task = asyncio.create_task(self._receive_loop())
        self._send_task = asyncio.create_task(self._send_loop())

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to keep connection alive"""
        with create_span("websocket_heartbeat") as span:
            while self._is_running and self._is_connected:
                try:
                    await asyncio.sleep(self.heartbeat_interval)

                    if self._is_connected:
                        heartbeat_msg = WSMessage(
                            type="heartbeat",
                            session_id=self.session_id,
                            payload={"timestamp": datetime.now().isoformat()},
                        )
                        await self.send_message(heartbeat_msg)
                        logger.debug("Heartbeat sent")

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Heartbeat failed: {e}")

    async def _receive_loop(self) -> None:
        """Continuously receive messages from WebSocket"""
        with create_span("websocket_receive_loop") as span:
            while self._is_running and self._is_connected:
                try:
                    if not self._ws:
                        break

                    message_data = await self._ws.recv()
                    message = WSMessage.from_dict(json.loads(message_data))

                    logger.debug(f"Received message: {message.type}")

                    await self._receive_queue.put(message)

                    if message.type in self._callbacks:
                        for callback in self._callbacks[message.type]:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(message)
                                else:
                                    callback(message)
                            except Exception as e:
                                logger.error(f"Callback error for {message.type}: {e}")

                    span.add_event("message_received", output_data={"message_type": message.type})

                except asyncio.CancelledError:
                    break
                except ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    self._is_connected = False
                    break
                except Exception as e:
                    logger.error(f"Receive error: {e}")

    async def _send_loop(self) -> None:
        """Continuously send queued messages"""
        with create_span("websocket_send_loop") as span:
            while self._is_running and self._is_connected:
                try:
                    message = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)

                    if self._is_connected:
                        success = await self.send_message(message)
                        if not success:
                            await self._message_queue.put(message)
                    else:
                        await self._message_queue.put(message)

                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Send loop error: {e}")

    async def _reconnect(self) -> bool:
        """
        Attempt to reconnect with exponential backoff.

        Returns:
            True if reconnection successful
        """
        with create_span("websocket_reconnect") as span:
            while self._is_running and self._reconnect_attempts < self.max_reconnect_attempts:
                self._reconnect_attempts += 1

                delay = min(
                    self.reconnect_delay * (2 ** (self._reconnect_attempts - 1)),
                    self.max_reconnect_delay,
                )

                logger.info(f"Reconnecting (attempt {self._reconnect_attempts}/{self.max_reconnect_attempts})")
                span.add_event(
                    "reconnection_attempt",
                    output_data={"attempt": self._reconnect_attempts, "delay": delay},
                )

                await asyncio.sleep(delay)

                if await self.connect():
                    span.add_event("reconnection_successful")
                    return True

            span.add_event("reconnection_failed")
            return False


class EscalationWebSocketClient(WebSocketClient):
    """
    Specialized WebSocket client for escalation scenarios.
    Handles escalation requests, agent responses, and context transfer.
    """

    def __init__(self, url: str, session_id: str, **kwargs):
        super().__init__(url, session_id, **kwargs)
        self._setup_default_handlers()

    def _setup_default_handlers(self):
        """Setup default message handlers for escalation workflow"""

        def handle_agent_response(message: WSMessage):
            logger.info(f"Agent response received: {message.payload}")

        def handle_escalation_confirmed(message: WSMessage):
            logger.info(f"Escalation confirmed: {message.payload}")

        def handle_agent_typing(message: WSMessage):
            logger.debug(f"Agent typing indicator: {message.payload}")

        self.on_message("agent_response", handle_agent_response)
        self.on_message("escalation_confirmed", handle_escalation_confirmed)
        self.on_message("agent_typing", handle_agent_typing)

    async def request_escalation(
        self,
        reason: str,
        context: Dict[str, Any],
        priority: int = 0,
    ) -> bool:
        """
        Request escalation to human agent.

        Args:
            reason: Reason for escalation
            context: Conversation context and history
            priority: Priority level (0=normal, 1=high, 2=critical)

        Returns:
            True if request sent successfully
        """
        with create_span("escalation_request") as span:
            message = WSMessage(
                type="escalation_request",
                session_id=self.session_id,
                payload={
                    "reason": reason,
                    "context": context,
                    "priority": priority,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            success = await self.send_message(message)
            span.add_event(
                "escalation_requested",
                output_data={"reason": reason, "priority": priority},
            )
            return success

    async def send_user_message(self, message_text: str) -> bool:
        """
        Send user message to agent.

        Args:
            message_text: User's message

        Returns:
            True if sent successfully
        """
        message = WSMessage(
            type="user_message",
            session_id=self.session_id,
            payload={"text": message_text},
        )
        return await self.send_message(message)

    async def send_bot_message(self, message_text: str, metadata: Optional[Dict] = None) -> bool:
        """
        Send bot message to agent (for co-pilot mode).

        Args:
            message_text: Bot's response
            metadata: Additional metadata (confidence, sources, etc.)

        Returns:
            True if sent successfully
        """
        message = WSMessage(
            type="bot_message",
            session_id=self.session_id,
            payload={
                "text": message_text,
                "metadata": metadata or {},
            },
        )
        return await self.send_message(message)

    async def acknowledge_agent_message(self, message_id: str) -> bool:
        """
        Acknowledge receipt of agent message.

        Args:
            message_id: ID of message to acknowledge

        Returns:
            True if acknowledgment sent
        """
        message = WSMessage(
            type="message_ack",
            session_id=self.session_id,
            payload={"acknowledged_message_id": message_id},
        )
        return await self.send_message(message)


def create_escalation_websocket(
    url: str,
    session_id: str,
    **kwargs,
) -> EscalationWebSocketClient:
    """
    Factory function to create escalation WebSocket client.

    Args:
        url: WebSocket server URL
        session_id: Session identifier
        **kwargs: Additional configuration

    Returns:
        EscalationWebSocketClient instance
    """
    return EscalationWebSocketClient(url, session_id, **kwargs)
