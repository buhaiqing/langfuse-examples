"""升级管理 API 路由"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from services.escalation_service import escalation_service
from storage.redis_client import redis_client


router = APIRouter(prefix="/escalations", tags=["升级管理"])


class EscalationCheckRequest(BaseModel):
    """升级检查请求"""

    session_id: str
    user_id: str
    intent_confidence: float
    user_message: str
    failure_count: int = 0
    is_vip: bool = False


class EscalationCheckResponse(BaseModel):
    """升级检查响应"""

    success: bool
    requires_escalation: bool
    priority_level: Optional[str] = None
    trigger_reasons: Optional[List[str]] = None


@router.post("/check", response_model=Dict[str, Any])
async def check_escalation(request: EscalationCheckRequest):
    """检查是否需要升级"""
    needs_escalation = await escalation_service.check_escalation(
        session_id=request.session_id,
        user_id=request.user_id,
        intent_confidence=request.intent_confidence,
        user_message=request.user_message,
        failure_count=request.failure_count,
        is_vip=request.is_vip,
    )

    return {
        "success": True,
        "requires_escalation": needs_escalation,
    }


@router.get("/queue", response_model=Dict[str, Any])
async def get_escalation_queue():
    """获取升级队列"""
    size = await redis_client.get_escalation_queue_size()

    return {
        "success": True,
        "data": {
            "queue_size": size,
            "pending_count": size,
        },
    }


@router.post("/queue/next", response_model=Dict[str, Any])
async def get_next_escalation():
    """获取下一个升级会话"""
    next_session = await redis_client.get_next_escalation()

    if not next_session:
        return {"success": False, "message": "队列为空"}

    return {
        "success": True,
        "data": {
            "session_id": next_session,
            "priority": "high",
        },
    }
