"""
Langfuse instrumentation and initialization.
"""

from typing import Any
from contextvars import ContextVar

from langfuse import Langfuse

from src.observability.config import ObservabilityConfig

_session_context: ContextVar[dict[str, Any]] = ContextVar(
    "session_context",
    default={},
)

_langfuse_client: Langfuse | None = None


def init_observability(config: ObservabilityConfig = None) -> Langfuse | None:
    global _langfuse_client

    if config is None:
        config = ObservabilityConfig()

    if not config.enabled:
        print("Observability disabled. Skipping Langfuse initialization.")
        _langfuse_client = None
        return None

    if not config.is_configured():
        print("Langfuse credentials not configured. Observability will be disabled.")
        _langfuse_client = None
        return None

    _langfuse_client = Langfuse(
        public_key=config.langfuse_public_key,
        secret_key=config.langfuse_secret_key,
        host=config.langfuse_host,
    )

    print(f"Langfuse initialized successfully (host={config.langfuse_host})")
    return _langfuse_client


def get_langfuse_client() -> Langfuse | None:
    """Get the global Langfuse client instance."""
    return _langfuse_client


def set_session_context(session_id: str, user_id: str = None) -> None:
    """Set session context for trace propagation."""
    _session_context.set({"session_id": session_id, "user_id": user_id})


def get_session_context() -> dict[str, Any]:
    """Get current session context."""
    return _session_context.get()


def clear_session_context() -> None:
    """Clear session context."""
    _session_context.set({})
