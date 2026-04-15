"""
WebSocket Redis Pub/Sub 集成模块

提供:
- 多实例 WebSocket 连接同步
- Redis Pub/Sub 广播机制
- 断线重连状态恢复
- 跨实例消息推送
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Set, Callable
from datetime import datetime
from dataclasses import dataclass, field

import redis.asyncio as redis
from redis.asyncio import Redis

from core.config import settings
from storage.redis_client import redis_client, RedisKeys

logger = logging.getLogger(__name__)


# ==================== 消息类型定义 ====================
class WSMessageType:
    """WebSocket 消息类型"""
    # 连接管理
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"

    # 状态同步
    AGENT_STATUS_UPDATE = "agent_status_update"
    USER_STATUS_UPDATE = "user_status_update"

    # 业务消息
    NEW_MESSAGE = "new_message"
    ESCALATION_REQUEST = "escalation_request"
    SESSION_UPDATE = "session_update"
    SESSION_TRANSFER = "session_transfer"

    # 广播
    BROADCAST_ALL = "broadcast_all"
    BROADCAST_AGENTS = "broadcast_agents"
    BROADCAST_USERS = "broadcast_users"


@dataclass
class PubSubMessage:
    """Pub/Sub 消息结构"""
    type: str
    payload: Dict[str, Any]
    source_instance: str  # 来源实例标识
    target: Optional[str] = None  # 目标客户端ID（定向发送）
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    message_id: Optional[str] = None


# ==================== Redis Pub/Sub 管理器 ====================
class RedisPubSubManager:
    """
    Redis Pub/Sub 管理器

    负责跨实例消息同步和广播
    """

    CHANNEL_AGENT = "ws:channel:agents"  # 客服频道
    CHANNEL_USER = "ws:channel:users"    # 用户频道
    CHANNEL_ALL = "ws:channel:all"       # 全局频道

    def __init__(self, instance_id: str = "default"):
        self.instance_id = instance_id
        self._pubsub: Optional[redis.client.PubSub] = None
        self._subscriber_task: Optional[asyncio.Task] = None
        self._message_handlers: Dict[str, Callable] = {}
        self._connected = False
        self._lock = asyncio.Lock()

        # 本地连接缓存（用于消息路由）
        self._local_connections: Dict[str, Any] = {}

    async def connect(self) -> bool:
        """连接 Redis Pub/Sub"""
        async with self._lock:
            if self._connected:
                return True

            try:
                # 获取 Redis 客户端
                client = await redis_client.get_client()
                if not client:
                    logger.error("Redis 客户端不可用，无法启动 Pub/Sub")
                    return False

                # 创建 PubSub 对象
                self._pubsub = client.pubsub()

                # 订阅频道
                await self._pubsub.subscribe(
                    self.CHANNEL_AGENT,
                    self.CHANNEL_USER,
                    self.CHANNEL_ALL,
                )

                # 启动消息监听任务
                self._subscriber_task = asyncio.create_task(
                    self._message_listener()
                )

                self._connected = True
                logger.info(f"Redis Pub/Sub 连接成功 (instance: {self.instance_id})")

                return True

            except Exception as e:
                logger.error(f"Redis Pub/Sub 连接失败: {e}")
                return False

    async def disconnect(self):
        """断开 Redis Pub/Sub"""
        async with self._lock:
            if not self._connected:
                return

            # 取消订阅任务
            if self._subscriber_task:
                self._subscriber_task.cancel()
                try:
                    await self._subscriber_task
                except asyncio.CancelledError:
                    pass
                self._subscriber_task = None

            # 取消订阅
            if self._pubsub:
                try:
                    await self._pubsub.unsubscribe()
                    await self._pubsub.close()
                except Exception as e:
                    logger.warning(f"关闭 Pub/Sub 失败: {e}")
                self._pubsub = None

            self._connected = False
            logger.info("Redis Pub/Sub 已断开")

    async def _message_listener(self):
        """消息监听循环"""
        while self._connected and self._pubsub:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )

                if message:
                    await self._handle_pubsub_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Pub/Sub 消息监听错误: {e}")
                # 尝试重连
                await asyncio.sleep(5)
                await self._reconnect()

    async def _reconnect(self):
        """重连 Redis Pub/Sub"""
        logger.info("尝试重新连接 Redis Pub/Sub...")
        await self.disconnect()
        await self.connect()

    async def _handle_pubsub_message(self, message: Dict):
        """处理 Pub/Sub 消息"""
        if message["type"] != "message":
            return

        channel = message["channel"]
        data = message["data"]

        try:
            # 解析消息
            if isinstance(data, bytes):
                data = data.decode("utf-8")

            msg_data = json.loads(data)
            pubsub_msg = PubSubMessage(**msg_data)

            # 跳过自己发出的消息
            if pubsub_msg.source_instance == self.instance_id:
                return

            # 处理消息
            await self._process_message(pubsub_msg, channel)

        except json.JSONDecodeError as e:
            logger.warning(f"Pub/Sub 消息解析失败: {e}")
        except Exception as e:
            logger.error(f"处理 Pub/Sub 消息失败: {e}")

    async def _process_message(self, msg: PubSubMessage, channel: str):
        """处理接收到的消息"""
        msg_type = msg.type

        # 调用注册的处理函数
        handler = self._message_handlers.get(msg_type)
        if handler:
            await handler(msg.payload, msg.source_instance)

        # 转发给本地连接的客户端
        if msg.target:
            # 定向发送
            if msg.target in self._local_connections:
                await self._send_to_local_connection(msg.target, msg)
        else:
            # 广播
            await self._broadcast_to_local(msg, channel)

    async def _send_to_local_connection(self, client_id: str, msg: PubSubMessage):
        """发送消息给本地连接"""
        connection = self._local_connections.get(client_id)
        if connection:
            try:
                await connection.send_json({
                    "type": msg.type,
                    "payload": msg.payload,
                    "timestamp": msg.timestamp,
                })
            except Exception as e:
                logger.warning(f"发送消息到本地连接失败: {e}")

    async def _broadcast_to_local(self, msg: PubSubMessage, channel: str):
        """广播到本地连接"""
        # 根据频道确定广播目标
        target_type = None
        if channel == self.CHANNEL_AGENT:
            target_type = "agent"
        elif channel == self.CHANNEL_USER:
            target_type = "user"

        # 广播到匹配的本地连接
        for client_id, connection_info in self._local_connections.items():
            if target_type and connection_info.get("type") != target_type:
                continue

            try:
                connection = connection_info.get("connection")
                if connection:
                    await connection.send_json({
                        "type": msg.type,
                        "payload": msg.payload,
                        "timestamp": msg.timestamp,
                    })
            except Exception as e:
                logger.warning(f"广播到本地连接失败 {client_id}: {e}")

    def register_handler(self, msg_type: str, handler: Callable):
        """注册消息处理器"""
        self._message_handlers[msg_type] = handler

    def unregister_handler(self, msg_type: str):
        """取消注册消息处理器"""
        self._message_handlers.pop(msg_type, None)

    # ==================== 发布消息 ====================

    async def publish_to_agents(self, msg_type: str, payload: Dict[str, Any]) -> int:
        """发布消息到客服频道"""
        return await self._publish(self.CHANNEL_AGENT, msg_type, payload)

    async def publish_to_users(self, msg_type: str, payload: Dict[str, Any]) -> int:
        """发布消息到用户频道"""
        return await self._publish(self.CHANNEL_USER, msg_type, payload)

    async def publish_to_all(self, msg_type: str, payload: Dict[str, Any]) -> int:
        """发布消息到全局频道"""
        return await self._publish(self.CHANNEL_ALL, msg_type, payload)

    async def publish_direct(self, target: str, msg_type: str, payload: Dict[str, Any]) -> int:
        """定向发布消息到特定客户端"""
        return await self._publish(self.CHANNEL_ALL, msg_type, payload, target=target)

    async def _publish(
        self,
        channel: str,
        msg_type: str,
        payload: Dict[str, Any],
        target: Optional[str] = None,
    ) -> int:
        """发布消息"""
        if not self._connected:
            logger.warning("Pub/Sub 未连接，无法发布消息")
            return 0

        try:
            client = await redis_client.get_client()
            if not client:
                return 0

            # 构建消息
            msg = PubSubMessage(
                type=msg_type,
                payload=payload,
                source_instance=self.instance_id,
                target=target,
            )

            # 发布
            message_json = json.dumps({
                "type": msg.type,
                "payload": msg.payload,
                "source_instance": msg.source_instance,
                "target": msg.target,
                "timestamp": msg.timestamp,
                "message_id": msg.message_id,
            })

            result = await client.publish(channel, message_json)
            logger.debug(f"发布消息到 {channel}: {msg_type}, 收到 {result} 个订阅者")

            return result

        except Exception as e:
            logger.error(f"发布消息失败: {e}")
            return 0

    # ==================== 本地连接管理 ====================

    def register_local_connection(
        self,
        client_id: str,
        connection: Any,
        connection_type: str = "user",  # user/agent
    ):
        """注册本地 WebSocket 连接"""
        self._local_connections[client_id] = {
            "connection": connection,
            "type": connection_type,
            "connected_at": datetime.utcnow().isoformat(),
        }
        logger.debug(f"注册本地连接: {client_id} ({connection_type})")

    def unregister_local_connection(self, client_id: str):
        """取消注册本地连接"""
        self._local_connections.pop(client_id, None)
        logger.debug(f"取消注册本地连接: {client_id}")

    def get_local_connections_count(self, connection_type: Optional[str] = None) -> int:
        """获取本地连接数量"""
        if connection_type:
            return sum(
                1 for info in self._local_connections.values()
                if info.get("type") == connection_type
            )
        return len(self._local_connections)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "instance_id": self.instance_id,
            "connected": self._connected,
            "local_connections": len(self._local_connections),
            "local_agents": self.get_local_connections_count("agent"),
            "local_users": self.get_local_connections_count("user"),
            "handlers_registered": len(self._message_handlers),
        }


# ==================== WebSocket 同步服务 ====================
class WebSocketSyncService:
    """
    WebSocket 同步服务

    整合 Redis Pub/Sub，提供完整的跨实例同步功能
    """

    def __init__(self, instance_id: str = "default"):
        self.pubsub_manager = RedisPubSubManager(instance_id)
        self._initialized = False

        # 注册默认消息处理器
        self._register_default_handlers()

    def _register_default_handlers(self):
        """注册默认消息处理器"""
        self.pubsub_manager.register_handler(
            WSMessageType.AGENT_STATUS_UPDATE,
            self._handle_agent_status_update
        )
        self.pubsub_manager.register_handler(
            WSMessageType.ESCALATION_REQUEST,
            self._handle_escalation_request
        )
        self.pubsub_manager.register_handler(
            WSMessageType.NEW_MESSAGE,
            self._handle_new_message
        )

    async def initialize(self) -> bool:
        """初始化同步服务"""
        if self._initialized:
            return True

        success = await self.pubsub_manager.connect()
        if success:
            self._initialized = True
            logger.info("WebSocket 同步服务初始化成功")

        return success

    async def shutdown(self):
        """关闭同步服务"""
        await self.pubsub_manager.disconnect()
        self._initialized = False

    async def _handle_agent_status_update(self, payload: Dict, source: str):
        """处理客服状态更新"""
        logger.info(f"收到客服状态更新 (from {source}): {payload}")
        # 更新 Redis 中客服状态
        agent_id = payload.get("agent_id")
        if agent_id:
            await redis_client.set_agent_status(
                agent_id=agent_id,
                status=payload.get("status", "offline"),
                concurrent_chats=payload.get("concurrent_chats", 0),
            )

    async def _handle_escalation_request(self, payload: Dict, source: str):
        """处理升级请求"""
        logger.info(f"收到升级请求 (from {source}): {payload}")
        # 添加到升级队列
        session_id = payload.get("session_id")
        priority_score = payload.get("priority_score", 50)
        if session_id:
            await redis_client.add_to_escalation_queue(session_id, priority_score)

    async def _handle_new_message(self, payload: Dict, source: str):
        """处理新消息"""
        logger.debug(f"收到新消息通知 (from {source}): {payload}")

    # ==================== 公共 API ====================

    async def broadcast_agent_status(
        self,
        agent_id: str,
        status: str,
        concurrent_chats: int,
    ):
        """广播客服状态变更"""
        await self.pubsub_manager.publish_to_agents(
            WSMessageType.AGENT_STATUS_UPDATE,
            {
                "agent_id": agent_id,
                "status": status,
                "concurrent_chats": concurrent_chats,
            }
        )

    async def broadcast_escalation_request(
        self,
        session_id: str,
        priority_score: float,
        priority_level: str,
        trigger_reasons: list,
    ):
        """广播升级请求"""
        await self.pubsub_manager.publish_to_agents(
            WSMessageType.ESCALATION_REQUEST,
            {
                "session_id": session_id,
                "priority_score": priority_score,
                "priority_level": priority_level,
                "trigger_reasons": trigger_reasons,
            }
        )

    async def broadcast_new_message(
        self,
        session_id: str,
        message_type: str,
        content: str,
    ):
        """广播新消息"""
        await self.pubsub_manager.publish_to_agents(
            WSMessageType.NEW_MESSAGE,
            {
                "session_id": session_id,
                "message_type": message_type,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    async def notify_user(
        self,
        user_id: str,
        msg_type: str,
        payload: Dict[str, Any],
    ):
        """通知特定用户"""
        await self.pubsub_manager.publish_direct(
            target=user_id,
            msg_type=msg_type,
            payload=payload,
        )

    def register_connection(
        self,
        client_id: str,
        connection: Any,
        is_agent: bool = False,
    ):
        """注册 WebSocket 连接"""
        connection_type = "agent" if is_agent else "user"
        self.pubsub_manager.register_local_connection(
            client_id, connection, connection_type
        )

    def unregister_connection(self, client_id: str):
        """取消注册 WebSocket 连接"""
        self.pubsub_manager.unregister_local_connection(client_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取同步服务状态"""
        return self.pubsub_manager.get_stats()


# ==================== 全局实例 ====================
_ws_sync_service: Optional[WebSocketSyncService] = None


def get_ws_sync_service(instance_id: str = "default") -> WebSocketSyncService:
    """获取 WebSocket 同步服务"""
    global _ws_sync_service

    if _ws_sync_service is None:
        _ws_sync_service = WebSocketSyncService(instance_id)

    return _ws_sync_service


async def init_ws_sync_service(instance_id: str = "default") -> WebSocketSyncService:
    """初始化 WebSocket 同步服务"""
    global _ws_sync_service

    _ws_sync_service = WebSocketSyncService(instance_id)
    await _ws_sync_service.initialize()

    return _ws_sync_service


# ==================== 导出 ====================
__all__ = [
    "WSMessageType",
    "PubSubMessage",
    "RedisPubSubManager",
    "WebSocketSyncService",
    "get_ws_sync_service",
    "init_ws_sync_service",
]