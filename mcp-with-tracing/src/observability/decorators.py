"""
Decorators for MCP tool instrumentation.

Provides observe_tool decorator that creates real Langfuse trace spans,
and track_session/track_prompt_version decorators for metadata attachment.
"""

import asyncio
import logging
from collections.abc import Callable
from functools import wraps

from src.observability.instrumentation import get_langfuse_client
from src.observability.prompt_versioning import get_active_prompt_version
from src.observability.session import SessionManager

logger = logging.getLogger(__name__)


def observe_tool(name: str | None = None) -> Callable[[Callable], Callable]:
    """Decorator to observe MCP tool executions with real Langfuse traces.

    Creates a Langfuse trace with a span observation for each tool call,
    recording input, output, and any errors. Session context (session_id,
    user_id) is automatically propagated from SessionManager.

    Supports both synchronous and asynchronous functions.

    Args:
        name: Optional name for the trace/span. Defaults to function name.

    Example:
        @mcp.tool()
        @observe_tool(name="submit_feedback")
        def submit_feedback(trace_id: str) -> dict:
            ...
    """

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                client = get_langfuse_client()
                if not client:
                    return await func(*args, **kwargs)

                ctx = SessionManager.get_session()
                session_id = ctx.get("session_id")
                user_id = ctx.get("user_id")

                trace_kwargs: dict = {"name": span_name}
                if session_id:
                    trace_kwargs["session_id"] = session_id
                if user_id:
                    trace_kwargs["user_id"] = user_id

                with client.trace(**trace_kwargs) as trace:
                    with trace.span(
                        name=span_name,
                        input=kwargs,
                    ) as span:
                        try:
                            result = await func(*args, **kwargs)
                            span.update(output=result)
                            return result
                        except Exception as e:
                            span.update(
                                level="ERROR",
                                status_message=str(e),
                            )
                            raise

            async_wrapper._langfuse_observed = True
            async_wrapper._langfuse_name = span_name
            return async_wrapper
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                client = get_langfuse_client()
                if not client:
                    return func(*args, **kwargs)

                ctx = SessionManager.get_session()
                session_id = ctx.get("session_id")
                user_id = ctx.get("user_id")

                trace_kwargs: dict = {"name": span_name}
                if session_id:
                    trace_kwargs["session_id"] = session_id
                if user_id:
                    trace_kwargs["user_id"] = user_id

                with client.trace(**trace_kwargs) as trace:
                    with trace.span(
                        name=span_name,
                        input=kwargs,
                    ) as span:
                        try:
                            result = func(*args, **kwargs)
                            span.update(output=result)
                            return result
                        except Exception as e:
                            span.update(
                                level="ERROR",
                                status_message=str(e),
                            )
                            raise

            wrapper._langfuse_observed = True
            wrapper._langfuse_name = span_name
            return wrapper

    return decorator


def track_session(session_id: str, user_id: str | None = None):
    """Decorator to set session context before function execution.

    Sets the session context in SessionManager so that observe_tool
    and other instrumentation can pick it up.

    Args:
        session_id: Session identifier.
        user_id: Optional user identifier.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            SessionManager.set_session(session_id, user_id)
            try:
                return func(*args, **kwargs)
            finally:
                SessionManager.clear_session()

        wrapper._langfuse_session = session_id
        wrapper._langfuse_user = user_id

        return wrapper

    return decorator


def track_prompt_version(prompt_id: str, version: str | None = None):
    """Decorator to attach prompt version metadata to traces.

    Records the prompt version in the Langfuse trace metadata
    so that prompt effectiveness can be analyzed.

    Args:
        prompt_id: The prompt identifier.
        version: Optional version string. If None, uses active version from manager.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            actual_version = version
            if actual_version is None:
                actual_version = get_active_prompt_version(prompt_id)

            client = get_langfuse_client()
            if not client:
                return func(*args, **kwargs)

            ctx = SessionManager.get_session()
            session_id = ctx.get("session_id")
            user_id = ctx.get("user_id")

            trace_kwargs = {
                "name": func.__name__,
                "metadata": {
                    "prompt_id": prompt_id,
                    "prompt_version": actual_version,
                },
                "version": actual_version,
            }
            if session_id:
                trace_kwargs["session_id"] = session_id
            if user_id:
                trace_kwargs["user_id"] = user_id

            with client.trace(**trace_kwargs) as trace:
                with trace.span(
                    name=func.__name__,
                    input=kwargs,
                    version=actual_version,
                ) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.update(output=result)
                        return result
                    except Exception as e:
                        span.update(
                            level="ERROR",
                            status_message=str(e),
                        )
                        raise

        wrapper._langfuse_prompt_id = prompt_id
        wrapper._langfuse_prompt_version = version

        return wrapper

    return decorator
