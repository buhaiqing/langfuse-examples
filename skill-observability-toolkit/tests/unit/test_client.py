"""
Tests for Langfuse Client.

This module tests the LangfuseClient wrapper and integration with STOP Protocol.
"""

import os
from unittest.mock import Mock, patch

import pytest

from skill_observability_toolkit.langfuse_integration.client import LangfuseClient
from skill_observability_toolkit.langfuse_integration.context import (
    get_trace_id,
    set_trace_id,
)


class TestLangfuseClient:
    """Tests for LangfuseClient class."""

    def test_get_instance_returns_client_when_configured(self):
        """Test get_instance returns Langfuse client when configured."""
        with patch.dict(os.environ, {
            "LANGFUSE_PUBLIC_KEY": "test_public_key",
            "LANGFUSE_SECRET_KEY": "test_secret_key",
        }):
            with patch("skill_observability_toolkit.langfuse_integration.client.Langfuse") as mock_langfuse_class:
                mock_langfuse = Mock()
                mock_langfuse_class.return_value = mock_langfuse

                client = LangfuseClient.get_instance()

                assert client is not None
                mock_langfuse_class.assert_called_once()

    def test_get_instance_returns_none_when_not_configured(self):
        """Test get_instance returns None when not configured."""
        with patch.dict(os.environ, {
            "LANGFUSE_PUBLIC_KEY": "",
            "LANGFUSE_SECRET_KEY": "",
        }, clear=True):
            # Reset singleton instance to ensure fresh state
            LangfuseClient._instance = None
            LangfuseClient._langfuse = None
            client = LangfuseClient.get_instance()
            assert client is None

    def test_is_available_returns_true_when_configured(self):
        """Test is_available returns True when configured."""
        with patch.dict(os.environ, {
            "LANGFUSE_PUBLIC_KEY": "test_public_key",
            "LANGFUSE_SECRET_KEY": "test_secret_key",
        }):
            with patch("skill_observability_toolkit.langfuse_integration.client.Langfuse"):
                assert LangfuseClient.is_available() is True

    def test_is_available_returns_false_when_not_configured(self):
        """Test is_available returns False when not configured."""
        with patch.dict(os.environ, {
            "LANGFUSE_PUBLIC_KEY": "",
            "LANGFUSE_SECRET_KEY": "",
        }, clear=True):
            assert LangfuseClient.is_available() is False

    def test_start_trace_generates_new_id_when_not_provided(self):
        """Test start_trace generates new trace ID when not provided."""
        with patch.dict(os.environ, {
            "LANGFUSE_PUBLIC_KEY": "test_public_key",
            "LANGFUSE_SECRET_KEY": "test_secret_key",
        }):
            with patch("skill_observability_toolkit.langfuse_integration.client.Langfuse"):
                with patch("uuid.uuid4") as mock_uuid:
                    mock_uuid.return_value.hex = "test1234test5678test9012"

                    trace_id = LangfuseClient.start_trace(name="test_skill")

                    assert trace_id is not None
                    assert "skill_trace_" in trace_id
                    assert "test1234" in trace_id

    def test_start_trace_uses_provided_trace_id(self):
        """Test start_trace uses provided trace ID."""
        with patch.dict(os.environ, {
            "LANGFUSE_PUBLIC_KEY": "test_public_key",
            "LANGFUSE_SECRET_KEY": "test_secret_key",
        }):
            with patch("skill_observability_toolkit.langfuse_integration.client.Langfuse"):
                custom_trace_id = "custom_trace_123"

                trace_id = LangfuseClient.start_trace(
                    trace_id=custom_trace_id,
                    name="test_skill"
                )

                assert trace_id == custom_trace_id

    def test_set_get_trace_id(self):
        """Test setting and getting trace ID."""
        set_trace_id("test_trace_123")
        assert get_trace_id() == "test_trace_123"

    def test_clear_trace_context(self):
        """Test clearing trace context."""
        LangfuseClient.set_trace_id("test_trace_123")

        LangfuseClient.clear_trace_context()

        assert LangfuseClient.get_trace_id() is None

    def test_score_trace_when_client_available(self):
        """Test scoring trace when Langfuse client is available."""
        with patch.dict(os.environ, {
            "LANGFUSE_PUBLIC_KEY": "test_public_key",
            "LANGFUSE_SECRET_KEY": "test_secret_key",
        }):
            with patch("skill_observability_toolkit.langfuse_integration.client.Langfuse"):
                with patch.object(LangfuseClient, 'get_trace_id', return_value="test_trace"):
                    with patch("skill_observability_toolkit.core.get_trace_context") as mock_get_ctx:
                        mock_ctx = Mock()
                        mock_span = Mock()
                        mock_ctx.get_current_span.return_value = mock_span
                        mock_get_ctx.return_value = mock_ctx

                        result = LangfuseClient.score_trace(
                            name="test_score",
                            value=0.95,
                            data_type="NUMERIC",
                        )

                        assert result is True
                        mock_span.score.assert_called_once()


class TestTraceContextIntegration:
    """Tests for trace context integration with Langfuse."""

    def test_trace_id_propagation(self):
        """Test that trace ID is properly propagated in context."""
        LangfuseClient.set_trace_id("trace_abc123")
        trace_id = LangfuseClient.get_trace_id()
        assert trace_id == "trace_abc123"

    def test_parent_trace_id_for_correlation(self):
        """Test parent trace ID for cross-layer correlation."""
        LangfuseClient.set_parent_trace_id("parent_trace_xyz")
        parent_id = LangfuseClient.get_parent_trace_id()
        assert parent_id == "parent_trace_xyz"

    def test_context_cleanup(self):
        """Test complete context cleanup."""
        LangfuseClient.set_trace_id("trace_123")
        LangfuseClient.set_parent_trace_id("parent_456")

        LangfuseClient.clear_trace_context()

        assert LangfuseClient.get_trace_id() is None
        assert LangfuseClient.get_parent_trace_id() is None

    def test_singleton_pattern(self):
        """Test that LangfuseClient follows singleton pattern."""
        client1 = LangfuseClient()
        client2 = LangfuseClient()
        assert client1 is client2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
