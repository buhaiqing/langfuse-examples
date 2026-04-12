"""
Integration tests for success/failure tracking of tool executions.

Tests verify that successful and failed tool calls are properly tracked in Langfuse.
"""

import pytest
from datetime import datetime
from src.observability.config import ObservabilityConfig
from src.observability.langfuse_client import init_observer, get_observer


@pytest.mark.integration
class TestSuccessFailureTracking:
    """Integration tests for success/failure tracking."""

    def test_success_tracking(self):
        """Test successful tool execution tracking."""
        observer = get_observer()
        session_id = f"success-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        try:
            with observer.trace_tool_call(
                tool_name="calculate",
                input_args={"operation": "add", "a": 5, "b": 3},
                session_id=session_id,
                user_id="test-user",
                prompt_version="v1.0",
            ) as observation:
                if observation:
                    result = 5 + 3
                    observation.update(output={"result": result})

            observer.flush()

        except Exception as e:
            pytest.fail(f"Success tracking failed: {e}")

    def test_failure_tracking(self):
        """Test failed tool execution tracking."""
        observer = get_observer()
        session_id = f"failure-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        with pytest.raises(ZeroDivisionError):
            with observer.trace_tool_call(
                tool_name="divide",
                input_args={"operation": "divide", "a": 10, "b": 0},
                session_id=session_id,
                user_id="test-user",
                prompt_version="v1.0",
            ) as observation:
                if observation:
                    result = 10 / 0  # This will raise ZeroDivisionError
                    observation.update(output={"result": result})

        observer.flush()

    def test_error_handling(self):
        """Test error message capture."""
        observer = get_observer()
        session_id = f"error-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        with pytest.raises(ValueError, match="Unknown operation"):
            with observer.trace_tool_call(
                tool_name="invalid_operation",
                input_args={"operation": "unknown", "a": 1},
                session_id=session_id,
                user_id="test-user",
            ) as observation:
                if observation:
                    raise ValueError("Unknown operation: unknown")

        observer.flush()
