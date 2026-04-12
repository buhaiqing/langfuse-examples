"""
Pytest configuration and fixtures for Langfuse customer service tests.

This module sets up the test environment before any test imports occur,
ensuring that required environment variables are set to allow module imports
without needing actual Langfuse credentials.
"""

import os
from unittest.mock import MagicMock, Mock

import pytest

# Set environment variables BEFORE any imports that check config
# This must happen at module level, before pytest collects tests
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "test_public_key")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "test_secret_key")
os.environ.setdefault("LANGFUSE_HOST", "https://cloud.langfuse.com")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("RELEASE_VERSION", "v1.0.0-test")
os.environ.setdefault("OPENAI_API_KEY", "test_openai_key")


@pytest.fixture
def mock_langfuse():
    """
    Fixture providing a mocked Langfuse client.

    Returns:
        Mock: A MagicMock object simulating the Langfuse client
    """
    mock = MagicMock()
    mock.update_current_trace = Mock()
    mock.score_current_trace = Mock()
    mock.score_current_span = Mock()
    mock.event = Mock()
    mock.start_span = Mock(return_value=MagicMock())
    mock.flush = Mock()
    return mock


@pytest.fixture
def mock_span():
    """
    Fixture providing a mocked span object.

    Returns:
        Mock: A MagicMock object simulating a Langfuse span
    """
    span = MagicMock()
    span.end = Mock()
    span.score = Mock()
    span.event = Mock()
    return span
