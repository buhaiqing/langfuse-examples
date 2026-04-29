"""
Session management for MCP Langfuse Observability.
"""

import logging
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_session_context: ContextVar[dict[str, Any] | None] = ContextVar(
    "session_context",
    default=None,
)


class SessionManager:
    """
    Manages session lifecycle and context propagation.

    Handles session ID generation, storage, and context variable management.
    Session context is passed directly to Langfuse trace creation methods
    (session_id, user_id parameters) rather than through a separate
    propagation mechanism.
    """

    @staticmethod
    def generate_session_id() -> str:
        """
        Generate a unique session ID.

        Returns:
            Session ID string (UUID format, <=200 chars, ASCII).
        """
        return f"session-{uuid.uuid4().hex}"

    @staticmethod
    def create_session(
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new session context.

        Args:
            session_id: Optional session ID. If None, generates new ID.
            user_id: Optional user ID.
            metadata: Optional session metadata.

        Returns:
            Session context dictionary.
        """
        ctx = {
            "session_id": session_id or SessionManager.generate_session_id(),
            "user_id": user_id,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return ctx

    @classmethod
    def set_session(
        cls,
        session_id: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Set session context in contextvars.

        Args:
            session_id: Session identifier.
            user_id: Optional user identifier.
            metadata: Optional metadata.
        """
        ctx = cls.create_session(session_id=session_id, user_id=user_id, metadata=metadata)
        _session_context.set(ctx)

    @classmethod
    def get_session(cls) -> dict[str, Any]:
        """Get current session context.

        Returns:
            Session context dictionary, or empty dict if not set.
        """
        ctx = _session_context.get()
        # Return a copy to prevent external mutation
        return ctx.copy() if ctx is not None else {}

    @classmethod
    def get_session_id(cls) -> str | None:
        """Get current session ID.

        Returns:
            Session ID string or None if not set.
        """
        ctx = _session_context.get()
        if ctx is None:
            return None
        return ctx.get("session_id")

    @classmethod
    def get_user_id(cls) -> str | None:
        """Get current user ID.

        Returns:
            User ID string or None if not set.
        """
        ctx = _session_context.get()
        if ctx is None:
            return None
        return ctx.get("user_id")

    @classmethod
    def clear_session(cls) -> None:
        """Clear session context."""
        _session_context.set({})

    @classmethod
    def start_session(
        cls,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Start a new session and set it in context.

        Args:
            session_id: Optional session ID. If None, generates new ID.
            user_id: Optional user ID.
            metadata: Optional metadata.

        Returns:
            Session context dictionary.
        """
        ctx = cls.create_session(session_id=session_id, user_id=user_id, metadata=metadata)
        _session_context.set(ctx)
        return ctx


def get_session_id() -> str | None:
    """Get current session ID from context."""
    return SessionManager.get_session_id()


def get_user_id() -> str | None:
    """Get current user ID from context."""
    return SessionManager.get_user_id()


def set_session(
    session_id: str,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Set session context."""
    SessionManager.set_session(session_id, user_id, metadata)


def clear_session() -> None:
    """Clear session context."""
    SessionManager.clear_session()
