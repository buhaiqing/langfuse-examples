"""会话管理 API 路由"""

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from storage.redis_client import ConversationState as RedisConversationState
from storage.redis_client import redis_client
from utils import utcnow

router = APIRouter(prefix="/conversations", tags=["会话管理"])


class ConversationStateResponse(BaseModel):
    """会话状态响应"""

    session_id: str
    user_id: str
    created_at: str
    updated_at: str
    current_intent: str | None = None
    collected_slots: dict[str, Any] = {}
    turn_count: int = 0


class AddMessageRequest(BaseModel):
    """添加消息请求"""

    role: str = Field(..., description="消息角色 (user/assistant)")
    content: str = Field(..., description="消息内容")
    intent: str | None = None
    confidence: float | None = None


class CreateConversationRequest(BaseModel):
    """创建会话请求"""

    session_id: str = Field(..., description="会话 ID")
    user_id: str = Field(..., description="用户 ID")
    initial_slots: dict[str, Any] | None = None


class ConversationResponse(BaseModel):
    """通用会话响应"""

    success: bool
    data: Any | None = None
    message: str | None = None


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(request: CreateConversationRequest):
    """创建新会话"""
    try:
        existing = await redis_client.get_session_state(request.session_id)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"会话 {request.session_id} 已存在",
            )

        state = RedisConversationState(
            session_id=request.session_id,
            user_id=request.user_id,
            collected_slots=request.initial_slots or {},
        )
        await redis_client.save_session_state(state)

        return ConversationResponse(
            success=True,
            data=ConversationStateResponse(
                session_id=state.session_id,
                user_id=state.user_id,
                created_at=state.created_at,
                updated_at=state.updated_at,
                current_intent=state.current_intent,
                collected_slots=state.collected_slots,
                turn_count=state.turn_count,
            ).model_dump(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"创建会话失败：{str(e)}",
        ) from e


@router.get("/{session_id}", response_model=ConversationResponse)
async def get_conversation(session_id: str):
    """获取会话状态"""
    try:
        state = await redis_client.get_session_state(session_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"会话 {session_id} 不存在",
            )

        return ConversationResponse(
            success=True,
            data=ConversationStateResponse(
                session_id=state.session_id,
                user_id=state.user_id,
                created_at=state.created_at,
                updated_at=state.updated_at,
                current_intent=state.current_intent,
                collected_slots=state.collected_slots,
                turn_count=state.turn_count,
            ).model_dump(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取会话失败：{str(e)}",
        ) from e


@router.get("/{session_id}/history", response_model=ConversationResponse)
async def get_conversation_history(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=200),
):
    """获取会话消息历史"""
    try:
        state = await redis_client.get_session_state(session_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"会话 {session_id} 不存在",
            )

        messages = await redis_client.get_session_history(session_id, limit=limit)
        return ConversationResponse(
            success=True,
            data={
                "session_id": session_id,
                "messages": messages,
                "total": len(messages),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取会话历史失败：{str(e)}",
        ) from e


@router.post("/{session_id}/messages", response_model=ConversationResponse)
async def add_message(session_id: str, request: AddMessageRequest):
    """添加消息到会话"""
    try:
        state = await redis_client.get_session_state(session_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"会话 {session_id} 不存在",
            )

        metadata = {}
        if request.intent:
            metadata["intent"] = request.intent
        if request.confidence is not None:
            metadata["confidence"] = request.confidence

        await redis_client.add_message_to_history(
            session_id=session_id,
            role=request.role,
            content=request.content,
            metadata=metadata if metadata else None,
        )

        state.turn_count += 1
        if request.intent:
            state.current_intent = request.intent
        state.updated_at = utcnow().isoformat()
        await redis_client.save_session_state(state)

        return ConversationResponse(
            success=True,
            data={
                "session_id": session_id,
                "turn_count": state.turn_count,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"添加消息失败：{str(e)}",
        ) from e


@router.delete("/{session_id}", response_model=ConversationResponse)
async def delete_conversation(session_id: str):
    """删除会话"""
    try:
        state = await redis_client.get_session_state(session_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"会话 {session_id} 不存在",
            )

        await redis_client.delete_session_state(session_id)
        await redis_client.clear_session_history(session_id)

        return ConversationResponse(
            success=True,
            data=None,
            message="会话已删除",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除会话失败：{str(e)}",
        ) from e


@router.get("", response_model=ConversationResponse)
async def list_conversations(
    user_id: str | None = Query(default=None, description="按用户 ID 过滤"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """获取会话列表

    注意：Redis 不支持高效分页查询，此接口仅用于管理目的。
    生产环境建议使用 PostgreSQL 进行会话持久化查询。
    """
    try:
        client = await redis_client.get_client()
        if not client:
            raise HTTPException(status_code=503, detail="Redis 连接不可用")

        pattern = "session:*:state"
        keys = []
        async for key in client.scan_iter(match=pattern, count=100):
            keys.append(key)

        total = len(keys)
        paginated_keys = keys[offset : offset + limit]

        conversations = []
        for key in paginated_keys:
            data = await client.get(key)
            if data:
                state_dict = json.loads(data)
                if user_id and state_dict.get("user_id") != user_id:
                    continue
                conversations.append(
                    ConversationStateResponse(
                        session_id=state_dict.get("session_id", ""),
                        user_id=state_dict.get("user_id", ""),
                        created_at=state_dict.get("created_at", ""),
                        updated_at=state_dict.get("updated_at", ""),
                        current_intent=state_dict.get("current_intent"),
                        collected_slots=state_dict.get("collected_slots", {}),
                        turn_count=state_dict.get("turn_count", 0),
                    ).model_dump()
                )

        return ConversationResponse(
            success=True,
            data={
                "total": total,
                "limit": limit,
                "offset": offset,
                "conversations": conversations,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取会话列表失败：{str(e)}",
        ) from e
