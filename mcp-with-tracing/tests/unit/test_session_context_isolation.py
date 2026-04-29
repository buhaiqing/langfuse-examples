"""
Unit tests for session context isolation.

Tests verify that ContextVar properly isolates session state
across concurrent tasks and prevents state pollution.
"""

import asyncio

from src.observability.session import (
    SessionManager,
    clear_session,
    get_session_id,
    get_user_id,
    set_session,
)


class TestSessionContextIsolation:
    """Test session context isolation in concurrent scenarios."""

    def setup_method(self):
        """Clear session before each test."""
        SessionManager.clear_session()

    def teardown_method(self):
        """Clean up after each test."""
        SessionManager.clear_session()

    def test_session_isolation_in_async_tasks(self):
        """Test that session context is isolated across async tasks."""

        async def task_1():
            SessionManager.set_session("session_1", "user_1")
            await asyncio.sleep(0.01)  # Simulate some async work
            return SessionManager.get_session_id()

        async def task_2():
            SessionManager.set_session("session_2", "user_2")
            await asyncio.sleep(0.01)
            return SessionManager.get_session_id()

        async def run_tasks():
            # Run both tasks concurrently
            result_1, result_2 = await asyncio.gather(task_1(), task_2())
            return result_1, result_2

        result_1, result_2 = asyncio.run(run_tasks())

        # Each task should see its own session
        assert result_1 == "session_1"
        assert result_2 == "session_2"

    def test_clear_session_returns_empty_dict(self):
        """Test that clear_session resets context to empty dict."""
        SessionManager.set_session("test_session", "test_user")
        assert SessionManager.get_session_id() == "test_session"

        SessionManager.clear_session()
        session = SessionManager.get_session()
        assert session == {}
        assert SessionManager.get_session_id() is None
        assert SessionManager.get_user_id() is None

    def test_get_session_returns_empty_dict_when_not_set(self):
        """Test get_session returns {} when no session is set."""
        # Ensure no session is set
        SessionManager.clear_session()
        session = SessionManager.get_session()
        assert session == {}
        assert isinstance(session, dict)

    def test_concurrent_session_sets_no_pollution(self):
        """Test rapid session sets don't cause pollution."""

        async def set_and_verify(session_id: str, user_id: str):
            SessionManager.set_session(session_id, user_id)
            # Verify immediately
            assert SessionManager.get_session_id() == session_id
            assert SessionManager.get_user_id() == user_id
            await asyncio.sleep(0.001)
            # Verify again after small delay
            assert SessionManager.get_session_id() == session_id
            assert SessionManager.get_user_id() == user_id

        async def run_concurrent_sets():
            tasks = [set_and_verify(f"session_{i}", f"user_{i}") for i in range(10)]
            await asyncio.gather(*tasks)

        asyncio.run(run_concurrent_sets())

    def test_nested_session_context(self):
        """Test nested session context handling."""
        # Set outer session
        SessionManager.set_session("outer_session", "outer_user")
        assert SessionManager.get_session_id() == "outer_session"

        # Simulate nested context (in real scenario, this would be a new async task)
        SessionManager.set_session("inner_session", "inner_user")
        assert SessionManager.get_session_id() == "inner_session"

        # Clear and verify
        SessionManager.clear_session()
        assert SessionManager.get_session_id() is None

    def test_session_metadata_isolation(self):
        """Test session metadata is properly isolated."""

        async def task_with_metadata(session_id: str, metadata: dict):
            SessionManager.set_session(session_id, metadata=metadata)
            await asyncio.sleep(0.01)
            session = SessionManager.get_session()
            return session.get("metadata")

        async def run_tasks():
            results = await asyncio.gather(
                task_with_metadata("session_1", {"key": "value1"}),
                task_with_metadata("session_2", {"key": "value2"}),
            )
            return results

        results = asyncio.run(run_tasks())
        assert results[0] == {"key": "value1"}
        assert results[1] == {"key": "value2"}

    def test_default_value_is_not_mutable(self):
        """Test that default value is not shared mutable object."""
        # Get session twice without setting
        session1 = SessionManager.get_session()
        session2 = SessionManager.get_session()

        # They should be equal (both empty dicts)
        assert session1 == session2 == {}

        # Mutating session1 doesn't affect session2 or future calls
        # (ContextVar returns a new empty dict each time when default is None)
        session1["test"] = "value"
        session3 = SessionManager.get_session()
        assert "test" not in session3
        assert session3 == {}


class TestSessionManagerBasic:
    """Test basic SessionManager functionality."""

    def setup_method(self):
        """Clear session before each test."""
        SessionManager.clear_session()

    def teardown_method(self):
        """Clean up after each test."""
        SessionManager.clear_session()

    def test_set_and_get_session(self):
        """Test basic set and get session."""
        SessionManager.set_session("test_session", "test_user")
        assert SessionManager.get_session_id() == "test_session"
        assert SessionManager.get_user_id() == "test_user"

    def test_generate_session_id(self):
        """Test session ID generation."""
        session_id = SessionManager.generate_session_id()
        assert session_id.startswith("session-")
        assert len(session_id) > 10

    def test_create_session_without_id(self):
        """Test session creation with auto-generated ID."""
        session = SessionManager.create_session()
        assert "session_id" in session
        assert session["session_id"].startswith("session-")
        assert "created_at" in session

    def test_start_session(self):
        """Test start_session sets context."""
        session = SessionManager.start_session("my_session", "my_user")
        assert session["session_id"] == "my_session"
        assert SessionManager.get_session_id() == "my_session"

    def test_helper_functions(self):
        """Test module-level helper functions."""
        set_session("helper_session", "helper_user")
        assert get_session_id() == "helper_session"
        assert get_user_id() == "helper_user"

        clear_session()
        assert get_session_id() is None
        assert get_user_id() is None
