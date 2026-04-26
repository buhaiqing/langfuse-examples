"""
WebSocket 服务端处理器

功能:
- WebSocket 连接管理
- 实时消息推送
- 心跳检测
- 断线重连处理
- 升级通知推送

性能优化:
- 使用 asyncio.Lock 保证线程安全
- 广播采用 fire-and-forget 模式
- 连接数监控和限流
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.config import settings
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from storage.redis_client import redis_client
from utils import utcnow

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """WebSocket 连接"""

    websocket: WebSocket
    client_id: str
    connection_time: datetime
    last_heartbeat: datetime
    is_agent: bool = False
    message_count: int = field(default=0)  # 消息计数
    bytes_sent: int = field(default=0)  # 发送字节数


@dataclass
class ConnectionMetrics:
    """连接指标"""

    total_connections: int = 0
    total_messages: int = 0
    total_bytes: int = 0
    peak_connections: int = 0
    connection_errors: int = 0
    broadcast_errors: int = 0


class WebSocketManager:
    """WebSocket 连接管理器 - 线程安全优化版"""

    # 最大连接数（防止 DDOS）
    MAX_CONNECTIONS = 1000
    # 最大广播并发数
    MAX_BROADCAST_CONCURRENCY = 50

    def __init__(self):
        # 活跃的 WebSocket 连接
        self.active_connections: dict[str, WebSocketConnection] = {}
        # 客服连接集合
        self.agent_connections: set[str] = set()
        # 用户连接集合
        self.user_connections: set[str] = set()
        # 心跳超时时间（秒）
        self.heartbeat_timeout = (
            settings.websocket_heartbeat_timeout
            if hasattr(settings, "websocket_heartbeat_timeout")
            else 30
        )
        # 最大无响应次数
        self.max_missed_heartbeats = 3

        # 线程安全锁
        self._connections_lock = asyncio.Lock()
        self._agents_lock = asyncio.Lock()
        self._users_lock = asyncio.Lock()

        # 性能指标
        self.metrics = ConnectionMetrics()

        # 广播信号量（限制并发）
        self._broadcast_semaphore = asyncio.Semaphore(self.MAX_BROADCAST_CONCURRENCY)

    async def connect(self, websocket: WebSocket, client_id: str, is_agent: bool = False) -> bool:
        """
        接受 WebSocket 连接 - 线程安全版本

        Args:
            websocket: WebSocket 对象
            client_id: 客户端 ID
            is_agent: 是否为客服客户端

        Returns:
            是否连接成功
        """
        try:
            # 检查连接数限制（防止 DDOS）- 使用锁保护
            async with self._connections_lock:
                if len(self.active_connections) >= self.MAX_CONNECTIONS:
                    logger.warning(f"达到最大连接数限制：{self.MAX_CONNECTIONS}")
                    await websocket.close(code=1013, reason="Too many connections")
                    return False

            await websocket.accept()

            connection = WebSocketConnection(
                websocket=websocket,
                client_id=client_id,
                connection_time=utcnow(),
                last_heartbeat=utcnow(),
                is_agent=is_agent,
            )

            # 使用锁保护共享状态
            async with self._connections_lock:
                self.active_connections[client_id] = connection

            if is_agent:
                async with self._agents_lock:
                    self.agent_connections.add(client_id)
            else:
                async with self._users_lock:
                    self.user_connections.add(client_id)

            # 更新指标
            self.metrics.total_connections += 1
            current_count = len(self.active_connections)
            if current_count > self.metrics.peak_connections:
                self.metrics.peak_connections = current_count

            # 存储到 Redis（支持多实例同步）- 非阻塞
            asyncio.create_task(self._save_to_redis(client_id, is_agent))

            logger.info(
                f"WebSocket 连接：{client_id} (客服：{is_agent}, 当前连接数：{current_count})"
            )

            # 发送欢迎消息
            await self.send_personal_message(
                websocket,
                {
                    "type": "welcome",
                    "payload": {
                        "client_id": client_id,
                        "timestamp": utcnow().isoformat(),
                        "connections_count": current_count,
                    },
                },
            )

            return True

        except Exception as e:
            logger.error(f"WebSocket 连接失败：{e}")
            self.metrics.connection_errors += 1
            return False

    async def _save_to_redis(self, client_id: str, is_agent: bool):
        """保存连接信息到 Redis"""
        try:
            connection_data = {
                "client_id": client_id,
                "is_agent": is_agent,
                "connected_at": utcnow().isoformat(),
            }
            await redis_client.add_websocket_connection(client_id, connection_data)
        except Exception as e:
            logger.warning(f"Redis 保存失败：{e}, 继续使用内存存储")

    async def disconnect(self, client_id: str):
        """断开 WebSocket 连接 - 线程安全版本"""
        async with self._connections_lock:
            if client_id not in self.active_connections:
                return

            connection = self.active_connections[client_id]

            # 从集合中移除
            if connection.is_agent:
                async with self._agents_lock:
                    self.agent_connections.discard(client_id)
            else:
                async with self._users_lock:
                    self.user_connections.discard(client_id)

            del self.active_connections[client_id]

        # 从 Redis 删除 - 非阻塞
        asyncio.create_task(self._remove_from_redis(client_id))

        logger.info(f"WebSocket 断开：{client_id} (剩余连接数：{len(self.active_connections)})")

    async def _remove_from_redis(self, client_id: str):
        """从 Redis 删除连接信息"""
        try:
            await redis_client.remove_websocket_connection(client_id)
        except Exception as e:
            logger.warning(f"Redis 删除失败：{e}")

    async def send_personal_message(self, websocket: WebSocket, message: dict) -> bool:
        """发送个人消息"""
        try:
            message_json = json.dumps(message, ensure_ascii=False)
            await websocket.send_text(message_json)

            # 更新指标
            self.metrics.total_messages += 1
            self.metrics.total_bytes += len(message_json.encode("utf-8"))

            return True
        except Exception as e:
            logger.error(f"发送消息失败：{e}")
            return False

    async def _send_to_connection_safe(
        self, connection: WebSocketConnection, message: dict
    ) -> bool:
        """安全地发送消息到单个连接"""
        try:
            async with self._broadcast_semaphore:
                success = await self.send_personal_message(connection.websocket, message)
                if success:
                    connection.message_count += 1
                return success
        except Exception as e:
            logger.warning(f"发送消息到 {connection.client_id} 失败：{e}")
            return False

    async def broadcast_to_agents(
        self, message: dict, exclude: set[str] | None = None
    ) -> dict[str, Any]:
        """
        广播消息到所有客服 - fire-and-forget 优化版本

        采用不等待全部完成的策略，超时后自动放弃，避免单点阻塞

        Args:
            message: 消息内容
            exclude: 排除的客服 ID 集合

        Returns:
            广播统计信息
        """
        exclude = exclude or set()
        start_time = time.time()

        # 获取当前在线客服列表（快照）
        async with self._agents_lock:
            current_agents = self.agent_connections.copy()

        # 创建发送任务
        tasks = []
        target_agents = []

        async with self._connections_lock:
            for client_id in current_agents:
                if client_id in exclude:
                    continue
                if client_id in self.active_connections:
                    connection = self.active_connections[client_id]
                    task = asyncio.create_task(
                        self._send_to_connection_safe(connection, message),
                        name=f"broadcast_{client_id}",
                    )
                    tasks.append(task)
                    target_agents.append(client_id)

        # 通过 Redis Pub/Sub 广播到其他实例 - 非阻塞
        asyncio.create_task(self._publish_to_redis(message))

        # 等待结果，但设置超时（避免阻塞）
        results = []
        if tasks:
            try:
                # 最多等待 2 秒
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), timeout=2.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"广播超时，取消剩余 {len(tasks) - len(results)} 个任务")
                # 取消未完成的任务
                for task in tasks[len(results) :]:
                    task.cancel()

        # 统计结果
        success_count = sum(1 for r in results if r is True)
        failed_count = len(results) - success_count
        error_count = sum(1 for r in results if isinstance(r, Exception))

        duration = time.time() - start_time

        if failed_count > 0 or error_count > 0:
            logger.warning(
                f"广播完成：成功 {success_count}/{len(tasks)}, "
                f"失败 {failed_count}, 错误 {error_count}, 耗时 {duration:.3f}s"
            )
            self.metrics.broadcast_errors += error_count

        return {
            "total_targets": len(tasks),
            "success_count": success_count,
            "failed_count": failed_count,
            "error_count": error_count,
            "duration_ms": round(duration * 1000, 2),
        }

    async def _publish_to_redis(self, message: dict):
        """发布消息到 Redis（跨实例广播）"""
        try:
            await redis_client.publish_websocket_message("agent_broadcast", message)
        except Exception as e:
            logger.warning(f"Redis 广播失败：{e}")

    async def send_to_user(self, user_id: str, message: dict) -> bool:
        """发送消息给特定用户"""
        async with self._connections_lock:
            if user_id not in self.active_connections:
                return False
            connection = self.active_connections[user_id]
            return await self.send_personal_message(connection.websocket, message)

    async def handle_heartbeat(self, client_id: str) -> bool:
        """处理心跳"""
        async with self._connections_lock:
            if client_id in self.active_connections:
                self.active_connections[client_id].last_heartbeat = utcnow()
                return True
        return False

    async def check_heartbeats(self) -> int:
        """检查所有连接的心跳状态 - 返回断开的连接数"""
        current_time = utcnow()
        dead_connections = []

        async with self._connections_lock:
            connections_snapshot = list(self.active_connections.items())

        for client_id, connection in connections_snapshot:
            time_since_heartbeat = (current_time - connection.last_heartbeat).total_seconds()

            if time_since_heartbeat > self.heartbeat_timeout:
                logger.warning(f"连接超时：{client_id} ({time_since_heartbeat:.1f}s)")
                dead_connections.append(client_id)

        # 断开超时连接
        disconnected_count = 0
        for client_id in dead_connections:
            await self.force_disconnect(client_id)
            disconnected_count += 1

        if disconnected_count > 0:
            logger.info(f"心跳检查：断开 {disconnected_count} 个超时连接")

        return disconnected_count

    async def force_disconnect(self, client_id: str) -> bool:
        """强制断开连接"""
        try:
            async with self._connections_lock:
                if client_id not in self.active_connections:
                    return False
                connection = self.active_connections[client_id]
                if connection.websocket.client_state != WebSocketState.DISCONNECTED:
                    await connection.websocket.close()
        except Exception as e:
            logger.error(f"强制断开连接失败 {client_id}: {e}")

        await self.disconnect(client_id)
        return True

    async def get_stats(self) -> dict:
        """获取连接统计信息（包含性能指标）"""
        async with self._connections_lock:
            total = len(self.active_connections)
        async with self._agents_lock:
            agents = len(self.agent_connections)
        async with self._users_lock:
            users = len(self.user_connections)

        return {
            "total_connections": total,
            "agent_connections": agents,
            "user_connections": users,
            "peak_connections": self.metrics.peak_connections,
            "total_messages": self.metrics.total_messages,
            "total_bytes": self.metrics.total_bytes,
            "connection_errors": self.metrics.connection_errors,
            "broadcast_errors": self.metrics.broadcast_errors,
            "uptime_seconds": (
                utcnow()
                - datetime.fromtimestamp(getattr(self, "_start_time", utcnow().timestamp()))
            ).total_seconds(),
        }

    def reset_metrics(self):
        """重置指标"""
        self.metrics = ConnectionMetrics()


# 全局 WebSocket 管理器实例
websocket_manager = WebSocketManager()
websocket_manager._start_time = utcnow().timestamp()


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
                        {"type": "heartbeat_ack", "timestamp": utcnow().isoformat()},
                    )

                elif msg_type == "status_change" and is_agent:
                    # 客服状态变更
                    asyncio.create_task(
                        websocket_manager.broadcast_to_agents(
                            {
                                "type": "agent_status_updated",
                                "payload": {
                                    "agent_id": client_id,
                                    **message.get("payload", {}),
                                },
                            },
                            exclude={client_id},
                        )
                    )

                elif msg_type == "new_message":
                    # 新消息通知 - 异步广播
                    payload = message.get("payload", {})
                    session_id = payload.get("session_id")

                    asyncio.create_task(
                        websocket_manager.broadcast_to_agents(
                            {
                                "type": "new_message",
                                "payload": {
                                    "session_id": session_id,
                                    "timestamp": utcnow().isoformat(),
                                },
                            }
                        )
                    )

            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析错误：{e}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开：{client_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误 {client_id}: {e}")
    finally:
        await websocket_manager.disconnect(client_id)


async def broadcast_escalation(escalation_data: dict) -> dict[str, Any]:
    """
    广播升级通知给所有客服

    Args:
        escalation_data: 升级数据

    Returns:
        广播统计
    """
    return await websocket_manager.broadcast_to_agents(
        {
            "type": "escalation_request",
            "payload": escalation_data,
        }
    )


async def notify_session_update(session_id: str, update_data: dict) -> dict[str, Any]:
    """
    通知会话更新

    Args:
        session_id: 会话 ID
        update_data: 更新数据

    Returns:
        广播统计
    """
    return await websocket_manager.broadcast_to_agents(
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
        disconnected = await websocket_manager.check_heartbeats()
        if disconnected > 0:
            logger.debug(f"心跳检查断开 {disconnected} 个连接")


# 启动心跳检查
async def start_heartbeat_checker():
    """启动心跳检查"""
    asyncio.create_task(heartbeat_checker())
