"""
Decorators for MCP tool instrumentation.
"""

from functools import wraps
from typing import Callable

from langfuse import propagate_attributes
from src.observability.session import SessionManager


def observe_tool(name: str = None):
    """Decorator to observe MCP tool executions."""

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            ctx = SessionManager.get_session()

            if ctx.get("session_id"):
                with propagate_attributes(
                    session_id=ctx["session_id"],
                    user_id=ctx.get("user_id"),
                    metadata=ctx.get("metadata", {}),
                ):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        wrapper._langfuse_observed = True
        wrapper._langfuse_name = span_name

        return wrapper

    return decorator


def track_session(session_id: str, user_id: str = None):
    """Decorator to attach session metadata to traces."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper._langfuse_session = session_id
        wrapper._langfuse_user = user_id

        return wrapper

    return decorator


def track_prompt_version(prompt_id: str, version: str):
    """Decorator to attach prompt version metadata to traces."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper._langfuse_prompt_id = prompt_id
        wrapper._langfuse_prompt_version = version

        return wrapper

    return decorator
