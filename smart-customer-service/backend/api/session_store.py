import uuid
from datetime import datetime
from typing import Optional

from api.schemas import (
    AssignedAgent,
    Conversation,
    ConversationContext,
    ConversationListItem,
    ConversationStatus,
    EscalationReason,
    Message,
    MessageRole,
    Priority,
)


class SessionStore:
    def __init__(self):
        self._conversations: dict[str, Conversation] = {}
        self._setup_sample_data()

    def _setup_sample_data(self):
        reasons = [
            EscalationReason.USER_REQUESTED_HUMAN,
            EscalationReason.LOW_CONFIDENCE,
            EscalationReason.COMPLEX_ISSUE,
            EscalationReason.SENTIMENT_NEGATIVE,
        ]
        names = ["张三", "李四", "王五", "赵六", "钱七"]
        previews = [
            "我的账户登录不了了，帮我看看",
            "API调用一直返回403错误怎么处理",
            "账单金额不对，请核实",
            "产品功能如何使用",
            "密码重置后还是登录失败",
        ]

        for i in range(12):
            status = (
                ConversationStatus.PENDING
                if i < 8
                else ConversationStatus.ACTIVE
                if i < 10
                else ConversationStatus.RESOLVED
            )
            priority = (
                Priority.URGENT
                if i < 3
                else Priority.HIGH
                if i < 6
                else Priority.MEDIUM
                if i < 9
                else Priority.LOW
            )
            conv_id = f"conv-{i + 1}"
            session_id = f"session-{1000 + i}"
            created_at = datetime.now()
            escalated_at = datetime.now()

            messages = [
                Message(
                    id="msg-1",
                    role=MessageRole.USER,
                    content="你好，我的API调用一直返回403错误，能帮我看看吗？",
                    timestamp=escalated_at,
                    metadata={"intent": "api_error_troubleshooting", "confidence": 0.85},
                ),
                Message(
                    id="msg-2",
                    role=MessageRole.ASSISTANT,
                    content="您好！我是智能客服助手。让我帮您查看这个问题。请问您调用的是哪个API端点？",
                    timestamp=escalated_at,
                    metadata={"intent": "api_error_troubleshooting", "confidence": 0.92},
                ),
                Message(
                    id="msg-3",
                    role=MessageRole.USER,
                    content="/api/v1/users 端点，显示无权访问",
                    timestamp=escalated_at,
                ),
                Message(
                    id="msg-4",
                    role=MessageRole.ASSISTANT,
                    content="403错误通常是由于权限问题导致的。让我帮您检查一下：\n\n1. 您的API密钥是否有访问该端点的权限？\n2. 您的账户是否已升级到支持该功能的版本？\n\n您方便提供一下您的API密钥前缀吗？",
                    timestamp=escalated_at,
                    metadata={"intent": "api_error_troubleshooting", "confidence": 0.88},
                ),
            ]

            conversation = Conversation(
                id=conv_id,
                session_id=session_id,
                user_id=f"user-{i + 1}",
                user_name=names[i % len(names)],
                user_email=f"user{i + 1}@example.com",
                status=status,
                priority=priority,
                created_at=created_at,
                updated_at=escalated_at,
                escalated_at=escalated_at,
                escalated_reason=reasons[i % len(reasons)],
                escalated_reason_description="用户请求转人工客服处理",
                messages=messages,
                context=ConversationContext(
                    total_turns=4,
                    ai_resolution_attempts=2,
                    last_intent="api_error_troubleshooting",
                    last_confidence=0.45,
                ),
                assigned_agent=AssignedAgent(id="agent-1", name="客服小王")
                if status != ConversationStatus.PENDING
                else None,
            )
            self._conversations[conv_id] = conversation

    def get_conversation_list(self) -> list[ConversationListItem]:
        result = []
        for conv in self._conversations.values():
            preview = ""
            if conv.messages:
                preview = conv.messages[-1].content[:50]
            result.append(
                ConversationListItem(
                    id=conv.id,
                    session_id=conv.session_id,
                    user_name=conv.user_name or conv.user_id,
                    status=conv.status,
                    priority=conv.priority,
                    preview=preview,
                    created_at=conv.created_at,
                    escalated_reason=conv.escalated_reason,
                )
            )
        result.sort(key=lambda x: x.created_at, reverse=True)
        return result

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return self._conversations.get(conversation_id)

    def add_message(
        self, conversation_id: str, content: str, role: MessageRole, agent_id: Optional[str] = None
    ) -> Optional[Message]:
        conv = self._conversations.get(conversation_id)
        if not conv:
            return None

        message = Message(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            role=role,
            content=content,
            timestamp=datetime.now(),
        )
        conv.messages.append(message)
        conv.updated_at = datetime.now()

        if role == MessageRole.AGENT:
            conv.status = ConversationStatus.ACTIVE
            if agent_id:
                conv.assigned_agent = AssignedAgent(id=agent_id, name=f"客服-{agent_id}")

        return message

    def resolve_conversation(
        self, conversation_id: str, resolution_notes: Optional[str] = None
    ) -> bool:
        conv = self._conversations.get(conversation_id)
        if not conv:
            return False

        conv.status = ConversationStatus.RESOLVED
        conv.resolved_at = datetime.now()
        conv.updated_at = datetime.now()

        if resolution_notes:
            self.add_message(
                conversation_id,
                f"会话已解决: {resolution_notes}",
                MessageRole.SYSTEM,
            )

        return True

    def create_conversation(
        self,
        user_id: str,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        initial_message: Optional[str] = None,
        escalated_reason: EscalationReason = EscalationReason.USER_REQUESTED_HUMAN,
        priority: Priority = Priority.MEDIUM,
    ) -> Conversation:
        conv_id = f"conv-{uuid.uuid4().hex[:8]}"
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        now = datetime.now()

        messages = []
        if initial_message:
            messages.append(
                Message(
                    id=f"msg-{uuid.uuid4().hex[:8]}",
                    role=MessageRole.USER,
                    content=initial_message,
                    timestamp=now,
                )
            )

        conversation = Conversation(
            id=conv_id,
            session_id=session_id,
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            status=ConversationStatus.PENDING,
            priority=priority,
            created_at=now,
            updated_at=now,
            escalated_at=now,
            escalated_reason=escalated_reason,
            escalated_reason_description="新会话",
            messages=messages,
            context=ConversationContext(total_turns=1),
        )
        self._conversations[conv_id] = conversation
        return conversation


session_store = SessionStore()
