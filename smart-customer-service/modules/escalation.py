"""
Escalation management module with Langfuse tracing
Handles fallback responses and human agent handoff
"""

import time
from dataclasses import dataclass
from enum import Enum

from core.scoring import score_escalation_required
from core.tracing import add_event, create_span
from modules.dialogue_manager import ConversationState
from modules.intent_recognition import IntentResult


class EscalationReason(str, Enum):
    """Reasons for escalating to human agent"""

    LOW_CONFIDENCE = "low_confidence"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    USER_REQUESTED_HUMAN = "user_requested_human"
    COMPLEX_ISSUE = "complex_issue"
    SENTIMENT_NEGATIVE = "sentiment_negative"
    REPEATED_FAILURE = "repeated_failure"


@dataclass
class EscalationDecision:
    """Decision about whether to escalate"""

    should_escalate: bool
    reason: EscalationReason | None = None
    confidence_score: float = 0.0
    suggested_action: str = ""


class EscalationManager:
    """Manages escalation decisions with Langfuse tracing"""

    def __init__(
        self,
        confidence_threshold: float = 0.6,
        max_retry_count: int = 3,
        sentiment_threshold: float = -0.7,
    ):
        self.confidence_threshold = confidence_threshold
        self.max_retry_count = max_retry_count
        self.sentiment_threshold = sentiment_threshold

        # Fallback response templates
        self.fallback_templates = {
            EscalationReason.LOW_CONFIDENCE: "抱歉，我可能没有完全理解您的问题。能否请您换一种方式描述，或者提供更多细节？",
            EscalationReason.MAX_RETRIES_EXCEEDED: "看来这个问题比较复杂，我已经尝试了几种方法但未能解决。我为您转接人工客服以获取更专业的帮助。",
            EscalationReason.USER_REQUESTED_HUMAN: "好的，我立即为您转接人工客服，请稍候。预计等待时间约为2-3分钟。",
            EscalationReason.SENTIMENT_NEGATIVE: "我注意到您可能有些不满，非常抱歉给您带来困扰。让我为您联系人工客服来更好地解决您的问题。",
            EscalationReason.COMPLEX_ISSUE: "这个问题涉及到较为复杂的技术细节，为了确保给您准确的解答，我将为您转接专业技术支持团队。",
            EscalationReason.REPEATED_FAILURE: "我意识到之前的回答可能没有帮助到您。为了避免浪费您的时间，我建议您直接与人工客服沟通。",
        }

    async def evaluate_escalation(
        self,
        session_id: str,
        intent_result: IntentResult,
        conversation_state: ConversationState,
        user_sentiment: float = 0.0,
    ) -> EscalationDecision:
        """
        Evaluate whether escalation is needed with full Langfuse tracing

        Args:
            session_id: Session identifier
            intent_result: Result from intent recognition
            conversation_state: Current conversation state
            user_sentiment: User sentiment score (-1 to 1)

        Returns:
            EscalationDecision with recommendation
        """
        # Create main span for escalation evaluation
        with create_span(
            name="escalation_evaluation",
            input_data={
                "session_id": session_id,
                "turn_count": conversation_state.turn_count,
                "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        ) as main_span:

            triggers: list[EscalationReason] = []

            # Check condition 1: Low confidence
            confidence_span = create_span(
                name="confidence_check", input_data={"intent_confidence": intent_result.confidence}
            )

            if intent_result.confidence < self.confidence_threshold:
                triggers.append(EscalationReason.LOW_CONFIDENCE)

            confidence_span.end(
                output_data={
                    "threshold": self.confidence_threshold,
                    "triggered": intent_result.confidence < self.confidence_threshold,
                }
            )

            # Check condition 2: Max retries exceeded
            retry_span = create_span(
                name="retry_count_check", input_data={"current_turn": conversation_state.turn_count}
            )

            if conversation_state.turn_count >= self.max_retry_count:
                triggers.append(EscalationReason.MAX_RETRIES_EXCEEDED)

            retry_span.end(
                output_data={
                    "max_retries": self.max_retry_count,
                    "triggered": conversation_state.turn_count >= self.max_retry_count,
                }
            )

            # Check condition 3: Negative sentiment
            sentiment_span = create_span(
                name="sentiment_analysis", input_data={"sentiment_score": user_sentiment}
            )

            if user_sentiment < self.sentiment_threshold:
                triggers.append(EscalationReason.SENTIMENT_NEGATIVE)

            sentiment_span.end(
                output_data={
                    "sentiment_threshold": self.sentiment_threshold,
                    "triggered": user_sentiment < self.sentiment_threshold,
                }
            )

            # Check condition 4: User requested human agent
            if self._detect_human_request(conversation_state.dialogue_history):
                triggers.append(EscalationReason.USER_REQUESTED_HUMAN)

            # Make decision
            should_escalate = len(triggers) > 0
            primary_reason = triggers[0] if triggers else None

            decision = EscalationDecision(
                should_escalate=should_escalate,
                reason=primary_reason,
                confidence_score=intent_result.confidence,
                suggested_action=self._get_suggested_action(triggers),
            )

            # Record decision
            decision_span = create_span(
                name="escalation_decision",
                input_data={"triggers": [t.value for t in triggers]},
                output_data={
                    "should_escalate": should_escalate,
                    "reason": primary_reason.value if primary_reason else None,
                    "action": decision.suggested_action,
                },
            )
            decision_span.end()

            # If escalation triggered, record event and score
            if should_escalate:
                add_event(
                    name="escalation_triggered",
                    output_data={
                        "reason": primary_reason.value,
                        "turn_count": conversation_state.turn_count,
                        "confidence": intent_result.confidence,
                    },
                )

                score_escalation_required(True, reason=primary_reason.value)

                # Notify human agent system (mock)
                await self._notify_human_agent(session_id, decision)

            else:
                score_escalation_required(False)

            # Update main span
            main_span.end(
                output_data={
                    "should_escalate": should_escalate,
                    "reason": primary_reason.value if primary_reason else None,
                    "trigger_count": len(triggers),
                }
            )

            return decision

    async def generate_fallback_response(
        self, session_id: str, escalation_reason: EscalationReason
    ) -> str:
        """
        Generate fallback response based on escalation reason

        Args:
            session_id: Session identifier
            escalation_reason: Reason for escalation

        Returns:
            Fallback response text
        """
        # Create span for fallback generation
        with create_span(
            name="fallback_response_generation",
            input_data={"escalation_reason": escalation_reason.value},
            metadata={"session_id": session_id},
        ) as span:

            response = self.fallback_templates.get(
                escalation_reason, "为了更好地帮助您，我将为您转接人工客服。"
            )

            span.end(output_data={"response": response, "length": len(response)})

            return response

    def _detect_human_request(self, dialogue_history: list[dict]) -> bool:
        """Detect if user has requested human agent"""
        human_request_keywords = [
            "人工",
            "客服",
            "转接",
            "真人",
            "手动",
            "human",
            "agent",
            "support",
            "representative",
        ]

        # Check last few messages
        recent_messages = dialogue_history[-4:]  # Last 2 turns

        for msg in recent_messages:
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                if any(keyword in content for keyword in human_request_keywords):
                    return True

        return False

    def _get_suggested_action(self, triggers: list[EscalationReason]) -> str:
        """Get suggested action based on triggers"""
        if not triggers:
            return "continue_normal_flow"

        primary = triggers[0]

        actions = {
            EscalationReason.LOW_CONFIDENCE: "request_clarification",
            EscalationReason.MAX_RETRIES_EXCEEDED: "escalate_to_human",
            EscalationReason.USER_REQUESTED_HUMAN: "immediate_escalation",
            EscalationReason.SENTIMENT_NEGATIVE: "empathetic_escalation",
            EscalationReason.COMPLEX_ISSUE: "expert_escalation",
            EscalationReason.REPEATED_FAILURE: "supervisor_escalation",
        }

        return actions.get(primary, "escalate_to_human")

    async def _notify_human_agent(self, session_id: str, decision: EscalationDecision):
        """Notify human agent system (mock implementation)"""
        # In production, integrate with your ticketing/CRM system
        print(f"[MOCK] Notifying human agent for session {session_id}")
        print(f"[MOCK] Reason: {decision.reason}")
        print(f"[MOCK] Action: {decision.suggested_action}")

        # This would typically:
        # 1. Create a ticket in the CRM system
        # 2. Notify available agents via WebSocket
        # 3. Transfer conversation context
        # 4. Update queue status


# Singleton instance
escalation_manager = EscalationManager()


async def evaluate_escalation_need(
    session_id: str,
    intent_result: IntentResult,
    conversation_state: ConversationState,
    user_sentiment: float = 0.0,
) -> EscalationDecision:
    """
    Convenience function to evaluate escalation need

    Args:
        session_id: Session identifier
        intent_result: Intent recognition result
        conversation_state: Current conversation state
        user_sentiment: User sentiment score

    Returns:
        EscalationDecision
    """
    return await escalation_manager.evaluate_escalation(
        session_id, intent_result, conversation_state, user_sentiment
    )


async def get_fallback_response(session_id: str, reason: EscalationReason) -> str:
    """Get fallback response"""
    return await escalation_manager.generate_fallback_response(session_id, reason)


# Export
__all__ = [
    "EscalationManager",
    "EscalationDecision",
    "EscalationReason",
    "evaluate_escalation_need",
    "get_fallback_response",
]
