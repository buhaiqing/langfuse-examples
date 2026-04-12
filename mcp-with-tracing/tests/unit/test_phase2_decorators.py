"""
Unit tests for Phase 2 session-related decorators.

Tests for:
- @observe_tool decorator with session context propagation
- @track_session decorator
- Integration with propagate_attributes
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

    def test_observe_tool_without_session(self):
        """Test observe_tool when no session is set."""
        call_count = {"count": 0}

        @observe_tool(name="test_tool")
        def test_func(x: int) -> int:
            call_count["count"] += 1
            return x * 2

        result = test_func(5)
        
        assert result == 10
        assert call_count["count"] == 1
        # Should execute without error even without session

    def test_observe_tool_with_session_context(self):
        """Test observe_tool propagates session context."""
        set_session(session_id="test-session-123", user_id="user-456")

        @observe_tool(name="test_tool_with_session")
        def test_func(data: str) -> str:
            # Verify session is accessible during execution
            current_session = SessionManager.get_session_id()
            current_user = SessionManager.get_user_id()
            return f"{data}|{current_session}|{current_user}"

        result = test_func("hello")
        
        assert "test-session-123" in result
        assert "user-456" in result

    @patch('src.observability.decorators.propagate_attributes')
    def test_observe_tool_calls_propagate_attributes(self, mock_propagate):
        """Test that observe_tool calls propagate_attributes with correct params."""
        mock_context = MagicMock()
        mock_propagate.return_value.__enter__ = Mock(return_value=None)
        mock_propagate.return_value.__exit__ = Mock(return_value=None)

        set_session(session_id="session-abc", user_id="user-xyz", metadata={"key": "value"})

        @observe_tool(name="tracked_tool")
        def test_func():
            return "result"

        result = test_func()
        
        assert result == "result"
        # Verify propagate_attributes was called
        mock_propagate.assert_called_once()
        call_kwargs = mock_propagate.call_args[1]
        assert call_kwargs["session_id"] == "session-abc"
        assert call_kwargs["user_id"] == "user-xyz"
        assert call_kwargs["metadata"] == {"key": "value"}

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

    def test_track_session_preserves_functionality(self):
        """Test track_session doesn't break function execution."""
        @track_session("session-123", "user-456")
        def add_numbers(a: int, b: int) -> int:
            return a + b

        result = add_numbers(3, 4)
        assert result == 7


class TestTrackPromptVersionDecorator:
    """Tests for @track_prompt_version decorator."""

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
        @track_prompt_version("prompt-123", "v1.5")
        def process_data(data: str) -> str:
            return data.upper()

        result = process_data("hello")
        assert result == "HELLO"

    @patch('src.observability.decorators.propagate_attributes')
    def test_track_prompt_version_with_explicit_version(self, mock_propagate):
        """Test track_prompt_version with explicitly provided version."""
        mock_context = MagicMock()
        mock_propagate.return_value.__enter__ = Mock(return_value=None)
        mock_propagate.return_value.__exit__ = Mock(return_value=None)

        @track_prompt_version(prompt_id="test-prompt", version="v3.0")
        def test_func():
            return "done"

        result = test_func()
        
        assert result == "done"
        # Verify propagate_attributes was called with correct metadata
        mock_propagate.assert_called_once()
        call_kwargs = mock_propagate.call_args[1]
        assert call_kwargs["metadata"]["prompt_id"] == "test-prompt"
        assert call_kwargs["metadata"]["prompt_version"] == "v3.0"

    @patch('src.observability.decorators.get_active_prompt_version')
    @patch('src.observability.decorators.propagate_attributes')
    def test_track_prompt_version_auto_fetches_version(
        self, mock_propagate, mock_get_active_version
    ):
        """Test track_prompt_version auto-fetches version when not specified."""
        # Setup mocks
        mock_context = MagicMock()
        mock_propagate.return_value.__enter__ = Mock(return_value=None)
        mock_propagate.return_value.__exit__ = Mock(return_value=None)
        mock_get_active_version.return_value = "auto-version-1.0"

        @track_prompt_version(prompt_id="auto-prompt", version=None)
        def test_func():
            return "auto-result"

        result = test_func()
        
        assert result == "auto-result"
        # Verify get_active_prompt_version was called
        mock_get_active_version.assert_called_once_with("auto-prompt")
        # Verify propagate_attributes was called with fetched version
        mock_propagate.assert_called_once()
        call_kwargs = mock_propagate.call_args[1]
        assert call_kwargs["metadata"]["prompt_id"] == "auto-prompt"
        assert call_kwargs["metadata"]["prompt_version"] == "auto-version-1.0"

    @patch('src.observability.decorators.get_active_prompt_version')
    @patch('src.observability.decorators.propagate_attributes')
    def test_track_prompt_version_default_parameter(
        self, mock_propagate, mock_get_active_version
    ):
        """Test track_prompt_version with default version parameter (None)."""
        mock_context = MagicMock()
        mock_propagate.return_value.__enter__ = Mock(return_value=None)
        mock_propagate.return_value.__exit__ = Mock(return_value=None)
        mock_get_active_version.return_value = "default-v2.0"

        # When version is not provided, it defaults to None
        @track_prompt_version(prompt_id="default-prompt")
        def test_func():
            return "default-result"

        result = test_func()
        
        assert result == "default-result"
        mock_get_active_version.assert_called_once_with("default-prompt")
        call_kwargs = mock_propagate.call_args[1]
        assert call_kwargs["metadata"]["prompt_version"] == "default-v2.0"


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

        # Check all decorator attributes are set
        assert hasattr(multi_decorated_func, '_langfuse_session')
        assert hasattr(multi_decorated_func, '_langfuse_prompt_id')
        assert hasattr(multi_decorated_func, '_langfuse_observed')

        # Verify functionality
        result = multi_decorated_func(5)
        assert result == 15

    def test_decorator_with_real_session_flow(self):
        """Test decorator in realistic session flow."""
        # Start session
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

    def test_observe_tool_with_empty_session(self):
        """Test observe_tool when session exists but has no session_id."""
        # Manually set incomplete session
        from src.observability.session import _session_context
        _session_context.set({"user_id": "user-only"})

        @observe_tool(name="incomplete_session_tool")
        def test_func():
            return "ok"

        # Should not raise error
        result = test_func()
        assert result == "ok"

    def test_observe_tool_with_exception(self):
        """Test observe_tool when decorated function raises exception."""
        @observe_tool(name="failing_tool")
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_func()

    def test_nested_session_contexts(self):
        """Test nested session context changes."""
        @observe_tool(name="outer_tool")
        def outer_func():
            set_session(session_id="outer-session", user_id="outer-user")
            
            @observe_tool(name="inner_tool")
            def inner_func():
                return SessionManager.get_session_id()
            
            return inner_func()

        result = outer_func()
        assert result == "outer-session"
