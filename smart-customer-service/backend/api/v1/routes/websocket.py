"""
WebSocket API 路由

提供 WebSocket 连接端点和相关 HTTP 接口
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import Optional
import logging
import jwt

from api.websocket_handler import websocket_handler, websocket_manager, start_heartbeat_checker
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


async def verify_websocket_token(token: str) -> dict:
    """
    验证 WebSocket 连接的 JWT Token

    Args:
        token: JWT Token

    Returns:
        dict: Token payload

    Raises:
        HTTPException: Token 无效或已过期
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


@router.websocket("/ws/agent")
async def agent_websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT Token 用于身份验证"),
    client_id: str = Query(..., description="客服客户端 ID")
):
    """
    客服 WebSocket 连接端点

    连接 URL: ws://localhost:8000/ws/agent?token=<jwt>&client_id=agent_001

    Args:
        token: JWT Token（必需）
        client_id: 客服客户端 ID（必需）
    """
    is_agent = True

    try:
        # 验证 JWT Token
        payload = await verify_websocket_token(token)

        # 检查是否有客服权限
        scopes = payload.get("scopes", [])
        if "agent" not in scopes:
            await websocket.close(code=1008, reason="Insufficient permissions: agent scope required")
            return

        await websocket_handler(websocket, client_id, is_agent)
    except HTTPException as e:
        logger.warning(f"WebSocket 鉴权失败: {e.detail}")
        await websocket.close(code=1008, reason=str(e.detail))
    except Exception as e:
        logger.error(f"WebSocket 连接错误: {e}")
        await websocket.close(code=1011, reason="Internal server error")


@router.websocket("/ws/user")
async def user_websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT Token 用于身份验证"),
    client_id: str = Query(..., description="用户客户端 ID")
):
    """
    用户 WebSocket 连接端点

    连接 URL: ws://localhost:8000/ws/user?token=<jwt>&client_id=user_123

    Args:
        token: JWT Token（必需）
        client_id: 用户客户端 ID（必需）
    """
    is_agent = False

    try:
        # 验证 JWT Token
        await verify_websocket_token(token)

        await websocket_handler(websocket, client_id, is_agent)
    except HTTPException as e:
        logger.warning(f"WebSocket 鉴权失败: {e.detail}")
        await websocket.close(code=1008, reason=str(e.detail))
    except Exception as e:
        logger.error(f"WebSocket 连接错误: {e}")
        await websocket.close(code=1011, reason="Internal server error")


@router.get("/ws/stats")
async def get_websocket_stats():
    """
    获取 WebSocket 连接统计

    返回:
    - total_connections: 总连接数
    - agent_connections: 客服连接数
    - user_connections: 用户连接数
    """
    stats = websocket_manager.get_stats()

    return {
        "success": True,
        "data": stats,
    }


@router.websocket("/ws/session/{session_id}")
async def session_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(..., description="JWT Token 用于身份验证")
):
    """
    会话专用 WebSocket 端点

    用于特定会话的实时通信

    Args:
        session_id: 会话 ID
        token: JWT Token（必需）
    """
    client_id = f"session:{session_id}"

    try:
        # 验证 JWT Token
        await verify_websocket_token(token)

        await websocket.accept()

        # 加入会话频道
        # TODO: 实现频道管理

        await websocket.send_json(
            {
                "type": "joined_session",
                "payload": {
                    "session_id": session_id,
                },
            }
        )

        while True:
            data = await websocket.receive_text()
            # 转发到会话相关方
            # TODO: 实现消息转发

    except HTTPException as e:
        logger.warning(f"会话 WebSocket 鉴权失败: {e.detail}")
        await websocket.close(code=1008, reason=str(e.detail))
    except WebSocketDisconnect:
        logger.info(f"会话 WebSocket 断开：{session_id}")
    except Exception as e:
        logger.error(f"会话 WebSocket 错误 {session_id}: {e}")


@router.on_event("startup")
async def startup_websocket():
    """应用启动时启动心跳检查"""
    await start_heartbeat_checker()
