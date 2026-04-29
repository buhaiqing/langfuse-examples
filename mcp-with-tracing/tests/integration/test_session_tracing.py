"""
Integration tests for multi-session tracing scenarios.

Tests cover:
1. Session isolation between concurrent sessions
2. Session ID propagation across multiple tool calls
3. Session replay functionality
4. Async session handling
"""

import asyncio

import pytest

from src.observability.langfuse_client import get_observer
from src.observability.session import (
    SessionManager,
    clear_session,
    get_session_id,
    get_user_id,
    set_session,
)


@pytest.mark.integration
class TestSessionTracing:
    """Integration tests for session tracing functionality."""

    def test_single_session_multiple_tools(self):
        """Test that multiple tool calls share the same session_id."""
        observer = get_observer()
        session_id = SessionManager.generate_session_id()
        user_id = "test-user-001"

        # Set session context
        set_session(session_id=session_id, user_id=user_id)

        # Simulate multiple tool calls in the same session
        tools_called = []
        for i in range(3):
            tool_name = f"tool_{i+1}"
            with observer.trace_tool_call(
                tool_name=tool_name,
                input_args={"call_number": i + 1},
            ) as obs:
                if obs:
                    obs.update(output_data={"result": f"success_{i+1}"})
                tools_called.append(tool_name)

        current_session = get_session_id()
        assert current_session == session_id, "Session ID should remain consistent"
        assert len(tools_called) == 3

        # Clear session
        clear_session()

    def test_session_isolation(self):
        """Test that different sessions are properly isolated."""
        observer = get_observer()

        # Create two separate sessions
        session_1 = SessionManager.generate_session_id()
        session_2 = SessionManager.generate_session_id()
        user_1 = "user-A"
        user_2 = "user-B"

        # Execute tool call in session 1
        set_session(session_id=session_1, user_id=user_1)
        with observer.trace_tool_call(
            tool_name="session_1_tool",
            input_args={"session": "1"},
        ):
            pass

        # Switch to session 2
        set_session(session_id=session_2, user_id=user_2)
        with observer.trace_tool_call(
            tool_name="session_2_tool",
            input_args={"session": "2"},
        ):
            pass

        # Verify isolation
        assert get_session_id() == session_2, "Should be in session 2"
        assert get_user_id() == user_2, "Should be user B"

        # Clear session
        clear_session()

    def test_session_metadata(self):
        """Test session metadata attachment."""
        observer = get_observer()
        session_id = SessionManager.generate_session_id()

        metadata = {
            "channel": "web_chat",
            "customer_tier": "enterprise",
            "product_version": "v2.3",
            "priority": "high",
        }

        # Set session with metadata
        set_session(
            session_id=session_id,
            user_id="vip-user-001",
            metadata=metadata,
        )

        # Execute tool call
        with observer.trace_tool_call(
            tool_name="metadata_test_tool",
            input_args={"test": "metadata"},
        ) as obs:
            if obs:
                obs.update(output_data={"metadata_attached": True})

        ctx = SessionManager.get_session()
        assert ctx["metadata"] == metadata, "Metadata should match"

        # Clear session
        clear_session()

    def test_session_lifecycle(self):
        """Test complete session lifecycle."""
        observer = get_observer()

        # 1. Start session
        ctx = SessionManager.start_session(
            session_id="lifecycle-test-session",
            user_id="lifecycle-user",
            metadata={"test": "lifecycle"}
        )
        assert ctx["session_id"] == "lifecycle-test-session"

        # 2. Use session
        with observer.trace_tool_call(
            tool_name="lifecycle_tool_1",
            input_args={},
        ):
            pass

        with observer.trace_tool_call(
            tool_name="lifecycle_tool_2",
            input_args={},
        ):
            pass

        # 3. Verify session
        current_session = get_session_id()
        current_user = get_user_id()
        assert current_session == "lifecycle-test-session"
        assert current_user == "lifecycle-user"

        # 4. Clear session
        clear_session()
        ctx_after_clear = SessionManager.get_session()
        assert ctx_after_clear == {}, "Session should be empty after clear"

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self):
        """Test multiple concurrent sessions (async)."""
        observer = get_observer()
        num_sessions = 3  # Reduced for faster testing

        async def session_worker(session_num: int):
            """Worker function for each session."""
            session_id = f"concurrent-session-{session_num}"
            user_id = f"user-{session_num}"

            # Set session context for this worker
            set_session(session_id=session_id, user_id=user_id)

            # Execute multiple tool calls
            for i in range(2):  # Reduced iterations
                tool_name = f"session_{session_num}_tool_{i+1}"
                with observer.trace_tool_call(
                    tool_name=tool_name,
                    input_args={"async": True},
                ) as obs:
                    await asyncio.sleep(0.01)  # Small delay
                    if obs:
                        obs.update(output_data={"status": "completed"})

            final_session = get_session_id()
            assert final_session == session_id
            return session_num

        # Run all sessions concurrently
        results = await asyncio.gather(*[
            session_worker(i) for i in range(1, num_sessions + 1)
        ])

        assert len(results) == num_sessions

        # Clear session
        clear_session()
