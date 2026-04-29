"""
Langfuse client wrapper for trace tracking.

Uses the shared Langfuse client from instrumentation module
instead of creating a separate instance.
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from langfuse import Langfuse

from src.observability.config import ObservabilityConfig
from src.observability.feedback import FeedbackType
from src.observability.instrumentation import get_langfuse_client
from src.observability.session import SessionManager

logger = logging.getLogger(__name__)


class LangfuseObserver:
    """Langfuse observer for tracking MCP tool executions.

    Uses the shared Langfuse client obtained from get_langfuse_client()
    to ensure all modules use the same client instance.
    """

    def __init__(self, config: ObservabilityConfig | None = None):
        self.config: ObservabilityConfig | None = config
        self._own_client: Langfuse | None = None

        if config is not None and config.enabled and config.is_configured():
            self._own_client = Langfuse(
                public_key=config.langfuse_public_key,
                secret_key=config.langfuse_secret_key,
                host=config.langfuse_host,
            )
            logger.info("LangfuseObserver initialized with dedicated client (host=%s)", config.langfuse_host)

    @property
    def client(self) -> Langfuse | None:
        """Get the Langfuse client.

        Priority:
        1. Own client (if created with explicit config)
        2. Shared global client from instrumentation module

        Returns:
            Langfuse client instance or None if not available.
        """
        if self._own_client is not None:
            return self._own_client
        return get_langfuse_client()

    @contextmanager
    def trace_tool_call(
        self,
        tool_name: str,
        input_args: dict[str, Any],
        session_id: str | None = None,
        user_id: str | None = None,
        prompt_version: str | None = None,
        prompt_id: str | None = None,
    ):
        """Context manager for tracing a tool call.

        Creates a real Langfuse trace with a span observation,
        properly recording input, output, and errors.

        Args:
            tool_name: Name of the tool being called.
            input_args: Input arguments to the tool.
            session_id: Optional session ID.
            user_id: Optional user ID.
            prompt_version: Optional prompt version.
            prompt_id: Optional prompt ID (stored in metadata).
        """
        client = self.client
        if not client:
            yield None
            return

        if session_id:
            SessionManager.set_session(session_id, user_id)

        ctx = SessionManager.get_session()
        effective_session_id = ctx.get("session_id") or session_id
        effective_user_id = ctx.get("user_id") or user_id

        metadata = {
            "tool_name": tool_name,
            "prompt_version": prompt_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if prompt_id:
            metadata["prompt_id"] = prompt_id

        trace_kwargs = {
            "name": tool_name,
            "input": input_args,
            "metadata": metadata,
            "version": prompt_version,
        }
        if effective_session_id:
            trace_kwargs["session_id"] = effective_session_id
        if effective_user_id:
            trace_kwargs["user_id"] = effective_user_id

        with client.trace(**trace_kwargs) as trace:
            with trace.span(
                name=tool_name,
                input=input_args,
                version=prompt_version,
            ) as span:
                try:
                    yield span
                except Exception as e:
                    span.update(
                        level="ERROR",
                        status_message=str(e),
                    )
                    raise
                else:
                    span.update(
                        metadata={"status": "success"},
                    )

    def flush(self) -> None:
        """Flush all pending traces to Langfuse."""
        client = self.client
        if client:
            client.flush()

    def shutdown(self) -> None:
        """Shutdown the Langfuse client."""
        client = self.client
        if client:
            client.shutdown()

    def score_trace(
        self,
        trace_id: str,
        name: str,
        value: float | int,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Score a trace with feedback.

        Args:
            trace_id: The trace ID to score.
            name: Score name (e.g., 'user-feedback', 'satisfaction').
            value: Score value (0-1 for boolean, 1-5 for ratings).
            comment: Optional comment.
            metadata: Optional additional metadata.
        """
        client = self.client
        if not client:
            return

        try:
            score_kwargs = {
                "trace_id": trace_id,
                "name": name,
                "value": value,
            }
            if comment:
                score_kwargs["comment"] = comment
            if metadata:
                score_kwargs["metadata"] = metadata

            client.score(**score_kwargs)
        except Exception as e:
            logger.error("Failed to score trace %s: %s", trace_id, e)

    def record_feedback_to_langfuse(
        self,
        trace_id: str,
        feedback_type: FeedbackType,
        value: Any,
        user_id: str | None = None,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record feedback to Langfuse as a score.

        Args:
            trace_id: Trace ID to attach feedback to.
            feedback_type: Type of feedback (ACCEPT, REJECT, RATING, COMMENT).
            value: Feedback value.
            user_id: Optional user ID.
            comment: Optional comment.
            metadata: Optional additional metadata.
        """
        client = self.client
        if not client:
            return

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
            score_name = "user-comment"
            score_value = 1.0
        else:
            return

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


_observer: LangfuseObserver | None = None


def get_observer() -> LangfuseObserver:
    """Get the global observer instance.

    The observer uses the shared Langfuse client from get_langfuse_client().
    """
    global _observer
    if _observer is None:
        _observer = LangfuseObserver()
    return _observer


def init_observer(config: ObservabilityConfig | None = None) -> LangfuseObserver:
    """Initialize the global observer with an optional config.

    If config is provided and valid, the observer will use a dedicated
    Langfuse client. Otherwise, it falls back to the shared global client.

    Args:
        config: Optional ObservabilityConfig for dedicated client.

    Returns:
        The initialized LangfuseObserver instance.
    """
    global _observer
    _observer = LangfuseObserver(config)
    return _observer
