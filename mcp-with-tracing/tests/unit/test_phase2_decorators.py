"""
Unit tests for Phase 2 session-related decorators.

Tests for:
- @observe_tool decorator with real Langfuse trace/span creation
- @track_session decorator
- Integration with session context propagation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.observability.decorators import observe_tool, track_session, track_prompt_version
from src.observability.session import set_session, clear_session, SessionManager


class TestObserveToolDecorator:
    """Tests for @observe_tool decorator with session context."""

    def setup_method(self):
        """Clear session before each test."""
        clear_session()

    def teardown_method(self):
        """Clear session after each test."""
        clear_session()

    @patch("src.observability.decorators.get_langfuse_client")
    def test_observe_tool_creates_trace_and_span(self, mock_get_client):
        """Test observe_tool creates a real Langfuse trace with span."""
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

        @observe_tool(name="test_tool")
        def test_func(x: int) -> int:
            return x * 2

        result = test_func(5)

        assert result == 10
        mock_client.trace.assert_called_once()
        trace_kwargs = mock_client.trace.call_args[1]
        assert trace_kwargs["name"] == "test_tool"
        mock_trace.span.assert_called_once()
        span_kwargs = mock_trace.span.call_args[1]
        assert span_kwargs["name"] == "test_tool"

    @patch("src.observability.decorators.get_langfuse_client")
    def test_observe_tool_propagates_session_context(self, mock_get_client):
        """Test observe_tool propagates session_id and user_id to trace."""
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

        set_session(session_id="test-session-123", user_id="user-456")

        @observe_tool(name="test_tool_with_session")
        def test_func(data: str) -> str:
            return data

        result = test_func("hello")

        assert result == "hello"
        trace_kwargs = mock_client.trace.call_args[1]
        assert trace_kwargs["session_id"] == "test-session-123"
        assert trace_kwargs["user_id"] == "user-456"

    @patch("src.observability.decorators.get_langfuse_client")
    def test_observe_tool_updates_span_with_output(self, mock_get_client):
        """Test observe_tool updates span with function output on success."""
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

        @observe_tool(name="output_tool")
        def test_func() -> dict:
            return {"status": "ok"}

        result = test_func()

        assert result == {"status": "ok"}
        mock_span.update.assert_called_once_with(output={"status": "ok"})

    @patch("src.observability.decorators.get_langfuse_client")
    def test_observe_tool_records_error_in_span(self, mock_get_client):
        """Test observe_tool records error in span when function raises."""
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

        @observe_tool(name="failing_tool")
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_func()

        mock_span.update.assert_called_once_with(
            level="ERROR",
            status_message="Test error",
        )

    def test_observe_tool_without_client_falls_through(self):
        """Test observe_tool calls function directly when no client available."""
        with patch("src.observability.decorators.get_langfuse_client", return_value=None):
            @observe_tool(name="no_client_tool")
            def test_func(x: int) -> int:
                return x + 1

            result = test_func(5)
            assert result == 6

    def test_observe_tool_without_session(self):
        """Test observe_tool when no session is set."""
        call_count = {"count": 0}

        with patch("src.observability.decorators.get_langfuse_client", return_value=None):
            @observe_tool(name="test_tool")
            def test_func(x: int) -> int:
                call_count["count"] += 1
                return x * 2

            result = test_func(5)

        assert result == 10
        assert call_count["count"] == 1

    def test_observe_tool_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""
        @observe_tool(name="custom_name")
        def my_documented_function():
            """This is my function."""
            pass

        assert my_documented_function.__name__ == "my_documented_function"
        assert my_documented_function.__doc__ == "This is my function."
        assert hasattr(my_documented_function, '_langfuse_observed')
        assert my_documented_function._langfuse_observed is True
        assert my_documented_function._langfuse_name == "custom_name"

    def test_observe_tool_with_default_name(self):
        """Test observe_tool uses function name when no name provided."""
        @observe_tool()
        def my_function():
            return "test"

        assert my_function._langfuse_name == "my_function"


class TestTrackSessionDecorator:
    """Tests for @track_session decorator."""

    def test_track_session_sets_attributes(self):
        """Test track_session decorator sets session attributes."""
        @track_session(session_id="decorator-session", user_id="decorator-user")
        def test_func():
            return "done"

        assert hasattr(test_func, '_langfuse_session')
        assert test_func._langfuse_session == "decorator-session"
        assert test_func._langfuse_user == "decorator-user"

    def test_track_session_without_user_id(self):
        """Test track_session with only session_id."""
        @track_session(session_id="session-only")
        def test_func():
            return "done"

        assert test_func._langfuse_session == "session-only"
        assert test_func._langfuse_user is None

    def test_track_session_sets_and_clears_context(self):
        """Test track_session sets context during execution and clears after."""
        @track_session(session_id="temp-session", user_id="temp-user")
        def test_func():
            session_id = SessionManager.get_session_id()
            user_id = SessionManager.get_user_id()
            return (session_id, user_id)

        result = test_func()
        assert result == ("temp-session", "temp-user")

        assert SessionManager.get_session_id() is None

    def test_track_session_preserves_functionality(self):
        """Test track_session doesn't break function execution."""
        @track_session("session-123", "user-456")
        def add_numbers(a: int, b: int) -> int:
            return a + b

        result = add_numbers(3, 4)
        assert result == 7


class TestTrackPromptVersionDecorator:
    """Tests for @track_prompt_version decorator."""

    @patch("src.observability.decorators.get_langfuse_client")
    def test_track_prompt_version_creates_trace_with_metadata(self, mock_get_client):
        """Test track_prompt_version creates trace with prompt metadata."""
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

        @track_prompt_version(prompt_id="test-prompt", version="v3.0")
        def test_func():
            return "done"

        result = test_func()

        assert result == "done"
        trace_kwargs = mock_client.trace.call_args[1]
        assert trace_kwargs["metadata"]["prompt_id"] == "test-prompt"
        assert trace_kwargs["metadata"]["prompt_version"] == "v3.0"
        assert trace_kwargs["version"] == "v3.0"

    @patch("src.observability.decorators.get_active_prompt_version")
    @patch("src.observability.decorators.get_langfuse_client")
    def test_track_prompt_version_auto_fetches_version(
        self, mock_get_client, mock_get_active_version
    ):
        """Test track_prompt_version auto-fetches version when not specified."""
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
        mock_get_active_version.return_value = "auto-version-1.0"

        @track_prompt_version(prompt_id="auto-prompt", version=None)
        def test_func():
            return "auto-result"

        result = test_func()

        assert result == "auto-result"
        mock_get_active_version.assert_called_once_with("auto-prompt")
        trace_kwargs = mock_client.trace.call_args[1]
        assert trace_kwargs["metadata"]["prompt_version"] == "auto-version-1.0"

    def test_track_prompt_version_sets_attributes(self):
        """Test track_prompt_version decorator sets prompt attributes."""
        @track_prompt_version(prompt_id="prompt-abc", version="v2.0")
        def test_func():
            return "result"

        assert hasattr(test_func, '_langfuse_prompt_id')
        assert test_func._langfuse_prompt_id == "prompt-abc"
        assert test_func._langfuse_prompt_version == "v2.0"

    def test_track_prompt_version_preserves_functionality(self):
        """Test track_prompt_version doesn't break function execution."""
        with patch("src.observability.decorators.get_langfuse_client", return_value=None):
            @track_prompt_version("prompt-123", "v1.5")
            def process_data(data: str) -> str:
                return data.upper()

            result = process_data("hello")
            assert result == "HELLO"


class TestDecoratorsIntegration:
    """Integration tests for multiple decorators."""

    def setup_method(self):
        """Clear session before each test."""
        clear_session()

    def teardown_method(self):
        """Clear session after each test."""
        clear_session()

    def test_combined_decorators(self):
        """Test using multiple decorators together."""
        @track_session("combined-session", "combined-user")
        @track_prompt_version("combined-prompt", "v3.0")
        @observe_tool(name="combined_tool")
        def multi_decorated_func(x: int) -> int:
            return x * 3

        assert hasattr(multi_decorated_func, '_langfuse_session')
        assert hasattr(multi_decorated_func, '_langfuse_prompt_id')
        assert hasattr(multi_decorated_func, '_langfuse_observed')

        result = multi_decorated_func(5)
        assert result == 15

    def test_decorator_with_real_session_flow(self):
        """Test decorator in realistic session flow."""
        SessionManager.start_session(
            session_id="flow-session",
            user_id="flow-user",
            metadata={"channel": "api"}
        )

        @observe_tool(name="flow_tool")
        def process_request(request_id: str) -> dict:
            session_id = SessionManager.get_session_id()
            user_id = SessionManager.get_user_id()
            return {
                "request_id": request_id,
                "session_id": session_id,
                "user_id": user_id
            }

        result = process_request("req-001")

        assert result["request_id"] == "req-001"
        assert result["session_id"] == "flow-session"
        assert result["user_id"] == "flow-user"


class TestEdgeCases:
    """Edge case tests for decorators."""

    def setup_method(self):
        """Clear session before each test."""
        clear_session()

    def teardown_method(self):
        """Clear session after each test."""
        clear_session()

    @patch("src.observability.decorators.get_langfuse_client")
    def test_observe_tool_with_empty_session(self, mock_get_client):
        """Test observe_tool when session exists but has no session_id."""
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

        from src.observability.session import _session_context
        _session_context.set({"user_id": "user-only"})

        @observe_tool(name="incomplete_session_tool")
        def test_func():
            return "ok"

        result = test_func()
        assert result == "ok"
        trace_kwargs = mock_client.trace.call_args[1]
        assert "session_id" not in trace_kwargs
        assert trace_kwargs["user_id"] == "user-only"

    @patch("src.observability.decorators.get_langfuse_client")
    def test_observe_tool_with_exception(self, mock_get_client):
        """Test observe_tool when decorated function raises exception."""
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

        @observe_tool(name="failing_tool")
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_func()

        mock_span.update.assert_called_once_with(
            level="ERROR",
            status_message="Test error",
        )

    def test_nested_session_contexts(self):
        """Test nested session context changes."""
        with patch("src.observability.decorators.get_langfuse_client", return_value=None):
            @observe_tool(name="outer_tool")
            def outer_func():
                set_session(session_id="outer-session", user_id="outer-user")

                @observe_tool(name="inner_tool")
                def inner_func():
                    return SessionManager.get_session_id()

                return inner_func()

            result = outer_func()
            assert result == "outer-session"
