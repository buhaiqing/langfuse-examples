"""
Standardized scoring system for customer service quality assessment
"""

from core.tracing import score_trace

# Score name constants
INTENT_CONFIDENCE = "intent_confidence"
RETRIEVAL_RELEVANCE = "retrieval_relevance"
TOOL_SUCCESS_RATE = "tool_success_rate"
ISSUE_RESOLVED = "issue_resolved"
USER_SATISFACTION = "user_satisfaction"
FAILURE_TYPE = "failure_type"
RESPONSE_LATENCY_MS = "response_latency_ms"
DIALOGUE_COHERENCE = "dialogue_coherence"
SLOT_COMPLETION_RATE = "slot_completion_rate"
ESCALATION_REQUIRED = "escalation_required"
ESCALATION_REASON = "escalation_reason"
ANSWER_CORRECTNESS = "answer_correctness"
ANSWER_HELPFULNESS = "answer_helpfulness"
FIRST_CONTACT_RESOLUTION = "first_contact_resolution"


def score_intent_confidence(confidence: float, comment: str | None = None):
    """
    Score intent recognition confidence (0-1)

    Args:
        confidence: Confidence score from intent classifier (0.0 to 1.0)
        comment: Optional explanation
    """
    score_trace(
        name=INTENT_CONFIDENCE,
        value=confidence,
        data_type="NUMERIC",
        comment=comment or f"Intent confidence: {confidence:.2f}",
    )


def score_retrieval_relevance(relevance: float, comment: str | None = None):
    """
    Score RAG retrieval relevance (0-1)

    Args:
        relevance: Relevance score (0.0 to 1.0)
        comment: Optional explanation
    """
    score_trace(
        name=RETRIEVAL_RELEVANCE,
        value=relevance,
        data_type="NUMERIC",
        comment=comment or f"Retrieval relevance: {relevance:.2f}",
    )


def score_tool_success_rate(success_rate: float, comment: str | None = None):
    """
    Score tool execution success rate (0-1)

    Args:
        success_rate: Success rate (0.0 to 1.0)
        comment: Optional explanation
    """
    score_trace(
        name=TOOL_SUCCESS_RATE,
        value=success_rate,
        data_type="NUMERIC",
        comment=comment or f"Tool success rate: {success_rate:.2f}",
    )


def score_issue_resolved(resolved: bool, comment: str | None = None):
    """
    Score whether issue was resolved (BOOLEAN)

    Args:
        resolved: True if issue was resolved
        comment: Optional explanation
    """
    score_trace(
        name=ISSUE_RESOLVED,
        value=1.0 if resolved else 0.0,
        data_type="BOOLEAN",
        comment=comment or ("Issue resolved" if resolved else "Issue not resolved"),
    )


def score_user_satisfaction(rating: int, comment: str | None = None):
    """
    Score user satisfaction (1-5 Likert scale)

    Args:
        rating: Satisfaction rating (1 to 5)
        comment: Optional explanation
    """
    if not 1 <= rating <= 5:
        raise ValueError(f"Satisfaction rating must be 1-5, got {rating}")

    score_trace(
        name=USER_SATISFACTION,
        value=float(rating),
        data_type="NUMERIC",
        comment=comment or f"User satisfaction: {rating}/5",
    )


def score_failure_type(failure_type: str, comment: str | None = None):
    """
    Categorize failure type (CATEGORICAL)

    Args:
        failure_type: Type of failure (e.g., "intent_recognition_error",
                     "rag_retrieval_failure", "tool_call_failure")
        comment: Optional explanation
    """
    valid_types = [
        "intent_recognition_error",
        "rag_retrieval_failure",
        "tool_call_failure",
        "generation_quality_issue",
        "user_experience_issue",
        "none",  # No failure
    ]

    if failure_type not in valid_types:
        raise ValueError(f"Invalid failure type: {failure_type}. Must be one of {valid_types}")

    score_trace(
        name=FAILURE_TYPE,
        value=failure_type,
        data_type="CATEGORICAL",
        comment=comment or f"Failure type: {failure_type}",
    )


def score_response_latency(latency_ms: float, comment: str | None = None):
    """
    Score response latency in milliseconds

    Args:
        latency_ms: Response time in milliseconds
        comment: Optional explanation
    """
    score_trace(
        name=RESPONSE_LATENCY_MS,
        value=latency_ms,
        data_type="NUMERIC",
        comment=comment or f"Response latency: {latency_ms:.0f}ms",
    )


def score_dialogue_coherence(coherence: float, comment: str | None = None):
    """
    Score dialogue coherence (0-1)

    Args:
        coherence: Coherence score (0.0 to 1.0)
        comment: Optional explanation
    """
    score_trace(
        name=DIALOGUE_COHERENCE,
        value=coherence,
        data_type="NUMERIC",
        comment=comment or f"Dialogue coherence: {coherence:.2f}",
    )


def score_slot_completion_rate(rate: float, comment: str | None = None):
    """
    Score slot filling completion rate (0-1)

    Args:
        rate: Completion rate (0.0 to 1.0)
        comment: Optional explanation
    """
    score_trace(
        name=SLOT_COMPLETION_RATE,
        value=rate,
        data_type="NUMERIC",
        comment=comment or f"Slot completion: {rate:.0%}",
    )


def score_escalation_required(required: bool, reason: str | None = None):
    """
    Score whether escalation is required (BOOLEAN)

    Args:
        required: True if escalation to human agent is needed
        reason: Reason for escalation
    """
    score_trace(
        name=ESCALATION_REQUIRED,
        value=1.0 if required else 0.0,
        data_type="BOOLEAN",
        comment=f"Escalation required: {reason}" if reason else None,
    )

    if required and reason:
        score_trace(
            name=ESCALATION_REASON,
            value=reason,
            data_type="CATEGORICAL",
            comment=f"Escalation reason: {reason}",
        )


def score_first_contact_resolution(resolved: bool, comment: str | None = None):
    """
    Score first contact resolution (BOOLEAN)

    Args:
        resolved: True if issue was resolved in first contact
        comment: Optional explanation
    """
    score_trace(
        name=FIRST_CONTACT_RESOLUTION,
        value=1.0 if resolved else 0.0,
        data_type="BOOLEAN",
        comment=comment
        or ("Resolved on first contact" if resolved else "Required multiple contacts"),
    )


def add_comprehensive_scores(
    intent_confidence: float | None = None,
    retrieval_relevance: float | None = None,
    tool_success_rate: float | None = None,
    issue_resolved: bool | None = None,
    user_satisfaction: int | None = None,
    response_latency_ms: float | None = None,
    failure_type: str | None = None,
    escalation_required: bool | None = None,
    escalation_reason: str | None = None,
):
    """
    Add comprehensive scores for a complete customer service interaction.

    Args:
        intent_confidence: Intent recognition confidence (0-1)
        retrieval_relevance: RAG retrieval relevance (0-1)
        tool_success_rate: Tool execution success rate (0-1)
        issue_resolved: Whether issue was resolved
        user_satisfaction: User satisfaction rating (1-5)
        response_latency_ms: Total response time in ms
        failure_type: Type of failure if any
        escalation_required: Whether escalation was needed
        escalation_reason: Reason for escalation
    """
    if intent_confidence is not None:
        score_intent_confidence(intent_confidence)

    if retrieval_relevance is not None:
        score_retrieval_relevance(retrieval_relevance)

    if tool_success_rate is not None:
        score_tool_success_rate(tool_success_rate)

    if issue_resolved is not None:
        score_issue_resolved(issue_resolved)

    if user_satisfaction is not None:
        score_user_satisfaction(user_satisfaction)

    if response_latency_ms is not None:
        score_response_latency(response_latency_ms)

    if failure_type is not None:
        score_failure_type(failure_type)

    if escalation_required is not None:
        score_escalation_required(escalation_required, escalation_reason)


# Export all scoring functions
__all__ = [
    "score_intent_confidence",
    "score_retrieval_relevance",
    "score_tool_success_rate",
    "score_issue_resolved",
    "score_user_satisfaction",
    "score_failure_type",
    "score_response_latency",
    "score_dialogue_coherence",
    "score_slot_completion_rate",
    "score_escalation_required",
    "score_first_contact_resolution",
    "add_comprehensive_scores",
    # Constants
    "INTENT_CONFIDENCE",
    "RETRIEVAL_RELEVANCE",
    "TOOL_SUCCESS_RATE",
    "ISSUE_RESOLVED",
    "USER_SATISFACTION",
    "FAILURE_TYPE",
    "RESPONSE_LATENCY_MS",
]
