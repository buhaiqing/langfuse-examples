from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    AGENT = "agent"
    SYSTEM = "system"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


class EscalationReason(str, Enum):
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"
    USER_REQUESTED_HUMAN = "USER_REQUESTED_HUMAN"
    COMPLEX_ISSUE = "COMPLEX_ISSUE"
    SENTIMENT_NEGATIVE = "SENTIMENT_NEGATIVE"
    REPEATED_FAILURE = "REPEATED_FAILURE"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Message(BaseModel):
    id: str
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Optional[dict] = None


class ConversationContext(BaseModel):
    total_turns: int = 0
    ai_resolution_attempts: int = 0
    last_intent: Optional[str] = None
    last_confidence: Optional[float] = None


class AssignedAgent(BaseModel):
    id: str
    name: str


class Conversation(BaseModel):
    id: str
    session_id: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    status: ConversationStatus
    priority: Priority
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    escalated_at: datetime
    escalated_reason: EscalationReason
    escalated_reason_description: Optional[str] = None
    messages: list[Message] = []
    context: Optional[ConversationContext] = None
    assigned_agent: Optional[AssignedAgent] = None


class ConversationListItem(BaseModel):
    id: str
    session_id: str
    user_name: str
    status: ConversationStatus
    priority: Priority
    preview: str
    created_at: datetime
    escalated_reason: EscalationReason


class SendMessageRequest(BaseModel):
    conversation_id: str
    content: str
    agent_id: Optional[str] = None


class SendMessageResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class ResolveConversationRequest(BaseModel):
    conversation_id: str
    resolution_notes: Optional[str] = None


class ApiResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
