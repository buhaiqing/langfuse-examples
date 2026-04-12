"""
Langfuse client wrapper for real trace tracking.
"""

from typing import Any, Optional
from contextlib import contextmanager
from datetime import datetime, timezone

from langfuse import Langfuse, propagate_attributes, Langfuse
from src.observability.config import ObservabilityConfig
from src.observability.session import SessionManager
from src.observability.prompt_versioning import get_prompt_version_manager
from src.observability.feedback import (
    FeedbackType,
    record_acceptance as _record_acceptance,
    record_rejection as _record_rejection,
    record_rating as _record_rating,
    record_comment as _record_comment,
)
from langfuse import Langfuse


class LangfuseObserver:
    """Langfuse observer for tracking MCP tool executions."""

    def __init__(self, config: Optional[ObservabilityConfig] = None):
        self.config = config or ObservabilityConfig()
        self.client: Optional[Langfuse] = None

        if self.config.enabled and self.config.is_configured():
            self.client = Langfuse(
                public_key=self.config.langfuse_public_key,
                secret_key=self.config.langfuse_secret_key,
                host=self.config.langfuse_host,
            )
            print(f"Langfuse initialized (host={self.config.langfuse_host})")
        else:
            print("Langfuse disabled or not configured")

    @contextmanager
    def trace_tool_call(
        self,
        tool_name: str,
        input_args: dict[str, Any],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        prompt_version: Optional[str] = None,
        prompt_id: Optional[str] = None,
    ):
        """Context manager for tracing a tool call.
        
        Args:
            tool_name: Name of the tool being called
            input_args: Input arguments to the tool
            session_id: Optional session ID
            user_id: Optional user ID
            prompt_version: Optional prompt version
            prompt_id: Optional prompt ID (will be stored in metadata)
        """
        if not self.client:
            yield None
            return

        if session_id:
            SessionManager.set_session(session_id, user_id)

        # Prepare metadata with version info
        metadata = {
            "tool_name": tool_name,
            "prompt_version": prompt_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if prompt_id:
            metadata["prompt_id"] = prompt_id

        with SessionManager.propagate_session_ctx():
            with self.client.start_as_current_observation(
                name=tool_name,
                as_type="tool",
                input=input_args,
                metadata=metadata,
                version=prompt_version,
            ) as observation:
                try:
                    yield observation
                except Exception as e:
                    observation.update(
                        level="ERROR",
                        status_message=str(e),
                    )
                    raise
                else:
                    observation.update(
                        metadata={"status": "success"},
                    )

    def flush(self) -> None:
        """Flush all pending traces to Langfuse."""
        if self.client:
            self.client.flush()

    def shutdown(self) -> None:
        """Shutdown the Langfuse client."""
        if self.client:
            self.client.shutdown()

    def score_trace(
        self,
        trace_id: str,
        name: str,
        value: float | int,
        comment: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Score a trace with feedback.

        Args:
            trace_id: The trace ID to score.
            name: Score name (e.g., 'user-feedback', 'satisfaction').
            value: Score value (0-1 for boolean, 1-5 for ratings).
            comment: Optional comment.
            metadata: Optional additional metadata.
        """
        if not self.client:
            return

        try:
            self.client.score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment,
                metadata=metadata or {},
            )
        except Exception as e:
            print(f"Failed to score trace {trace_id}: {e}")

    def record_feedback_to_langfuse(
        self,
        trace_id: str,
        feedback_type: FeedbackType,
        value: Any,
        user_id: Optional[str] = None,
        comment: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Record feedback to Langfuse as a score.

        Args:
            trace_id: Trace ID to attach feedback to.
            feedback_type: Type of feedback (ACCEPT, REJECT, RATING, COMMENT).
            value: Feedback value.
            user_id: Optional user ID.
            comment: Optional comment.
            metadata: Optional additional metadata.
        """
        if not self.client:
            return

        # Map feedback type to score name and value
        if feedback_type == FeedbackType.ACCEPT:
            score_name = "user-feedback"
            score_value = 1.0
        elif feedback_type == FeedbackType.REJECT:
            score_name = "user-feedback"
            score_value = 0.0
        elif feedback_type == FeedbackType.RATING:
            score_name = "user-satisfaction"
            score_value = float(value)
        elif feedback_type == FeedbackType.COMMENT:
            # Comments don't have numeric scores, use metadata only
            score_name = "user-comment"
            score_value = 1.0  # Placeholder
        else:
            return

        # Prepare metadata
        fb_metadata = {
            "feedback_type": feedback_type.value,
            **(metadata or {}),
        }
        if user_id:
            fb_metadata["user_id"] = user_id

        self.score_trace(
            trace_id=trace_id,
            name=score_name,
            value=score_value,
            comment=comment,
            metadata=fb_metadata,
        )


_observer: Optional[LangfuseObserver] = None


def get_observer() -> LangfuseObserver:
    """Get the global observer instance."""
    global _observer
    if _observer is None:
        _observer = LangfuseObserver()
    return _observer


def init_observer(config: ObservabilityConfig = None) -> LangfuseObserver:
    """Initialize the global observer."""
    global _observer
    _observer = LangfuseObserver(config)
    return _observer
