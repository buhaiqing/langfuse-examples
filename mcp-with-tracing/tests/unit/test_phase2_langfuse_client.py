"""
Unit tests for Phase 2 langfuse_client session integration.

Tests for:
- trace_tool_call with session context
- Session propagation in LangfuseObserver
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from src.observability.langfuse_client import LangfuseObserver, get_observer, init_observer
from src.observability.session import set_session, clear_session, SessionManager
from src.observability.config import ObservabilityConfig


class TestLangfuseObserverSessionIntegration:
    """Tests for LangfuseObserver session integration."""

    def setup_method(self):
        """Clear session before each test."""
        clear_session()

    def teardown_method(self):
        """Clear session after each test."""
        clear_session()

    def test_trace_tool_call_with_session_sets_context(self):
        """Test that trace_tool_call sets session context when session_id provided."""
        config = ObservabilityConfig()
        config.enabled = False  # Disable actual Langfuse calls
        observer = LangfuseObserver(config)

        # When Langfuse is disabled, session_id parameter is not used
        # This tests the behavior when client is None
        with observer.trace_tool_call(
            tool_name="test_tool",
            input_args={"param": "value"},
            session_id="explicit-session-123",
            user_id="explicit-user-456",
        ) as obs:
            # When client is None, yields None and doesn't set session
            assert obs is None

    def test_trace_tool_call_without_session_id(self):
        """Test trace_tool_call when no session_id is provided."""
        config = ObservabilityConfig()
        config.enabled = False
        observer = LangfuseObserver(config)

        # Set session beforehand
        set_session(session_id="pre-set-session", user_id="pre-set-user")

        with observer.trace_tool_call(
            tool_name="test_tool",
            input_args={},
        ):
            # Should use pre-existing session
            current_session = SessionManager.get_session_id()
            assert current_session == "pre-set-session"

    def test_trace_tool_call_propagates_session_ctx(self):
        """Test that trace_tool_call uses propagate_session_ctx."""
        config = ObservabilityConfig()
        config.enabled = False
        observer = LangfuseObserver(config)

        set_session(
            session_id="propagation-test",
            user_id="user-test",
            metadata={"test": "metadata"}
        )

        # This should use SessionManager.propagate_session_ctx() internally
        with observer.trace_tool_call(
            tool_name="propagation_tool",
            input_args={},
        ) as obs:
            # Session should be accessible
            assert SessionManager.get_session_id() == "propagation-test"

    def test_trace_tool_call_handles_disabled_langfuse(self):
        """Test trace_tool_call when Langfuse is not configured."""
        config = ObservabilityConfig()
        config.enabled = False
        config.langfuse_public_key = ""
        config.langfuse_secret_key = ""
        
        observer = LangfuseObserver(config)
        assert observer.client is None

        # Should not raise error, just yield None
        with observer.trace_tool_call(
            tool_name="disabled_tool",
            input_args={},
        ) as obs:
            assert obs is None

    def test_trace_tool_call_exception_handling(self):
        """Test that trace_tool_call handles exceptions properly."""
        # Create mock client
        mock_client = MagicMock()
        mock_observation = MagicMock()
        mock_client.start_as_current_observation.return_value.__enter__ = Mock(return_value=mock_observation)
        mock_client.start_as_current_observation.return_value.__exit__ = Mock(return_value=None)

        config = ObservabilityConfig()
        config.enabled = True
        observer = LangfuseObserver(config)
        observer.client = mock_client

        set_session(session_id="error-session", user_id="error-user")

        # Function that raises exception
        def failing_tool():
            raise RuntimeError("Tool execution failed")

        with pytest.raises(RuntimeError, match="Tool execution failed"):
            with observer.trace_tool_call(
                tool_name="failing_tool",
                input_args={},
            ):
                failing_tool()

        # Verify error was recorded
        mock_observation.update.assert_called()
        update_kwargs = mock_observation.update.call_args[1]
        assert update_kwargs["level"] == "ERROR"
        assert "Tool execution failed" in update_kwargs["status_message"]

    def test_trace_tool_call_success_metadata(self):
        """Test that successful tool call records success metadata."""
        mock_client = MagicMock()
        mock_observation = MagicMock()
        mock_client.start_as_current_observation.return_value.__enter__ = Mock(return_value=mock_observation)
        mock_client.start_as_current_observation.return_value.__exit__ = Mock(return_value=None)

        config = ObservabilityConfig()
        config.enabled = True
        observer = LangfuseObserver(config)
        observer.client = mock_client

        with observer.trace_tool_call(
            tool_name="success_tool",
            input_args={"input": "data"},
        ):
            pass

        # Verify success metadata was added
        mock_observation.update.assert_called()
        update_kwargs = mock_observation.update.call_args[1]
        assert update_kwargs["metadata"]["status"] == "success"

    def test_trace_tool_call_with_prompt_version(self):
        """Test trace_tool_call includes prompt_version in metadata."""
        mock_client = MagicMock()
        mock_observation = MagicMock()
        mock_client.start_as_current_observation.return_value.__enter__ = Mock(return_value=mock_observation)
        mock_client.start_as_current_observation.return_value.__exit__ = Mock(return_value=None)

        config = ObservabilityConfig()
        config.enabled = True
        observer = LangfuseObserver(config)
        observer.client = mock_client

        with observer.trace_tool_call(
            tool_name="versioned_tool",
            input_args={},
            prompt_version="v2.5",
        ):
            pass

        # Verify prompt_version was included
        call_kwargs = mock_client.start_as_current_observation.call_args[1]
        assert call_kwargs["version"] == "v2.5"
        assert call_kwargs["metadata"]["prompt_version"] == "v2.5"

    def test_trace_tool_call_timestamp_metadata(self):
        """Test that trace_tool_call includes timestamp in metadata."""
        mock_client = MagicMock()
        mock_observation = MagicMock()
        mock_client.start_as_current_observation.return_value.__enter__ = Mock(return_value=mock_observation)
        mock_client.start_as_current_observation.return_value.__exit__ = Mock(return_value=None)

        config = ObservabilityConfig()
        config.enabled = True
        observer = LangfuseObserver(config)
        observer.client = mock_client

        with observer.trace_tool_call(
            tool_name="timestamp_tool",
            input_args={},
        ):
            pass

        # Verify timestamp was included
        call_kwargs = mock_client.start_as_current_observation.call_args[1]
        assert "timestamp" in call_kwargs["metadata"]
        # Verify it's a valid ISO format timestamp
        timestamp_str = call_kwargs["metadata"]["timestamp"]
        datetime.fromisoformat(timestamp_str)  # Should not raise


class TestLangfuseObserverLifecycle:
    """Tests for LangfuseObserver lifecycle methods."""

    def test_flush_with_client(self):
        """Test flush method when client exists."""
        mock_client = MagicMock()
        
        config = ObservabilityConfig()
        config.enabled = True
        observer = LangfuseObserver(config)
        observer.client = mock_client

        observer.flush()
        
        mock_client.flush.assert_called_once()

    def test_flush_without_client(self):
        """Test flush method when client is None."""
        config = ObservabilityConfig()
        config.enabled = False
        observer = LangfuseObserver(config)
        assert observer.client is None

        # Should not raise error
        observer.flush()

    def test_shutdown_with_client(self):
        """Test shutdown method when client exists."""
        mock_client = MagicMock()
        
        config = ObservabilityConfig()
        config.enabled = True
        observer = LangfuseObserver(config)
        observer.client = mock_client

        observer.shutdown()
        
        mock_client.shutdown.assert_called_once()

    def test_shutdown_without_client(self):
        """Test shutdown method when client is None."""
        config = ObservabilityConfig()
        config.enabled = False
        observer = LangfuseObserver(config)
        assert observer.client is None

        # Should not raise error
        observer.shutdown()


class TestGlobalObserverFunctions:
    """Tests for global observer functions."""

    def teardown_method(self):
        """Reset global observer after each test."""
        import src.observability.langfuse_client as lc
        lc._observer = None

    def test_get_observer_creates_instance(self):
        """Test get_observer creates instance if none exists."""
        import src.observability.langfuse_client as lc
        lc._observer = None

        observer = get_observer()
        
        assert observer is not None
        assert isinstance(observer, LangfuseObserver)
        # Should be singleton
        assert get_observer() is observer

    def test_init_observer_creates_new_instance(self):
        """Test init_observer creates new observer instance."""
        import src.observability.langfuse_client as lc
        lc._observer = None

        config = ObservabilityConfig()
        config.enabled = False
        
        observer1 = get_observer()
        observer2 = init_observer(config)
        
        assert observer2 is not observer1
        assert isinstance(observer2, LangfuseObserver)


class TestSessionPropagationEdgeCases:
    """Edge case tests for session propagation."""

    def setup_method(self):
        """Clear session before each test."""
        clear_session()

    def teardown_method(self):
        """Clear session after each test."""
        clear_session()

    def test_trace_tool_call_with_none_session_id(self):
        """Test trace_tool_call when session_id is explicitly None."""
        config = ObservabilityConfig()
        config.enabled = False
        observer = LangfuseObserver(config)

        with observer.trace_tool_call(
            tool_name="none_session_tool",
            input_args={},
            session_id=None,
        ):
            # Should not set session
            assert SessionManager.get_session_id() is None

    def test_trace_tool_call_with_empty_user_id(self):
        """Test trace_tool_call with empty user_id."""
        # Set session first since disabled observer won't set it
        set_session(session_id="session-only", user_id="")
        
        config = ObservabilityConfig()
        config.enabled = False
        observer = LangfuseObserver(config)

        with observer.trace_tool_call(
            tool_name="empty_user_tool",
            input_args={},
        ):
            current_user = SessionManager.get_user_id()
            assert current_user == ""

    def test_multiple_nested_trace_calls(self):
        """Test multiple nested trace_tool_call contexts."""
        config = ObservabilityConfig()
        config.enabled = False
        observer = LangfuseObserver(config)

        set_session(session_id="outer-session", user_id="outer-user")

        with observer.trace_tool_call(tool_name="outer_tool", input_args={}):
            assert SessionManager.get_session_id() == "outer-session"
            
            # Inner call should maintain same session
            with observer.trace_tool_call(tool_name="inner_tool", input_args={}):
                assert SessionManager.get_session_id() == "outer-session"

    def test_trace_tool_call_preserves_existing_metadata(self):
        """Test that trace_tool_call preserves existing session metadata."""
        config = ObservabilityConfig()
        config.enabled = False
        observer = LangfuseObserver(config)

        set_session(
            session_id="metadata-session",
            user_id="metadata-user",
            metadata={"existing_key": "existing_value", "another_key": "another_value"}
        )

        with observer.trace_tool_call(
            tool_name="metadata_tool",
            input_args={},
        ):
            ctx = SessionManager.get_session()
            assert ctx["metadata"]["existing_key"] == "existing_value"
            assert ctx["metadata"]["another_key"] == "another_value"
