"""
Session management for MCP Langfuse Observability.
"""

import uuid
from typing import Any, Optional
from contextvars import ContextVar
from datetime import datetime, timezone
from contextlib import nullcontext

from langfuse import propagate_attributes


_session_context: ContextVar[dict[str, Any]] = ContextVar(
    "session_context",
    default={},
)


class SessionManager:
    """
    Manages session lifecycle and context propagation.

    Handles session ID generation, storage, and Langfuse attribute propagation.
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
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
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
        user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
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
        """Get current session context."""
        return _session_context.get()

    @classmethod
    def get_session_id(cls) -> Optional[str]:
        """Get current session ID."""
        ctx = _session_context.get()
        return ctx.get("session_id")

    @classmethod
    def get_user_id(cls) -> Optional[str]:
        """Get current user ID."""
        ctx = _session_context.get()
        return ctx.get("user_id")

    @classmethod
    def clear_session(cls) -> None:
        """Clear session context."""
        _session_context.set({})

    @staticmethod
    def propagate_session_ctx():
        ctx = SessionManager.get_session()
        if not ctx.get("session_id"):
            return nullcontext()

        return propagate_attributes(
            session_id=ctx["session_id"],
            user_id=ctx.get("user_id"),
            metadata=ctx.get("metadata", {}),
        )

    @classmethod
    def start_session(
        cls,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
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


def get_session_id() -> Optional[str]:
    """Get current session ID from context."""
    return SessionManager.get_session_id()


def get_user_id() -> Optional[str]:
    """Get current user ID from context."""
    return SessionManager.get_user_id()


def set_session(
    session_id: str,
    user_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Set session context."""
    SessionManager.set_session(session_id, user_id, metadata)


def clear_session() -> None:
    """Clear session context."""
    SessionManager.clear_session()
