from typing import Optional

from api.schemas import (
    ApiResponse,
    Conversation,
    ConversationListItem,
    MessageRole,
    SendMessageRequest,
    SendMessageResponse,
    ResolveConversationRequest,
)
from api.session_store import session_store


def get_conversation_list() -> ApiResponse:
    try:
        conversations = session_store.get_conversation_list()
        return ApiResponse(
            success=True,
            data={"conversations": [conv.model_dump() for conv in conversations]},
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


def get_conversation(conversation_id: str) -> ApiResponse:
    try:
        conversation = session_store.get_conversation(conversation_id)
        if not conversation:
            return ApiResponse(success=False, error="会话不存在")
        return ApiResponse(
            success=True,
            data={"conversation": conversation.model_dump()},
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


def send_message(request: SendMessageRequest, agent_id: Optional[str] = None) -> SendMessageResponse:
    try:
        message = session_store.add_message(
            conversation_id=request.conversation_id,
            content=request.content,
            role=MessageRole.AGENT,
            agent_id=agent_id or request.agent_id or "agent-1",
        )
        if not message:
            return SendMessageResponse(success=False, error="会话不存在")
        return SendMessageResponse(success=True, message_id=message.id)
    except Exception as e:
        return SendMessageResponse(success=False, error=str(e))


def resolve_conversation(request: ResolveConversationRequest) -> ApiResponse:
    try:
        success = session_store.resolve_conversation(
            conversation_id=request.conversation_id,
            resolution_notes=request.resolution_notes,
        )
        if not success:
            return ApiResponse(success=False, error="会话不存在")
        return ApiResponse(success=True)
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


def create_conversation_from_webhook(payload: dict) -> ApiResponse:
    try:
        from api.schemas import EscalationReason, Priority

        conversation = session_store.create_conversation(
            user_id=payload.get("session_id", "unknown"),
            user_name=payload.get("user_name"),
            user_email=payload.get("user_email"),
            initial_message=payload.get("initial_message"),
            escalated_reason=EscalationReason(payload.get("reason", "USER_REQUESTED_HUMAN")),
            priority=Priority(payload.get("priority", "medium")),
        )
        return ApiResponse(
            success=True,
            data={"conversation": conversation.model_dump()},
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))
