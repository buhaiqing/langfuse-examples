"""
Langfuse Integration Client.

This module provides a wrapper around the Langfuse SDK for integrated
tracing with STOP Protocol.
"""

import logging
import os
from contextvars import ContextVar
from typing import Any, Optional

from langfuse import Langfuse

logger = logging.getLogger(__name__)


class LangfuseClient:
    """Singleton client for Langfuse integration with STOP Protocol."""

    _instance: Optional["LangfuseClient"] = None
    _langfuse: Langfuse | None = None

    # Context variable for trace_id propagation
    _trace_id_context: ContextVar[str | None] = ContextVar(
        "trace_id", default=None
    )

    # Context variable for parent_trace_id (cross-layer correlation)
    _parent_trace_id_context: ContextVar[str | None] = ContextVar(
        "parent_trace_id", default=None
    )

    def __new__(cls) -> "LangfuseClient":
        """Create singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize Langfuse client using unified configuration."""
        if self._langfuse is not None:
            return

        # Use unified configuration
        from skill_observability_toolkit.config import get_config

        config = get_config()

        if not config.is_langfuse_enabled():
            logger.info(
                "Langfuse not configured. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY "
                "environment variables, or disable tracing with ENABLE_TRACING=false"
            )
            self._langfuse = None
            return

        self._langfuse = Langfuse(
            public_key=config.langfuse_public_key,
            secret_key=config.langfuse_secret_key,
            host=config.langfuse_host,
            debug=config.log_level == "DEBUG",
        )

    @classmethod
    def get_instance(cls) -> Langfuse | None:
        """Get the Langfuse client instance."""
        instance = cls()
        return instance._langfuse

    @classmethod
    def is_available(cls) -> bool:
        """Check if Langfuse is configured and available."""
        return cls().get_instance() is not None

    @classmethod
    def start_trace(
        cls,
        trace_id: str | None = None,
        name: str = "skill_execution",
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Start a new trace.

        Args:
            trace_id: Optional trace ID (if None, auto-generated)
            name: Trace name
            session_id: Session identifier
            user_id: User identifier
            metadata: Additional metadata

        Returns:
            Trace ID if successful, None otherwise
        """
        client = cls.get_instance()
        if client is None:
            return None

        try:
            # Use provided trace_id or generate new one
            if not trace_id:
                import uuid
                trace_id = f"skill_trace_{uuid.uuid4().hex[:12]}"

            # Set context
            cls.set_trace_id(trace_id)

            # Optional: start trace in Langfuse
            # Note: Langfuse SDK 3.x handles this automatically

            return trace_id

        except Exception as e:
            logger.warning(f"Failed to start trace: {e}")
            return None

    @classmethod
    def end_trace(
        cls,
        status: str = "success",
        output: dict[str, Any] | None = None,
    ) -> bool:
        """
        End current trace.

        Args:
            status: Trace status (success, error)
            output: Output data

        Returns:
            True if successful, False otherwise
        """
        client = cls.get_instance()
        if client is None:
            return False

        try:
            # Optional: explicit trace update
            # Langfuse SDK handles this automatically
            return True

        except Exception as e:
            logger.warning(f"Failed to end trace: {e}")
            return False

    @classmethod
    def score_trace(
        cls,
        name: str,
        value: Any,
        data_type: str = "NUMERIC",
        comment: str | None = None,
    ) -> bool:
        """
        Add a score to the current trace.

        Args:
            name: Score name
            value: Score value
            data_type: Score data type (NUMERIC, BOOLEAN, CATEGORICAL)
            comment: Optional comment

        Returns:
            True if successful, False otherwise
        """
        client = cls.get_instance()
        if client is None:
            return False

        try:
            # Use core abstraction layer to avoid circular imports
            from skill_observability_toolkit.core import get_trace_context

            trace_context = get_trace_context()
            trace_id = cls.get_trace_id()
            if not trace_id or trace_context is None:
                return False

            # Get current span for scoring
            current_span = trace_context.get_current_span()
            if current_span:
                # Apply score to span
                current_span.score(name, value, data_type, comment)

            return True

        except Exception as e:
            logger.warning(f"Failed to end trace: {e}")
            return False

    @classmethod
    def start_span(
        cls,
        name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        input_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Start a new span.

        Args:
            name: Span name
            trace_id: Trace ID (if None, uses current context)
            parent_span_id: Parent span ID
            input_data: Input data
            metadata: Additional metadata

        Returns:
            Span context if successful, None otherwise
        """
        from skill_observability_toolkit.core import get_trace_context

        try:
            trace_context = get_trace_context()
            if trace_context is None:
                logger.warning("Trace context not initialized")
                return None

            # Use current trace ID if not provided
            if not trace_id:
                trace_id = cls.get_trace_id()

            # Create span using trace context
            span = trace_context.start_span(
                name=name,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                input_data=input_data,
                metadata=metadata,
            )

            return span

        except Exception as e:
            logger.warning(f"Failed to start span: {e}")
            return None

    @classmethod
    def end_span(
        cls,
        span: dict[str, Any],
        status: str = "success",
        output: dict[str, Any] | None = None,
    ) -> bool:
        """
        End a span.

        Args:
            span: Span to end
            status: Span status
            output: Output data

        Returns:
            True if successful, False otherwise
        """
        try:
            from skill_observability_toolkit.core import get_trace_context
            trace_context = get_trace_context()
            if trace_context:
                trace_context.end_span(span, status=status, output=output)
            return True

        except Exception as e:
            logger.warning(f"Failed to end span: {e}")
            return False

    @classmethod
    def set_trace_id(cls, trace_id: str) -> None:
        """Set the current trace ID in context."""
        cls._trace_id_context.set(trace_id)

    @classmethod
    def get_trace_id(cls) -> str | None:
        """Get the current trace ID from context."""
        return cls._trace_id_context.get()

    @classmethod
    def set_parent_trace_id(cls, parent_trace_id: str) -> None:
        """Set the parent trace ID for cross-layer correlation."""
        cls._parent_trace_id_context.set(parent_trace_id)

    @classmethod
    def get_parent_trace_id(cls) -> str | None:
        """Get the parent trace ID."""
        return cls._parent_trace_id_context.get()

    @classmethod
    def clear_trace_context(cls) -> None:
        """Clear trace context."""
        cls._trace_id_context.set(None)
        cls._parent_trace_id_context.set(None)
