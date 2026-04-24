"""
Trace ID Context Management.

This module provides context-based trace ID propagation using contextvars.
"""

import uuid
from contextvars import ContextVar
from typing import Any

# Trace ID context
_trace_id_context: ContextVar[str | None] = ContextVar(
    "trace_id", default=None
)

# Parent trace ID context (for cross-layer correlation)
_parent_trace_id_context: ContextVar[str | None] = ContextVar(
    "parent_trace_id", default=None
)

# Current span context (stack of active spans)
_current_span_stack: ContextVar[list] = ContextVar(
    "span_stack", default=[]
)


def set_trace_id(trace_id: str) -> None:
    """Set the current trace ID."""
    _trace_id_context.set(trace_id)


def get_trace_id() -> str | None:
    """Get the current trace ID."""
    return _trace_id_context.get()


def generate_trace_id(prefix: str = "skill") -> str:
    """
    Generate a new trace ID.

    Args:
        prefix: Prefix for trace ID

    Returns:
        Generated trace ID
    """
    trace_id = f"{prefix}_{uuid.uuid4().hex[:12]}"
    set_trace_id(trace_id)
    return trace_id


def set_parent_trace_id(parent_trace_id: str) -> None:
    """Set the parent trace ID for cross-layer correlation."""
    _parent_trace_id_context.set(parent_trace_id)


def get_parent_trace_id() -> str | None:
    """Get the parent trace ID."""
    return _parent_trace_id_context.get()


def get_current_span() -> dict[str, Any] | None:
    """Get the current active span."""
    stack = _current_span_stack.get()
    return stack[-1] if stack else None


def push_span(span: dict[str, Any]) -> None:
    """Push a span onto the context stack."""
    stack = _current_span_stack.get()
    stack.append(span)
    _current_span_stack.set(stack)


def pop_span() -> dict[str, Any] | None:
    """Pop the current span from the context stack and return the NEW current span."""
    stack = _current_span_stack.get()
    if stack:
        popped = stack.pop()
        _current_span_stack.set(stack)
        return popped
    return None


def clear_trace_context() -> None:
    """Clear all trace context variables."""
    _trace_id_context.set(None)
    _parent_trace_id_context.set(None)
    _current_span_stack.set([])


class TraceContextManager:
    """Context manager for trace context."""

    def __init__(
        self,
        trace_id: str | None = None,
        parent_trace_id: str | None = None,
    ):
        self.trace_id = trace_id
        self.parent_trace_id = parent_trace_id
        self._trace_id_tokens: list = []
        self._parent_trace_id_tokens: list = []

    def __enter__(self):
        """Enter context manager."""
        if self.trace_id:
            self._trace_id_tokens.append(_trace_id_context.set(self.trace_id))
        if self.parent_trace_id:
            self._parent_trace_id_tokens.append(_parent_trace_id_context.set(self.parent_trace_id))
        return self

    def end(self):
        """End the trace context."""
        self.__exit__(None, None, None)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and restore context."""
        for token in reversed(self._trace_id_tokens):
            try:
                _trace_id_context.reset(token)
            except Exception:
                pass

        for token in reversed(self._parent_trace_id_tokens):
            try:
                _parent_trace_id_context.reset(token)
            except Exception:
                pass

        self._trace_id_tokens = []
        self._parent_trace_id_tokens = []
        return False


def create_trace_context(
    trace_id: str | None = None,
    parent_trace_id: str | None = None,
) -> TraceContextManager:
    """
    Create a trace context manager.

    Args:
        trace_id: Trace ID (if None, auto-generated)
        parent_trace_id: Parent trace ID

    Returns:
        TraceContextManager instance
    """
    return TraceContextManager(
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
    )
