"""
Feedback collection for MCP Langfuse Observability.

Provides user satisfaction signal collection, aggregation, and analysis.
"""

import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of feedback."""

    ACCEPT = "accept"
    REJECT = "reject"
    RATING = "rating"
    COMMENT = "comment"


@dataclass
class Feedback:
    """Represents user feedback."""

    trace_id: str
    feedback_type: FeedbackType
    value: Optional[Any]
    comment: Optional[str] = None
    user_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


class FeedbackCollector:
    """
    Collects and manages user feedback.

    Handles acceptance/rejection signals, ratings, and comments.
    Integrates with Langfuse for score tracking.
    """

    def __init__(self):
        self._feedback: list[Feedback] = []

    def record_acceptance(
        self,
        trace_id: str,
        user_id: Optional[str] = None,
        comment: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        send_to_langfuse: bool = True,
    ) -> Feedback:
        """
        Record a positive feedback signal.

        Args:
            trace_id: Trace identifier to attach feedback to.
            user_id: Optional user identifier.
            comment: Optional feedback comment.
            metadata: Optional additional metadata.
            send_to_langfuse: Whether to send feedback to Langfuse.

        Returns:
            Created Feedback instance.
        """
        feedback = Feedback(
            trace_id=trace_id,
            feedback_type=FeedbackType.ACCEPT,
            value=1,
            comment=comment,
            user_id=user_id,
            metadata=metadata or {},
        )
        self._feedback.append(feedback)

        # Send to Langfuse if enabled
        if send_to_langfuse:
            try:
                from src.observability.langfuse_client import get_observer
                observer = get_observer()
                observer.record_feedback_to_langfuse(
                    trace_id=trace_id,
                    feedback_type=FeedbackType.ACCEPT,
                    value=1,
                    user_id=user_id,
                    comment=comment,
                    metadata=metadata,
                )
            except Exception as e:
                logger.error("Failed to send acceptance to Langfuse: %s", e)

        return feedback

    def record_rejection(
        self,
        trace_id: str,
        user_id: Optional[str] = None,
        reason: Optional[str] = None,
        comment: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        send_to_langfuse: bool = True,
    ) -> Feedback:
        """
        Record a negative feedback signal.

        Args:
            trace_id: Trace identifier to attach feedback to.
            user_id: Optional user identifier.
            reason: Optional rejection reason.
            comment: Optional detailed comment.
            metadata: Optional additional metadata.
            send_to_langfuse: Whether to send feedback to Langfuse.

        Returns:
            Created Feedback instance.
        """
        fb_metadata = metadata or {}
        if reason:
            fb_metadata["rejection_reason"] = reason

        feedback = Feedback(
            trace_id=trace_id,
            feedback_type=FeedbackType.REJECT,
            value=0,
            comment=comment,
            user_id=user_id,
            metadata=fb_metadata,
        )
        self._feedback.append(feedback)

        # Send to Langfuse if enabled
        if send_to_langfuse:
            try:
                from src.observability.langfuse_client import get_observer
                observer = get_observer()
                observer.record_feedback_to_langfuse(
                    trace_id=trace_id,
                    feedback_type=FeedbackType.REJECT,
                    value=0,
                    user_id=user_id,
                    comment=comment,
                    metadata=fb_metadata,
                )
            except Exception as e:
                logger.error("Failed to send rejection to Langfuse: %s", e)

        return feedback

    def record_rating(
        self,
        trace_id: str,
        rating: int,
        user_id: Optional[str] = None,
        comment: Optional[str] = None,
        scale: int = 5,
        metadata: Optional[dict[str, Any]] = None,
        send_to_langfuse: bool = True,
    ) -> Feedback:
        """
        Record a rating score.

        Args:
            trace_id: Trace identifier to attach feedback to.
            rating: Rating value (1-scale).
            user_id: Optional user identifier.
            comment: Optional comment.
            scale: Maximum rating value (default 5).
            metadata: Optional additional metadata.
            send_to_langfuse: Whether to send feedback to Langfuse.

        Returns:
            Created Feedback instance.
        """
        feedback = Feedback(
            trace_id=trace_id,
            feedback_type=FeedbackType.RATING,
            value=rating,
            comment=comment,
            user_id=user_id,
            metadata={
                **(metadata or {}),
                "scale": scale,
            },
        )
        self._feedback.append(feedback)

        # Send to Langfuse if enabled
        if send_to_langfuse:
            try:
                from src.observability.langfuse_client import get_observer
                observer = get_observer()
                observer.record_feedback_to_langfuse(
                    trace_id=trace_id,
                    feedback_type=FeedbackType.RATING,
                    value=rating,
                    user_id=user_id,
                    comment=comment,
                    metadata={**(metadata or {}), "scale": scale},
                )
            except Exception as e:
                logger.error("Failed to send rating to Langfuse: %s", e)

        return feedback

    def record_comment(
        self,
        trace_id: str,
        comment: str,
        user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        send_to_langfuse: bool = True,
    ) -> Feedback:
        """
        Record a text comment without score.

        Args:
            trace_id: Trace identifier to attach feedback to.
            comment: Comment text.
            user_id: Optional user identifier.
            metadata: Optional additional metadata.
            send_to_langfuse: Whether to send feedback to Langfuse.

        Returns:
            Created Feedback instance.
        """
        feedback = Feedback(
            trace_id=trace_id,
            feedback_type=FeedbackType.COMMENT,
            value=None,
            comment=comment,
            user_id=user_id,
            metadata=metadata or {},
        )
        self._feedback.append(feedback)

        # Send to Langfuse if enabled
        if send_to_langfuse:
            try:
                from src.observability.langfuse_client import get_observer
                observer = get_observer()
                observer.record_feedback_to_langfuse(
                    trace_id=trace_id,
                    feedback_type=FeedbackType.COMMENT,
                    value=None,
                    user_id=user_id,
                    comment=comment,
                    metadata=metadata,
                )
            except Exception as e:
                logger.error("Failed to send comment to Langfuse: %s", e)

        return feedback

    def get_feedback_for_trace(self, trace_id: str) -> list[Feedback]:
        """Get all feedback for a specific trace."""
        return [f for f in self._feedback if f.trace_id == trace_id]

    def get_all_feedback(self) -> list[Feedback]:
        """Get all collected feedback."""
        return self._feedback

    def get_acceptance_rate(self) -> float:
        """
        Calculate overall acceptance rate.

        Returns:
            Acceptance rate as percentage (0-100).
        """
        scored = [
            f
            for f in self._feedback
            if f.feedback_type in (FeedbackType.ACCEPT, FeedbackType.REJECT)
        ]
        if not scored:
            return 100.0

        accepts = sum(1 for f in scored if f.feedback_type == FeedbackType.ACCEPT)
        return (accepts / len(scored)) * 100

    def get_average_rating(self) -> Optional[float]:
        """
        Calculate average rating.

        Returns:
            Average rating value, or None if no ratings.
        """
        ratings = [f for f in self._feedback if f.feedback_type == FeedbackType.RATING]
        if not ratings:
            return None

        return sum(f.value for f in ratings) / len(ratings)

    def get_feedback_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive feedback statistics.

        Returns:
            Dictionary with feedback statistics.
        """
        scored = [
            f
            for f in self._feedback
            if f.feedback_type in (FeedbackType.ACCEPT, FeedbackType.REJECT)
        ]
        ratings = [f for f in self._feedback if f.feedback_type == FeedbackType.RATING]
        comments = [f for f in self._feedback if f.feedback_type == FeedbackType.COMMENT]

        stats = {
            "total_feedback": len(self._feedback),
            "acceptance_rate": self.get_acceptance_rate(),
            "accepts": sum(1 for f in scored if f.feedback_type == FeedbackType.ACCEPT),
            "rejects": sum(1 for f in scored if f.feedback_type == FeedbackType.REJECT),
            "ratings_count": len(ratings),
            "comments_count": len(comments),
        }

        if ratings:
            stats["average_rating"] = self.get_average_rating()
            stats["rating_distribution"] = {
                str(i): sum(1 for f in ratings if f.value == i)
                for i in range(1, max(f.metadata.get("scale", 5) + 1 for f in ratings) + 1)
            }

        return stats


_feedback_collector: Optional[FeedbackCollector] = None


def get_feedback_collector() -> FeedbackCollector:
    """Get or create the global feedback collector."""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector


def record_acceptance(
    trace_id: str,
    user_id: Optional[str] = None,
    comment: Optional[str] = None,
    send_to_langfuse: bool = True,
) -> Feedback:
    """Record acceptance feedback."""
    return get_feedback_collector().record_acceptance(trace_id, user_id, comment, send_to_langfuse=send_to_langfuse)


def record_rejection(
    trace_id: str,
    user_id: Optional[str] = None,
    reason: Optional[str] = None,
    comment: Optional[str] = None,
    send_to_langfuse: bool = True,
) -> Feedback:
    """Record rejection feedback."""
    return get_feedback_collector().record_rejection(trace_id, user_id, reason, comment, send_to_langfuse=send_to_langfuse)


def record_rating(
    trace_id: str,
    rating: int,
    user_id: Optional[str] = None,
    comment: Optional[str] = None,
    send_to_langfuse: bool = True,
) -> Feedback:
    """Record rating feedback."""
    return get_feedback_collector().record_rating(trace_id, rating, user_id, comment, send_to_langfuse=send_to_langfuse)


def record_comment(
    trace_id: str,
    comment: str,
    user_id: Optional[str] = None,
    send_to_langfuse: bool = True,
) -> Feedback:
    """Record comment feedback."""
    return get_feedback_collector().record_comment(trace_id, comment, user_id, send_to_langfuse=send_to_langfuse)


def get_acceptance_rate() -> float:
    """Get current acceptance rate."""
    return get_feedback_collector().get_acceptance_rate()


def get_feedback_statistics() -> dict[str, Any]:
    """Get feedback statistics."""
    return get_feedback_collector().get_feedback_statistics()
