"""
Core Trace Context Abstraction.

Provides abstract interfaces to decouple module dependencies and
prevent circular imports between tracer, client, and decorator modules.
"""

from typing import Any, Protocol


class TraceContextProtocol(Protocol):
    """
    Protocol for trace context management.

    Defines the minimal interface that trace context implementations must provide,
    enabling decoupling between tracer and client modules.
    """

    def get_trace_id(self) -> str | None:
        """
        Get current trace ID from context.

        Returns:
            Current trace ID or None if not initialized
        """
        ...

    def set_trace_id(self, trace_id: str) -> None:
        """
        Set trace ID in context.

        Args:
            trace_id: Trace ID to set
        """
        ...

    def get_current_span(self) -> Any | None:
        """
        Get current active span from context.

        Returns:
            Current span object or None if no active span
        """
        ...

    def push_span(self, span: Any) -> None:
        """
        Push a span onto the context stack.

        Args:
            span: Span object to push
        """
        ...

    def pop_span(self) -> Any | None:
        """
        Pop and return the current span from context.

        Returns:
            Popped span object or None if stack is empty
        """
        ...


class SpanProtocol(Protocol):
    """
    Protocol for span objects.

    Defines the minimal interface that span implementations must provide.
    """

    @property
    def span_id(self) -> str:
        """Span identifier."""
        ...

    @property
    def trace_id(self) -> str:
        """Parent trace identifier."""
        ...

    @property
    def name(self) -> str:
        """Span name."""
        ...

    def score(
        self,
        name: str,
        value: Any,
        type_: str = "NUMERIC",
        comment: str = "",
    ) -> Any:
        """
        Record a score for this span.

        Args:
            name: Score name
            value: Score value
            type_: Score type (NUMERIC, BOOLEAN, CATEGORICAL)
            comment: Optional comment

        Returns:
            Self for method chaining
        """
        ...

    def end(
        self,
        output: dict[str, Any] | None = None,
        status: str = "success",
    ) -> Any:
        """
        Mark span as completed.

        Args:
            output: Output data to record
            status: Exit status (success, error)

        Returns:
            Self for method chaining
        """
        ...


# Global trace context getter/setter
# Allows modules to register their context implementation without direct import

_trace_context: TraceContextProtocol | None = None


def register_trace_context(context: TraceContextProtocol) -> None:
    """
    Register a trace context implementation.

    This allows modules to provide their context without creating circular imports.

    Args:
        context: TraceContextProtocol implementation
    """
    global _trace_context
    _trace_context = context


def get_trace_context() -> TraceContextProtocol | None:
    """
    Get the registered trace context implementation.

    Returns:
        TraceContextProtocol implementation or None if not registered
    """
    return _trace_context