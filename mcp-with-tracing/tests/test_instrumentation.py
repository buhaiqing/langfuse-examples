"""
Tests for observability instrumentation.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.observability.config import ObservabilityConfig
from src.observability.instrumentation import (
    init_observability,
    get_langfuse_client,
    set_session_context,
    get_session_context,
    clear_session_context,
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
        config = ObservabilityConfig()
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

    def test_init_observability_disabled(self):
        """Test initialization with disabled observability."""
        config = ObservabilityConfig(enabled=False)
        result = init_observability(config)
        assert result is None
        assert get_langfuse_client() is None

    def test_init_observability_no_credentials(self):
        """Test initialization without credentials."""
        config = ObservabilityConfig()
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

    def test_session_context(self):
        """Test session context management."""
        set_session_context("session-123", "user-456")
        ctx = get_session_context()

        assert ctx["session_id"] == "session-123"
        assert ctx["user_id"] == "user-456"

        clear_session_context()
        ctx = get_session_context()
        assert ctx == {}


class TestDecorators:
    """Tests for decorators."""

    def test_observe_tool_decorator(self):
        """Test observe_tool decorator."""

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

        @track_prompt_version("prompt-1", "v1.0")
        def test_func() -> str:
            return "result"

        result = test_func()
        assert result == "result"
