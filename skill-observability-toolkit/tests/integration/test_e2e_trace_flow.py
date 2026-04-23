"""
End-to-End Integration Tests for Skill Observability Toolkit.

Tests the complete flow from CI pipeline -> Skill execution -> Langfuse integration.
"""

import os
import tempfile
from pathlib import Path

import pytest

from skill_observability_toolkit.config import get_config, reload_config
from skill_observability_toolkit.ci.decorators import trace_ci_step
from skill_observability_toolkit.stop.tracer import STOPTracer, trace_skill_execution
from skill_observability_toolkit.correlation.correlation import correlate_traces


class TestEndToEndTraceFlow:
    """Test complete trace flow from CI to Langfuse."""

    def test_ci_to_skill_trace_correlation(self, tmp_path: Path):
        """Test correlation between CI trace and Skill trace."""
        # Setup: Create temporary trace output
        trace_file = tmp_path / "trace.ndjson"

        # Simulate CI environment
        os.environ["GITHUB_ACTIONS"] = "true"
        os.environ["GITHUB_RUN_ID"] = "ci_build_12345"
        os.environ["GITHUB_WORKFLOW"] = "test-workflow"

        # Reload config to detect CI environment
        config = reload_config()
        assert config.ci_platform == "github_actions"
        assert config.ci_trace_id == "ci_build_12345"

        # Step 1: Start CI-level trace
        @trace_ci_step(step_name="build", step_type="build", auto_capture_env=True)
        def build_step():
            """Simulate CI build step."""
            return {"status": "success", "artifact": "dist.tar.gz"}

        # Execute build step
        result = build_step()
        assert result["status"] == "success"

        # Step 2: Execute skill within CI context
        @trace_skill_execution(skill_name="test-skill", version="1.0.0")
        def execute_skill():
            """Simulate skill execution."""
            tracer = STOPTracer(output_path=str(trace_file))
            tracer.start_trace(name="skill:test-skill")

            with tracer.start_span("operation1") as span:
                span.end(output={"result": "step1_complete"})

            with tracer.start_span("operation2") as span:
                span.end(output={"result": "step2_complete"})

            tracer.end_trace(status="success")
            return {"skill_result": "success"}

        # Execute skill
        skill_result = execute_skill()
        assert skill_result["skill_result"] == "success"

        # Step 3: Correlate traces
        correlation = correlate_traces(
            ci_trace_id=config.ci_trace_id,
            skill_trace_id="skill_trace_test-skill",
        )

        assert correlation["ci_trace_id"] == "ci_build_12345"
        assert correlation["skill_trace_id"] == "skill_trace_test-skill"
        assert correlation["parent_of_skill"] == "ci_build_12345"

        # Verify trace file was created
        assert trace_file.exists()

    def test_gitlab_ci_environment_detection(self):
        """Test GitLab CI environment auto-detection."""
        # Setup GitLab CI environment
        os.environ["GITLAB_CI"] = "true"
        os.environ["CI_PIPELINE_ID"] = "gitlab_pipeline_98765"
        os.environ["CI_JOB_NAME"] = "deploy"

        # Clean GitHub env
        os.environ.pop("GITHUB_ACTIONS", None)

        # Reload config
        config = reload_config()
        assert config.ci_platform == "gitlab_ci"
        assert config.ci_trace_id == "gitlab_pipeline_98765"

    def test_sensitive_info_filtering(self):
        """Test that sensitive environment variables are filtered."""
        # Setup CI with sensitive tokens (only capture standard CI vars)
        os.environ["GITHUB_ACTIONS"] = "true"
        os.environ["GITHUB_RUN_ID"] = "build_123"
        os.environ["GITHUB_TOKEN"] = "ghp_supersecret123456"

        from skill_observability_toolkit.ci.decorators import _capture_ci_environment

        # Capture CI environment
        ci_env = _capture_ci_environment()

        # Verify sensitive values are redacted
        assert ci_env.get("GITHUB_TOKEN") == "***REDACTED***"
        assert ci_env.get("ci_trace_id") == "build_123"  # Safe value kept
        assert ci_env.get("ci") == "github_actions"  # Safe value kept

    def test_span_propagation_across_layers(self):
        """Test span propagation from CI to Skill to nested operations."""
        tracer = STOPTracer()
        tracer.start_trace(trace_id="test_correlation_flow")

        # Level 1: CI root span
        with tracer.start_span("ci_build") as ci_span:
            ci_span.set_metadata(ci_platform="github_actions")

            # Level 2: Skill execution span
            with tracer.start_span("skill_execution") as skill_span:
                skill_span.set_metadata(skill_name="test-skill")

                # Level 3: Nested operation
                with tracer.start_span("model_inference") as inference_span:
                    inference_span.score("accuracy", 0.95)
                    inference_span.end(output={"prediction": "positive"})

                skill_span.end(output={"skill_result": "completed"})

            ci_span.end(status="success")

        trace_data = tracer.end_trace()

        # Verify span hierarchy
        assert len(trace_data["spans"]) == 4  # root + ci + skill + inference

        # Verify parent-child relationships
        spans = trace_data["spans"]
        root_span = spans[0]
        ci_span = spans[1]
        skill_span = spans[2]
        inference_span = spans[3]

        assert ci_span["parent_span_id"] == root_span["span_id"]
        assert skill_span["parent_span_id"] == ci_span["span_id"]
        assert inference_span["parent_span_id"] == skill_span["span_id"]


class TestLangfuseIntegration:
    """Test Langfuse client integration."""

    def test_langfuse_config_validation(self):
        """Test configuration validation for Langfuse."""
        # Test missing keys
        os.environ["LANGFUSE_PUBLIC_KEY"] = ""
        os.environ["LANGFUSE_SECRET_KEY"] = ""
        os.environ["ENABLE_TRACING"] = "true"

        config = reload_config()
        assert not config.is_langfuse_enabled()

        # Test valid config
        os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-test-123"
        os.environ["LANGFUSE_SECRET_KEY"] = "sk-test-456"

        config = reload_config()
        assert config.is_langfuse_enabled()

    def test_langfuse_client_singleton(self):
        """Test Langfuse client singleton behavior."""
        from skill_observability_toolkit.langfuse_integration.client import LangfuseClient

        # Get two instances
        client1 = LangfuseClient()
        client2 = LangfuseClient()

        # Verify same instance
        assert client1 is client2


class TestConfigurationManagement:
    """Test unified configuration management."""

    def test_config_env_file_loading(self, tmp_path: Path):
        """Test loading configuration from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("""
LANGFUSE_PUBLIC_KEY=pk-file-123
LANGFUSE_SECRET_KEY=sk-file-456
ENABLE_TRACING=true
LOG_LEVEL=INFO
""")

        # Set env file path
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        config = reload_config()
        assert config.langfuse_public_key == "pk-file-123"
        assert config.log_level == "INFO"

        os.chdir(original_cwd)

    def test_config_validation_errors(self):
        """Test configuration validation."""
        from skill_observability_toolkit.config import validate_config

        # Setup invalid config
        os.environ["LANGFUSE_PUBLIC_KEY"] = ""
        os.environ["LANGFUSE_SECRET_KEY"] = ""
        os.environ["ENABLE_TRACING"] = "true"

        reload_config()
        errors = validate_config()

        assert len(errors) > 0
        assert any("LANGFUSE_PUBLIC_KEY" in e for e in errors)


class TestCrossLayerCorrelation:
    """Test cross-layer trace correlation."""

    def test_trace_correlation_tree(self):
        """Test building correlation tree across layers."""
        from skill_observability_toolkit.correlation.correlation import (
            TraceCorrelator,
            start_trace,
            start_span,
        )

        correlator = TraceCorrelator()

        # Start CI trace
        ci_trace_id = correlator.start_trace(
            trace_id="ci_pipeline_001",
            name="CI Pipeline",
            layer="ci",
        )

        # Start skill trace linked to CI
        skill_trace_id = correlator.start_trace(
            trace_id="skill_trace_001",
            name="Skill Execution",
            layer="skill",
        )

        # Correlate
        correlation = correlator.correlate_traces(
            ci_trace_id=ci_trace_id,
            skill_trace_id=skill_trace_id,
        )

        assert correlation["parent_of_skill"] == ci_trace_id

        # Get correlation tree
        tree = correlator.get_correlation_tree()
        assert len(tree["traces"]) == 2


class TestManifestIntegration:
    """Test skill manifest integration with tracing."""

    def test_manifest_to_trace_integration(self, tmp_path: Path):
        """Test executing skill from manifest with tracing."""
        # Create skill.yaml
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
name: test-skill
version: 1.0.0
sop: "Test skill SOP"
description: "Test skill for integration testing"

inputs:
  - name: query
    type: string
    description: "User query"
    required: true

outputs:
  - name: response
    type: string
    description: "Model response"

assertions:
  pre:
    - check: input_valid
      message: "Input must be valid"
  post:
    - check: output_not_empty
      message: "Output must not be empty"

trust_score:
  enabled: true
  min_pass_rate: 0.8
""")

        from skill_observability_toolkit.stop.manifest import ManifestParser

        # Parse manifest
        parser = ManifestParser(str(skill_yaml))
        manifest = parser.parse()

        assert manifest.name == "test-skill"

        # Execute skill with tracing
        tracer = STOPTracer()
        tracer.start_trace(trace_id=manifest.name)

        with tracer.start_span("skill_execution") as span:
            span.set_metadata(skill_version=manifest.version)
            span.end(output={"response": "test response"})

        trace_data = tracer.end_trace()

        assert trace_data["trace_id"] == "test-skill"
        assert len(trace_data["spans"]) == 2


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_env():
    """Clean up environment variables after each test."""
    yield

    # Remove test environment variables
    test_env_vars = [
        "GITHUB_ACTIONS", "GITHUB_RUN_ID", "GITHUB_WORKFLOW",
        "GITLAB_CI", "CI_PIPELINE_ID", "CI_JOB_NAME",
        "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY",
        "ENABLE_TRACING", "LOG_LEVEL",
    ]
    for var in test_env_vars:
        os.environ.pop(var, None)