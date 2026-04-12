"""
Integration tests for Langfuse connection.

Tests verify Langfuse client initialization and basic trace submission.
"""

import pytest
from datetime import datetime
from src.observability.config import ObservabilityConfig
from src.observability.langfuse_client import init_observer, get_observer


@pytest.mark.integration
class TestLangfuseConnection:
    """Integration tests for Langfuse connection."""

    def test_langfuse_connection(self):
        """Test Langfuse client initialization and trace submission."""
        config = ObservabilityConfig()

        # Check configuration
        assert config.is_configured(), "Langfuse credentials not configured"

        # Initialize observer
        observer = init_observer(config)
        assert observer.client is not None, "Langfuse client not initialized"

        # Create test trace
        test_session_id = f"test-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        try:
            with observer.trace_tool_call(
                tool_name="test_echo",
                input_args={"message": "Hello, Langfuse!"},
                session_id=test_session_id,
                user_id="test-user",
                prompt_version="v1.0",
            ) as observation:
                if observation:
                    observation.update(output="Echo: Hello, Langfuse!")

            observer.flush()
            observer.shutdown()

        except Exception as e:
            pytest.fail(f"Failed to submit trace: {e}")
