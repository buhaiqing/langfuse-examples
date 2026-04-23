# CI/CD Integration Tests

"""Tests for CI/CD integration with correlation layer."""

import os
import pytest


class TestCIIntegration:
    """Test CI integration with correlation layer."""

    def test_ci_trace_context_from_env(self):
        """Test CI trace ID context from environment variables."""
        # Arrange
        os.environ["GITHUB_RUN_ID"] = "123456"
        os.environ["GITHUB_ACTIONS"] = "true"

        # Act
        from skill_observability_toolkit.ci.context import set_ci_context_from_env
        context = set_ci_context_from_env()

        # Assert
        assert context.get("trace_id") == "123456"
        assert context.get("ci") == "github_actions"