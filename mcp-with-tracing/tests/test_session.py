"""
Tests for session management.
"""

import pytest

from src.observability.session import (
    SessionManager,
    get_session_id,
    get_user_id,
    set_session,
    clear_session,
)


class TestSessionManager:
    """Tests for SessionManager class."""

    def setup_method(self):
        """Clear session before each test."""
        clear_session()

    def teardown_method(self):
        """Clear session after each test."""
        clear_session()

    def test_generate_session_id(self):
        """Test session ID generation."""
        session_id = SessionManager.generate_session_id()

        assert session_id.startswith("session-")
        assert len(session_id) <= 200
        assert session_id.isascii()

    def test_generate_session_id_unique(self):
        """Test that generated session IDs are unique."""
        id1 = SessionManager.generate_session_id()
        id2 = SessionManager.generate_session_id()

        assert id1 != id2

    def test_create_session(self):
        """Test session creation."""
        ctx = SessionManager.create_session(
            session_id="test-123",
            user_id="user-456",
            metadata={"key": "value"},
        )

        assert ctx["session_id"] == "test-123"
        assert ctx["user_id"] == "user-456"
        assert ctx["metadata"]["key"] == "value"
        assert "created_at" in ctx

    def test_create_session_auto_id(self):
        """Test session creation with auto-generated ID."""
        ctx = SessionManager.create_session()

        assert ctx["session_id"].startswith("session-")
        assert ctx["user_id"] is None
        assert ctx["metadata"] == {}

    def test_set_session(self):
        """Test setting session context."""
        SessionManager.set_session(
            session_id="test-123",
            user_id="user-456",
            metadata={"app": "mcp"},
        )

        ctx = SessionManager.get_session()
        assert ctx["session_id"] == "test-123"
        assert ctx["user_id"] == "user-456"

    def test_get_session_id(self):
        """Test getting session ID."""
        set_session("test-123", "user-456")

        session_id = get_session_id()
        assert session_id == "test-123"

    def test_get_user_id(self):
        """Test getting user ID."""
        set_session("test-123", "user-456")

        user_id = get_user_id()
        assert user_id == "user-456"

    def test_clear_session(self):
        """Test clearing session context."""
        set_session("test-123", "user-456")
        clear_session()

        ctx = SessionManager.get_session()
        assert ctx == {}

    def test_start_session(self):
        """Test starting a new session."""
        ctx = SessionManager.start_session(
            session_id="test-789",
            user_id="user-000",
        )

        assert ctx["session_id"] == "test-789"
        assert get_session_id() == "test-789"


class TestSessionConstraints:
    """Test session ID constraints."""

    def test_session_id_length(self):
        """Test session ID is within 200 char limit."""
        session_id = SessionManager.generate_session_id()
        assert len(session_id) <= 200

    def test_session_id_ascii(self):
        """Test session ID is ASCII only."""
        session_id = SessionManager.generate_session_id()
        assert session_id.isascii()
