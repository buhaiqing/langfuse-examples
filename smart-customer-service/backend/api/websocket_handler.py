"""
WebSocket 服务端处理器

功能:
- WebSocket 连接管理
- 实时消息推送
- 心跳检测
- 断线重连处理
- 升级通知推送
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Optional, List, Any
from dataclasses import dataclass
import logging

from fastapi import WebSocket, WebSocketDisconnect, WebSocketState
from storage.redis_client import redis_client
from core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """WebSocket 连接"""

    websocket: WebSocket
    client_id: str
    connection_time: datetime
    last_heartbeat: datetime
    is_agent: bool = False


class WebSocketManager:
    """WebSocket 连接管理器"""

    # 最大连接数（防止 DDOS）
    MAX_CONNECTIONS = 1000

    def __init__(self):
        # 活跃的 WebSocket 连接
        self.active_connections: Dict[str, WebSocketConnection] = {}
        # 客服连接集合
        self.agent_connections: Set[str] = set()
        # 用户连接集合
        self.user_connections: Set[str] = set()
        # 心跳超时时间（秒）
        self.heartbeat_timeout = (
            settings.websocket_heartbeat_timeout
            if hasattr(settings, "websocket_heartbeat_timeout")
            else 30
        )
        # 最大无响应次数
        self.max_missed_heartbeats = 3

    async def connect(self, websocket: WebSocket, client_id: str, is_agent: bool = False) -> bool:
        """
        接受 WebSocket 连接并存储到 Redis

        Args:
            websocket: WebSocket 对象
            client_id: 客户端 ID
            is_agent: 是否为客服客户端

        Returns:
            是否连接成功
        """
        try:
            # 检查连接数限制（防止 DDOS）
            if len(self.active_connections) >= self.MAX_CONNECTIONS:
                logger.warning(f"达到最大连接数限制：{self.MAX_CONNECTIONS}")
                await websocket.close(code=1013, reason="Too many connections")
                return False

            await websocket.accept()

            connection = WebSocketConnection(
                websocket=websocket,
                client_id=client_id,
                connection_time=datetime.utcnow(),
                last_heartbeat=datetime.utcnow(),
                is_agent=is_agent,
            )

            self.active_connections[client_id] = connection

            if is_agent:
                self.agent_connections.add(client_id)
            else:
                self.user_connections.add(client_id)

            # 存储到 Redis（支持多实例同步）
            await self._save_to_redis(client_id, is_agent)

            logger.info(f"WebSocket 连接：{client_id} (客服：{is_agent})")

            # 发送欢迎消息
            await self.send_personal_message(
                websocket,
                {
                    "type": "welcome",
                    "payload": {
                        "client_id": client_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                },
            )

            return True

        except Exception as e:
            logger.error(f"WebSocket 连接失败：{e}")
            return False

    async def _save_to_redis(self, client_id: str, is_agent: bool):
        """保存连接信息到 Redis"""
        try:
            connection_data = {
                "client_id": client_id,
                "is_agent": is_agent,
                "connected_at": datetime.utcnow().isoformat(),
            }
            await redis_client.add_websocket_connection(client_id, connection_data)
        except Exception as e:
            logger.warning(f"Redis 保存失败：{e}, 继续使用内存存储")

    def disconnect(self, client_id: str):
        """断开 WebSocket 连接并从 Redis 删除"""
        if client_id in self.active_connections:
            connection = self.active_connections[client_id]

            if connection.is_agent:
                self.agent_connections.discard(client_id)
            else:
                self.user_connections.discard(client_id)

            # 从 Redis 删除
            asyncio.create_task(self._remove_from_redis(client_id))

            del self.active_connections[client_id]

            logger.info(f"WebSocket 断开：{client_id}")

    async def _remove_from_redis(self, client_id: str):
        """从 Redis 删除连接信息"""
        try:
            await redis_client.remove_websocket_connection(client_id)
        except Exception as e:
            logger.warning(f"Redis 删除失败：{e}")

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """发送个人消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败：{e}")
            raise

    async def broadcast_to_agents(self, message: dict, exclude: Optional[Set[str]] = None):
        """
        并发广播消息到所有客服（支持多实例）

        Args:
            message: 消息内容
            exclude: 排除的客服 ID 集合
        """
        exclude = exclude or set()

        # 创建并发任务
        tasks: List[asyncio.Task] = []

        # 先使用本地连接广播（快速路径）
        for client_id in self.agent_connections:
            if client_id in exclude:
                continue

            if client_id in self.active_connections:
                connection = self.active_connections[client_id]
                tasks.append(
                    asyncio.create_task(self._send_to_connection_safe(connection, message))
                )

        # 通过 Redis Pub/Sub 广播到其他实例
        try:
            await redis_client.publish_websocket_message("agent_broadcast", message)
        except Exception as e:
            logger.warning(f"Redis 广播失败：{e}")

        # 并发执行
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 记录失败
            failed_count = sum(1 for r in results if isinstance(r, Exception))
            if failed_count > 0:
                logger.warning(f"广播消息失败 {failed_count}/{len(tasks)} 个客服")

    async def send_to_user(self, user_id: str, message: dict):
        """发送消息给特定用户"""
        if user_id in self.active_connections:
            try:
                connection = self.active_connections[user_id]
                await self.send_personal_message(connection.websocket, message)
            except Exception as e:
                logger.error(f"发送消息给用户 {user_id} 失败：{e}")

    async def handle_heartbeat(self, client_id: str):
        """
        处理心跳

        Args:
            client_id: 客户端 ID
        """
        if client_id in self.active_connections:
            self.active_connections[client_id].last_heartbeat = datetime.utcnow()

    async def check_heartbeats(self):
        """检查所有连接的心跳状态"""
        current_time = datetime.utcnow()
        dead_connections = []

        for client_id, connection in self.active_connections.items():
            time_since_heartbeat = (current_time - connection.last_heartbeat).total_seconds()

            if time_since_heartbeat > self.heartbeat_timeout:
                logger.warning(f"连接超时：{client_id} ({time_since_heartbeat}s)")
                dead_connections.append(client_id)

        # 断开超时连接
        for client_id in dead_connections:
            await self.force_disconnect(client_id)

    async def force_disconnect(self, client_id: str):
        """强制断开连接"""
        if client_id in self.active_connections:
            try:
                connection = self.active_connections[client_id]
                if connection.websocket.client_state != WebSocketState.DISCONNECTED:
                    await connection.websocket.close()
            except Exception as e:
                logger.error(f"强制断开连接失败 {client_id}: {e}")

            self.disconnect(client_id)

    def get_stats(self) -> dict:
        """获取连接统计信息（包含 Redis 数据）"""
        local_stats = {
            "total_connections": len(self.active_connections),
            "agent_connections": len(self.agent_connections),
            "user_connections": len(self.user_connections),
        }

        # 尝试从 Redis 获取全局统计
        try:
            redis_stats = asyncio.get_event_loop().run_until_complete(
                redis_client.get_websocket_stats()
            )
            local_stats["redis"] = redis_stats
            local_stats["is_multi_instance"] = (
                redis_stats.get("total_connections", 0) > local_stats["total_connections"]
            )
        except Exception as e:
            logger.debug(f"获取 Redis 统计失败：{e}")

        return local_stats


# 全局 WebSocket 管理器实例
websocket_manager = WebSocketManager()


async def websocket_handler(websocket: WebSocket, client_id: str, is_agent: bool = False):
    """
    WebSocket 连接处理器

    Args:
        websocket: WebSocket 连接
        client_id: 客户端 ID
        is_agent: 是否为客服客户端
    """
    # 连接
    success = await websocket_manager.connect(websocket, client_id, is_agent)

    if not success:
        return

    # 心跳检测任务
    heartbeat_task = None

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "heartbeat":
                    # 心跳响应
                    await websocket_manager.handle_heartbeat(client_id)
                    await websocket_manager.send_personal_message(
                        websocket,
                        {"type": "heartbeat_ack", "timestamp": datetime.utcnow().isoformat()},
                    )

                elif msg_type == "status_change" and is_agent:
                    # 客服状态变更
                    # TODO: 更新 Redis 中的客服状态
                    await websocket_manager.broadcast_to_agents(
                        {
                            "type": "agent_status_updated",
                            "payload": message.get("payload", {}),
                        },
                        exclude={client_id},
                    )

                elif msg_type == "new_message":
                    # 新消息通知
                    payload = message.get("payload", {})
                    session_id = payload.get("session_id")

                    # 通知相关客服
                    # TODO: 从 Redis 获取负责该会话的客服
                    await websocket_manager.broadcast_to_agents(
                        {
                            "type": "new_message",
                            "payload": {
                                "session_id": session_id,
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        }
                    )

            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析错误：{e}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开：{client_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误 {client_id}: {e}")
    finally:
        websocket_manager.disconnect(client_id)


async def broadcast_escalation(escalation_data: dict):
    """
    广播升级通知给所有客服

    Args:
        escalation_data: 升级数据
    """
    await websocket_manager.broadcast_to_agents(
        {
            "type": "escalation_request",
            "payload": escalation_data,
        }
    )


async def notify_session_update(session_id: str, update_data: dict):
    """
    通知会话更新

    Args:
        session_id: 会话 ID
        update_data: 更新数据
    """
    # TODO: 从 Redis 获取负责的客服
    # 暂时广播给所有客服
    await websocket_manager.broadcast_to_agents(
        {
            "type": "session_update",
            "payload": {
                "session_id": session_id,
                **update_data,
            },
        }
    )


async def heartbeat_checker():
    """心跳检查后台任务"""
    while True:
        await asyncio.sleep(10)  # 每 10 秒检查一次
        await websocket_manager.check_heartbeats()


# 启动心跳检查
async def start_heartbeat_checker():
    """启动心跳检查"""
    asyncio.create_task(heartbeat_checker())
