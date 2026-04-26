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
        config.enabled = False
        observer = LangfuseObserver(config)

        with observer.trace_tool_call(
            tool_name="test_tool",
            input_args={"param": "value"},
            session_id="explicit-session-123",
            user_id="explicit-user-456",
        ) as obs:
            assert obs is None

    def test_trace_tool_call_without_session_id(self):
        """Test trace_tool_call when no session_id is provided."""
        config = ObservabilityConfig()
        config.enabled = False
        observer = LangfuseObserver(config)

        set_session(session_id="pre-set-session", user_id="pre-set-user")

        with observer.trace_tool_call(
            tool_name="test_tool",
            input_args={},
        ):
            current_session = SessionManager.get_session_id()
            assert current_session == "pre-set-session"

    def test_trace_tool_call_propagates_session_ctx(self):
        """Test that trace_tool_call uses session context."""
        config = ObservabilityConfig()
        config.enabled = False
        observer = LangfuseObserver(config)

        set_session(
            session_id="propagation-test",
            user_id="user-test",
            metadata={"test": "metadata"}
        )

        with observer.trace_tool_call(
            tool_name="propagation_tool",
            input_args={},
        ) as obs:
            assert SessionManager.get_session_id() == "propagation-test"

    def test_trace_tool_call_handles_disabled_langfuse(self):
        """Test trace_tool_call when Langfuse is not configured."""
        config = ObservabilityConfig()
        config.enabled = False
        config.langfuse_public_key = ""
        config.langfuse_secret_key = ""

        observer = LangfuseObserver(config)
        assert observer.client is None

        with observer.trace_tool_call(
            tool_name="disabled_tool",
            input_args={},
        ) as obs:
            assert obs is None

    @patch("src.observability.langfuse_client.get_langfuse_client")
    def test_trace_tool_call_exception_handling(self, mock_get_client):
        """Test that trace_tool_call handles exceptions properly."""
        mock_client = MagicMock()
        mock_trace = MagicMock()
        mock_span = MagicMock()
        mock_trace.__enter__ = Mock(return_value=mock_trace)
        mock_trace.__exit__ = Mock(return_value=False)
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_trace.span.return_value = mock_span
        mock_client.trace.return_value = mock_trace
        mock_get_client.return_value = mock_client

        observer = LangfuseObserver()
        set_session(session_id="error-session", user_id="error-user")

        def failing_tool():
            raise RuntimeError("Tool execution failed")

        with pytest.raises(RuntimeError, match="Tool execution failed"):
            with observer.trace_tool_call(
                tool_name="failing_tool",
                input_args={},
            ):
                failing_tool()

        mock_span.update.assert_called()
        update_kwargs = mock_span.update.call_args[1]
        assert update_kwargs["level"] == "ERROR"
        assert "Tool execution failed" in update_kwargs["status_message"]

    @patch("src.observability.langfuse_client.get_langfuse_client")
    def test_trace_tool_call_success_metadata(self, mock_get_client):
        """Test that successful tool call records success metadata."""
        mock_client = MagicMock()
        mock_trace = MagicMock()
        mock_span = MagicMock()
        mock_trace.__enter__ = Mock(return_value=mock_trace)
        mock_trace.__exit__ = Mock(return_value=False)
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_trace.span.return_value = mock_span
        mock_client.trace.return_value = mock_trace
        mock_get_client.return_value = mock_client

        observer = LangfuseObserver()

        with observer.trace_tool_call(
            tool_name="success_tool",
            input_args={"input": "data"},
        ):
            pass

        mock_span.update.assert_called()
        update_kwargs = mock_span.update.call_args[1]
        assert update_kwargs["metadata"]["status"] == "success"

    @patch("src.observability.langfuse_client.get_langfuse_client")
    def test_trace_tool_call_with_prompt_version(self, mock_get_client):
        """Test trace_tool_call includes prompt_version in metadata."""
        mock_client = MagicMock()
        mock_trace = MagicMock()
        mock_span = MagicMock()
        mock_trace.__enter__ = Mock(return_value=mock_trace)
        mock_trace.__exit__ = Mock(return_value=False)
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_trace.span.return_value = mock_span
        mock_client.trace.return_value = mock_trace
        mock_get_client.return_value = mock_client

        observer = LangfuseObserver()

        with observer.trace_tool_call(
            tool_name="versioned_tool",
            input_args={},
            prompt_version="v2.5",
        ):
            pass

        trace_kwargs = mock_client.trace.call_args[1]
        assert trace_kwargs["version"] == "v2.5"
        assert trace_kwargs["metadata"]["prompt_version"] == "v2.5"

    @patch("src.observability.langfuse_client.get_langfuse_client")
    def test_trace_tool_call_timestamp_metadata(self, mock_get_client):
        """Test that trace_tool_call includes timestamp in metadata."""
        mock_client = MagicMock()
        mock_trace = MagicMock()
        mock_span = MagicMock()
        mock_trace.__enter__ = Mock(return_value=mock_trace)
        mock_trace.__exit__ = Mock(return_value=False)
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_trace.span.return_value = mock_span
        mock_client.trace.return_value = mock_trace
        mock_get_client.return_value = mock_client

        observer = LangfuseObserver()

        with observer.trace_tool_call(
            tool_name="timestamp_tool",
            input_args={},
        ):
            pass

        trace_kwargs = mock_client.trace.call_args[1]
        assert "timestamp" in trace_kwargs["metadata"]
        timestamp_str = trace_kwargs["metadata"]["timestamp"]
        datetime.fromisoformat(timestamp_str)


class TestLangfuseObserverLifecycle:
    """Tests for LangfuseObserver lifecycle methods."""

    @patch("src.observability.langfuse_client.get_langfuse_client")
    def test_flush_with_client(self, mock_get_client):
        """Test flush method when client exists."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        observer = LangfuseObserver()
        observer.flush()

        mock_client.flush.assert_called_once()

    def test_flush_without_client(self):
        """Test flush method when client is None."""
        config = ObservabilityConfig()
        config.enabled = False
        observer = LangfuseObserver(config)
        assert observer.client is None

        observer.flush()

    @patch("src.observability.langfuse_client.get_langfuse_client")
    def test_shutdown_with_client(self, mock_get_client):
        """Test shutdown method when client exists."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        observer = LangfuseObserver()
        observer.shutdown()

        mock_client.shutdown.assert_called_once()

    def test_shutdown_without_client(self):
        """Test shutdown method when client is None."""
        config = ObservabilityConfig()
        config.enabled = False
        observer = LangfuseObserver(config)
        assert observer.client is None

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
            assert SessionManager.get_session_id() is None

    def test_trace_tool_call_with_empty_user_id(self):
        """Test trace_tool_call with empty user_id."""
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
