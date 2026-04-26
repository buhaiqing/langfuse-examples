"""意图识别 API 路由"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from services.intent_recognition import intent_service

router = APIRouter(prefix="/intent", tags=["意图识别"])


class IntentRecognizeRequest(BaseModel):
    """意图识别请求"""

    user_message: str = Field(..., description="用户消息", min_length=1, max_length=500)
    session_id: str = Field(..., description="会话 ID")
    user_id: str = Field(..., description="用户 ID")
    channel: str | None = Field(default="web_chat", description="渠道")
    context: dict[str, Any] | None = Field(default=None, description="上下文信息")


class IntentRecognizeResponse(BaseModel):
    """意图识别响应"""

    success: bool
    data: dict[str, Any] | None = None
    message: str | None = None


@router.post("/recognize", response_model=IntentRecognizeResponse)
async def recognize_intent(request: IntentRecognizeRequest):
    """意图识别接口 - 识别用户消息的意图，提取槽位和实体信息"""
    try:
        result = await intent_service.recognize(
            user_message=request.user_message, context=request.context
        )

        return IntentRecognizeResponse(
            success=True,
            data={
                "intent": result.intent,
                "confidence": result.confidence,
                "slots": result.slots,
                "entities": result.entities,
            },
            message=None,
        )

    except Exception as e:
        return IntentRecognizeResponse(success=False, data=None, message=f"意图识别失败：{str(e)}")


@router.get("/intents")
async def list_intents():
    """获取所有支持的意图类型"""
    from services.intent_recognition import INTENT_DEFINITIONS

    return {
        "success": True,
        "data": {
            intent_type: {
                "description": info["description"],
                "required_slots": info["required_slots"],
                "optional_slots": info["optional_slots"],
                "example": info["example"],
            }
            for intent_type, info in INTENT_DEFINITIONS.items()
        },
    }
