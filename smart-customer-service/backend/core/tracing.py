"""
Core tracing decorators and context management for customer service
"""

from functools import wraps
from typing import Any

from langfuse import observe

from core.langfuse_client import langfuse


def trace_customer_service(
    name: str,
    session_id: str | None = None,
    user_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
):
    """
    Decorator for tracing customer service interactions.
    Automatically creates a trace with session and user context.

    Args:
        name: Trace name (e.g., "tech_support_conversation")
        session_id: Unique session identifier
        user_id: User identifier (will be hashed for privacy)
        tags: List of tags for categorization
        metadata: Additional metadata to attach to trace

    Returns:
        Decorated async function with tracing enabled

    Example:
        @trace_customer_service(
            name="api_error_troubleshooting",
            session_id="session_123",
            user_id="user_456",
            tags=["technical_support", "api_issue"]
        )
        async def handle_api_error(query: str):
            # Your business logic here
            pass
    """

    def decorator(func):
        @wraps(func)
        @observe(name=name, as_type="agent")
        async def wrapper(*args, **kwargs):
            # Update current trace with context
            if session_id or user_id or tags or metadata:
                update_kwargs = {}
                if session_id:
                    update_kwargs["session_id"] = session_id
                if user_id:
                    from utils.data_masking import hash_user_id

                    update_kwargs["user_id"] = hash_user_id(user_id)
                if tags:
                    update_kwargs["tags"] = tags
                if metadata:
                    update_kwargs["metadata"] = metadata

                if update_kwargs:
                    langfuse.update_current_trace(**update_kwargs)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def create_span(
    name: str,
    input_data: Any | None = None,
    metadata: dict[str, Any] | None = None,
    as_type: str = "span",
):
    """
    Context manager for creating spans within a trace.

    Args:
        name: Span name
        input_data: Input data for the span
        metadata: Additional metadata
        as_type: Type of observation (span, generation, retriever, etc.)

    Returns:
        Langfuse span object

    Example:
        with create_span("intent_recognition", input_data={"query": text}) as span:
            result = recognize_intent(text)
            span.end(output={"intent": result})
    """
    class SpanContextManager:
        def __init__(self, span):
            self.span = span
        
        def __enter__(self):
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                try:
                    self.end(output_data={"error": str(exc_val)})
                except Exception:
                    pass
            else:
                pass
        
        def end(self, *args, **kwargs):
            try:
                # Try with output parameter
                if 'output_data' in kwargs:
                    kwargs['output'] = kwargs.pop('output_data')
                return self.span.end(*args, **kwargs)
            except Exception:
                # If any error occurs, just return None
                return None
        
        def add_event(self, name: str, output_data: Any = None, **kwargs):
            """Add event to the span"""
            try:
                if output_data is not None:
                    kwargs['output'] = output_data
                self.span.event(name=name, **kwargs)
            except Exception:
                pass
        
        def __getattr__(self, name):
            return getattr(self.span, name)
    
    span = langfuse.start_span(name=name, input=input_data, metadata=metadata)
    return SpanContextManager(span)


def score_trace(
    name: str,
    value: float,
    data_type: str = "NUMERIC",
    comment: str | None = None,
    metadata: dict[str, Any] | None = None,
):
    """
    Convenience function to score the current trace.

    Args:
        name: Score name (e.g., "user_satisfaction")
        value: Score value
        data_type: Type of score (NUMERIC, CATEGORICAL, BOOLEAN)
        comment: Optional comment explaining the score
        metadata: Additional metadata

    Example:
        score_trace("user_satisfaction", 4.5, comment="User rated 4.5/5")
    """
    langfuse.score_current_trace(
        name=name, value=value, data_type=data_type, comment=comment, metadata=metadata
    )


def score_span(name: str, value: float, data_type: str = "NUMERIC", comment: str | None = None):
    """
    Convenience function to score the current span.

    Args:
        name: Score name
        value: Score value
        data_type: Type of score
        comment: Optional comment
    """
    langfuse.score_current_span(name=name, value=value, data_type=data_type, comment=comment)


def add_event(
    name: str,
    input_data: Any | None = None,
    output_data: Any | None = None,
    metadata: dict[str, Any] | None = None,
):
    """
    Add an event to the current trace.

    Args:
        name: Event name
        input_data: Event input data
        output_data: Event output data
        metadata: Additional metadata

    Example:
        add_event(
            "escalation_triggered",
            output_data={"reason": "low_confidence"}
        )
    """
    try:
        langfuse.event(name=name, input=input_data, output=output_data, metadata=metadata)
    except AttributeError:
        pass


def update_trace_metadata(metadata: dict[str, Any]):
    """
    Update metadata for the current trace.

    Args:
        metadata: Metadata to add/update
    """
    langfuse.update_current_trace(metadata=metadata)


def update_trace_tags(tags: list[str]):
    """
    Update tags for the current trace.

    Args:
        tags: List of tags to add
    """
    langfuse.update_current_trace(tags=tags)


# Export all utilities
__all__ = [
    "trace_customer_service",
    "create_span",
    "score_trace",
    "score_span",
    "add_event",
    "update_trace_metadata",
    "update_trace_tags",
]
