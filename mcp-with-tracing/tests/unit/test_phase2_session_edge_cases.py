"""
Edge case and boundary tests for Phase 2 session management.

Tests edge cases not covered in main test suite.
"""


from src.observability.session import (
    SessionManager,
    _session_context,
    clear_session,
    get_session_id,
    get_user_id,
    set_session,
)


class TestSessionManagerEdgeCases:
    """Edge case tests for SessionManager."""

    def setup_method(self):
        """Clear session before each test."""
        clear_session()

    def teardown_method(self):
        """Clear session after each test."""
        clear_session()

    def test_get_session_id_when_no_session(self):
        """Test get_session_id when no session is set."""
        clear_session()

        session_id = get_session_id()
        assert session_id is None

    def test_get_user_id_when_no_session(self):
        """Test get_user_id when no session is set."""
        clear_session()

        user_id = get_user_id()
        assert user_id is None

    def test_get_user_id_when_session_no_user(self):
        """Test get_user_id when session exists but no user_id."""
        _session_context.set({"session_id": "test-session"})

        user_id = get_user_id()
        assert user_id is None

    def test_set_session_overwrites_previous(self):
        """Test that set_session overwrites previous session."""
        set_session(session_id="first-session", user_id="first-user")
        assert get_session_id() == "first-session"

        set_session(session_id="second-session", user_id="second-user")
        assert get_session_id() == "second-session"
        assert get_user_id() == "second-user"

    def test_session_metadata_merging(self):
        """Test session metadata handling."""
        set_session(
            session_id="meta-session",
            user_id="meta-user",
            metadata={"key1": "value1"}
        )

        ctx = SessionManager.get_session()
        assert ctx["metadata"]["key1"] == "value1"

        # Update with new metadata
        set_session(
            session_id="meta-session",
            user_id="meta-user",
            metadata={"key2": "value2"}
        )

        ctx = SessionManager.get_session()
        # Should overwrite, not merge
        assert "key1" not in ctx["metadata"]
        assert ctx["metadata"]["key2"] == "value2"

    def test_start_session_returns_context(self):
        """Test that start_session returns the created context."""
        ctx = SessionManager.start_session(
            session_id="return-test",
            user_id="return-user",
            metadata={"test": "data"}
        )

        assert isinstance(ctx, dict)
        assert ctx["session_id"] == "return-test"
        assert ctx["user_id"] == "return-user"
        assert ctx["metadata"]["test"] == "data"
        assert "created_at" in ctx

    def test_create_session_vs_start_session(self):
        """Test difference between create_session and start_session."""
        # create_session returns context but doesn't set it
        ctx1 = SessionManager.create_session(session_id="create-test")
        assert get_session_id() is None  # Not set in context

        # start_session returns context AND sets it
        ctx2 = SessionManager.start_session(session_id="start-test")
        assert get_session_id() == "start-test"  # Set in context


class TestSessionIDGeneration:
    """Tests for session ID generation edge cases."""

    def test_session_id_format_consistency(self):
        """Test that all generated session IDs follow same format."""
        ids = [SessionManager.generate_session_id() for _ in range(100)]

        for sid in ids:
            assert sid.startswith("session-")
            assert len(sid) <= 200
            assert sid.isascii()

    def test_session_id_uniqueness_large_scale(self):
        """Test session ID uniqueness with large sample."""
        ids = [SessionManager.generate_session_id() for _ in range(1000)]

        # All should be unique
        assert len(ids) == len(set(ids))

    def test_custom_session_id_validation(self):
        """Test using custom session IDs."""
        # Valid custom ID
        set_session(session_id="custom-id-123", user_id="user")
        assert get_session_id() == "custom-id-123"

        # Custom ID with special characters (still valid if ASCII)
        set_session(session_id="custom_id.with-special+chars", user_id="user")
        assert get_session_id() == "custom_id.with-special+chars"


class TestContextVarsBehavior:
    """Tests for contextvars behavior."""

    def setup_method(self):
        """Clear session before each test."""
        clear_session()

    def teardown_method(self):
        """Clear session after each test."""
        clear_session()

    def test_context_isolation_between_tests(self):
        """Test that context is properly isolated."""
        # This test verifies setup/teardown works
        assert get_session_id() is None

        set_session(session_id="isolation-test", user_id="iso-user")
        assert get_session_id() == "isolation-test"

        # After clear, should be None again
        clear_session()
        assert get_session_id() is None

    def test_get_session_returns_copy_or_reference(self):
        """Test whether get_session returns copy or reference."""
        set_session(session_id="ref-test", user_id="ref-user", metadata={"key": "value"})

        ctx = SessionManager.get_session()
        original_id = ctx["session_id"]

        # Modify returned dict
        ctx["session_id"] = "modified"

        # Check if original was affected
        current_id = get_session_id()
        # If it's a reference, this would be "modified"
        # If it's a copy, this would be "ref-test"
        # Current implementation returns reference
        assert current_id == "modified"


class TestSessionWithComplexMetadata:
    """Tests for sessions with complex metadata."""

    def setup_method(self):
        """Clear session before each test."""
        clear_session()

    def teardown_method(self):
        """Clear session after each test."""
        clear_session()

    def test_session_with_nested_metadata(self):
        """Test session with nested metadata structures."""
        complex_metadata = {
            "user_profile": {
                "name": "John Doe",
                "preferences": {
                    "theme": "dark",
                    "language": "en"
                }
            },
            "request_info": {
                "ip": "192.168.1.1",
                "user_agent": "Mozilla/5.0"
            },
            "tags": ["vip", "enterprise", "priority"]
        }

        set_session(
            session_id="complex-meta-session",
            user_id="complex-user",
            metadata=complex_metadata
        )

        ctx = SessionManager.get_session()
        assert ctx["metadata"]["user_profile"]["name"] == "John Doe"
        assert ctx["metadata"]["request_info"]["ip"] == "192.168.1.1"
        assert "vip" in ctx["metadata"]["tags"]

    def test_session_with_none_metadata(self):
        """Test session with None metadata."""
        set_session(
            session_id="none-meta-session",
            user_id="none-meta-user",
            metadata=None
        )

        ctx = SessionManager.get_session()
        assert ctx["metadata"] == {}

    def test_session_with_empty_metadata(self):
        """Test session with empty metadata dict."""
        set_session(
            session_id="empty-meta-session",
            user_id="empty-meta-user",
            metadata={}
        )

        ctx = SessionManager.get_session()
        assert ctx["metadata"] == {}


class TestSessionTimestamp:
    """Tests for session timestamp functionality."""

    def test_created_at_timestamp_format(self):
        """Test that created_at timestamp is in ISO format."""
        ctx = SessionManager.create_session(session_id="timestamp-test")

        assert "created_at" in ctx
        timestamp_str = ctx["created_at"]

        # Should be parseable as ISO format
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp_str)
        assert dt is not None

    def test_created_at_is_utc(self):
        """Test that created_at timestamp is in UTC."""
        ctx = SessionManager.create_session(session_id="utc-test")

        timestamp_str = ctx["created_at"]
        # ISO format with timezone should end with +00:00 or Z
        assert "+00:00" in timestamp_str or timestamp_str.endswith("Z")

    def test_timestamp_uniqueness(self):
        """Test that timestamps are created for each session."""
        ctx1 = SessionManager.create_session(session_id="ts-1")
        ctx2 = SessionManager.create_session(session_id="ts-2")

        # Both should have timestamps
        assert "created_at" in ctx1
        assert "created_at" in ctx2
