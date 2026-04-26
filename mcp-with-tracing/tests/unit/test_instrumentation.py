"""
Tests for observability instrumentation.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.observability.config import ObservabilityConfig
from src.observability.instrumentation import (
    init_observability,
    get_langfuse_client,
)
from src.observability.session import (
    SessionManager,
    set_session,
    clear_session,
)
from src.observability.decorators import (
    observe_tool,
    track_session,
    track_prompt_version,
)


class TestObservabilityConfig:
    """Tests for ObservabilityConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ObservabilityConfig()

        assert config.enabled is True
        assert config.sampling_rate == 1.0
        assert config.langfuse_host == "https://cloud.langfuse.com"

    def test_is_configured_empty(self):
        """Test is_configured with empty credentials."""
        config = ObservabilityConfig(langfuse_public_key="", langfuse_secret_key="")
        assert config.is_configured() is False

    def test_is_configured_with_keys(self):
        """Test is_configured with credentials."""
        config = ObservabilityConfig(
            langfuse_public_key="pk-test",
            langfuse_secret_key="sk-test",
        )
        assert config.is_configured() is True

    def test_sampling_rate_validation(self):
        """Test sampling rate validation."""
        with pytest.raises(Exception):
            ObservabilityConfig(sampling_rate=1.5)

        with pytest.raises(Exception):
            ObservabilityConfig(sampling_rate=-0.1)


class TestInstrumentation:
    """Tests for instrumentation module."""

    def setup_method(self):
        import src.observability.instrumentation as mod
        mod._langfuse_client = None

    def teardown_method(self):
        import src.observability.instrumentation as mod
        mod._langfuse_client = None

    def test_init_observability_disabled(self):
        """Test initialization with disabled observability."""
        config = ObservabilityConfig(enabled=False)
        result = init_observability(config)
        assert result is None
        assert get_langfuse_client() is None

    def test_init_observability_no_credentials(self):
        """Test initialization without credentials."""
        config = ObservabilityConfig(
            langfuse_public_key="",
            langfuse_secret_key="",
            enabled=True,
        )
        result = init_observability(config)
        assert result is None

    @patch("src.observability.instrumentation.Langfuse")
    def test_init_observability_success(self, mock_langfuse):
        """Test successful initialization."""
        config = ObservabilityConfig(
            langfuse_public_key="pk-test",
            langfuse_secret_key="sk-test",
        )

        mock_client = MagicMock()
        mock_langfuse.return_value = mock_client

        result = init_observability(config)

        assert result is mock_client
        assert get_langfuse_client() is mock_client
        mock_langfuse.assert_called_once()

    @patch("src.observability.instrumentation.Langfuse")
    def test_get_langfuse_client_returns_shared_instance(self, mock_langfuse):
        """Test get_langfuse_client returns the same shared instance."""
        mock_client = MagicMock()
        mock_langfuse.return_value = mock_client

        config = ObservabilityConfig(
            langfuse_public_key="pk-test",
            langfuse_secret_key="sk-test",
        )
        init_observability(config)

        client1 = get_langfuse_client()
        client2 = get_langfuse_client()

        assert client1 is client2
        assert client1 is mock_client

    def test_session_context(self):
        """Test session context management."""
        set_session(session_id="session-123", user_id="user-456")
        ctx = SessionManager.get_session()

        assert ctx["session_id"] == "session-123"
        assert ctx["user_id"] == "user-456"

        clear_session()
        ctx = SessionManager.get_session()
        assert ctx == {}


class TestDecorators:
    """Tests for decorators."""

    def test_observe_tool_decorator(self):
        """Test observe_tool decorator."""

        with patch("src.observability.decorators.get_langfuse_client", return_value=None):
            @observe_tool(name="test_tool")
            def test_func(x: int) -> int:
                return x * 2

            result = test_func(5)
            assert result == 10

    def test_track_session_decorator(self):
        """Test track_session decorator."""

        @track_session("session-123", "user-456")
        def test_func() -> str:
            return "hello"

        result = test_func()
        assert result == "hello"

    def test_track_prompt_version_decorator(self):
        """Test track_prompt_version decorator."""

        with patch("src.observability.decorators.get_langfuse_client", return_value=None):
            @track_prompt_version("prompt-1", "v1.0")
            def test_func() -> str:
                return "result"

            result = test_func()
            assert result == "result"
