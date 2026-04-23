"""
CI/CD Tracing Decorators.

This module provides decorators for tracing CI/CD pipeline steps
with support for GitHub Actions and GitLab CI.
"""

import functools
import os
import time
from collections.abc import Callable
from typing import Any

from skill_observability_toolkit.langfuse_integration.client import LangfuseClient
from skill_observability_toolkit.langfuse_integration.context import (
    get_trace_id,
    set_parent_trace_id,
)


def trace_ci_step(
    step_name: str,
    step_type: str = "unknown",
    trace_id: str | None = None,
    auto_capture_env: bool = True,
):
    """
    Decorator for tracing CI/CD pipeline steps.

    Args:
        step_name: Name of the CI step (e.g., "install", "build", "test")
        step_type: Type of step (build, test, deploy, etc.)
        trace_id: Optional trace ID (if None, uses current context)
        auto_capture_env: Whether to auto capture CI environment variables

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            client = LangfuseClient.get_instance()
            ci_env = _capture_ci_environment() if auto_capture_env else {}

            # Generate or use provided trace ID
            current_trace_id = trace_id or get_trace_id()
            if not current_trace_id:
                import uuid
                current_trace_id = f"ci_build_{uuid.uuid4().hex[:12]}"

            # Set parent trace ID for cross-layer correlation
            if ci_env.get("ci_trace_id"):
                set_parent_trace_id(ci_env["ci_trace_id"])

            start_time = time.time()

            try:
                # Execute step
                result = func(*args, **kwargs)

                duration_ms = (time.time() - start_time) * 1000

                # Score trace if Langfuse available
                if client:
                    client.score_trace(
                        name=f"ci_{step_name}_duration_ms",
                        value=duration_ms,
                        comment=f"CI Step {step_name} execution time",
                    )
                    client.score_trace(
                        name=f"ci_{step_name}_success",
                        value=1,
                        data_type="BOOLEAN",
                    )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                # Score trace with error
                if client:
                    client.score_trace(
                        name=f"ci_{step_name}_success",
                        value=0,
                        data_type="BOOLEAN",
                    )
                    client.score_trace(
                        name=f"ci_{step_name}_error",
                        value=str(e),
                        data_type="CATEGORICAL",
                    )

                raise

            finally:
                # Optionally end trace (depends on use case)
                # For pipeline-level tracing, might want to keep trace open
                pass

        return wrapper
    return decorator


def trace_ci_stage(
    stage_name: str,
    trace_id: str | None = None,
    auto_capture_env: bool = True,
):
    """
    Decorator for tracing CI/CD pipeline stages (collection of steps).

    Args:
        stage_name: Name of the stage (e.g., "build", "test", "deploy")
        trace_id: Optional trace ID
        auto_capture_env: Whether to auto capture CI environment

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            client = LangfuseClient.get_instance()
            _capture_ci_environment() if auto_capture_env else {}

            current_trace_id = trace_id or get_trace_id()
            if not current_trace_id:
                import uuid
                current_trace_id = f"ci_stage_{uuid.uuid4().hex[:12]}"

            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                duration_ms = (time.time() - start_time) * 1000

                if client:
                    client.score_trace(
                        name=f"ci_stage_{stage_name}_duration_ms",
                        value=duration_ms,
                        comment=f"CI Stage {stage_name} execution time",
                    )
                    client.score_trace(
                        name=f"ci_stage_{stage_name}_success",
                        value=1,
                        data_type="BOOLEAN",
                    )

                return result

            except Exception:
                duration_ms = (time.time() - start_time) * 1000

                if client:
                    client.score_trace(
                        name=f"ci_stage_{stage_name}_success",
                        value=0,
                        data_type="BOOLEAN",
                    )

                raise

        return wrapper
    return decorator


def trace_ci_job(
    job_name: str,
    trace_id: str | None = None,
    auto_capture_env: bool = True,
):
    """
    Decorator for tracing CI/CD pipeline jobs.

    Args:
        job_name: Name of the job
        trace_id: Optional trace ID
        auto_capture_env: Whether to auto capture CI environment

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            client = LangfuseClient.get_instance()

            current_trace_id = trace_id or get_trace_id()
            if not current_trace_id:
                import uuid
                current_trace_id = f"ci_job_{uuid.uuid4().hex[:12]}"

            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                duration_ms = (time.time() - start_time) * 1000

                if client:
                    client.score_trace(
                        name=f"ci_job_{job_name}_duration_ms",
                        value=duration_ms,
                        comment=f"CI Job {job_name} execution time",
                    )
                    client.score_trace(
                        name=f"ci_job_{job_name}_success",
                        value=1,
                        data_type="BOOLEAN",
                    )

                return result

            except Exception:
                duration_ms = (time.time() - start_time) * 1000

                if client:
                    client.score_trace(
                        name=f"ci_job_{job_name}_success",
                        value=0,
                        data_type="BOOLEAN",
                    )

                raise

        return wrapper
    return decorator


def _capture_ci_environment() -> dict[str, Any]:
    """
    Capture CI environment variables.

    Returns:
        Dictionary of CI environment variables
    """
    # Sensitive environment variable patterns to filter
    SENSITIVE_ENV_PATTERNS = [
        "TOKEN", "SECRET", "KEY", "PASSWORD", "CREDENTIAL",
        "AWS_ACCESS", "AWS_SECRET", "PRIVATE", "AUTH",
    ]

    env_vars = {}

    # GitHub Actions
    if os.getenv("GITHUB_ACTIONS") == "true":
        env_vars.update({
            "ci": "github_actions",
            "ci_trace_id": os.getenv("GITHUB_RUN_ID"),
            "ci_workflow": os.getenv("GITHUB_WORKFLOW"),
            "ci_job": os.getenv("GITHUB_JOB"),
            "ci_step": os.getenv("GITHUB_STEP"),
            "ci_run_number": os.getenv("GITHUB_RUN_NUMBER"),
            "ci_run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
            "ci_actor": os.getenv("GITHUB_ACTOR"),
            "ci_repository": os.getenv("GITHUB_REPOSITORY"),
            "ci_ref": os.getenv("GITHUB_REF"),
            "ci_sha": os.getenv("GITHUB_SHA"),
            # Capture potentially sensitive vars for filtering
            "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN"),
        })

    # GitLab CI
    elif os.getenv("GITLAB_CI") == "true":
        env_vars.update({
            "ci": "gitlab_ci",
            "ci_trace_id": os.getenv("CI_PIPELINE_ID"),
            "ci_pipeline": os.getenv("CI_PIPELINE_IID"),
            "ci_job": os.getenv("CI_JOB_NAME"),
            "ci_job_id": os.getenv("CI_JOB_ID"),
            "ci_stage": os.getenv("CI_JOB_STAGE"),
            "ci_ref": os.getenv("CI_COMMIT_REF_NAME"),
            "ci_sha": os.getenv("CI_COMMIT_SHA"),
            "ci_user_name": os.getenv("CI_USER_NAME"),
            "ci_user_email": os.getenv("CI_USER_EMAIL"),
            # Capture potentially sensitive vars for filtering
            "CI_JOB_TOKEN": os.getenv("CI_JOB_TOKEN"),
        })

    # Other CI systems
    else:
        env_vars.update({
            "ci": "other",
            "ci_trace_id": os.getenv("CI_BUILD_ID"),
        })

    # Filter sensitive values (redact tokens, secrets, etc.)
    for key, value in env_vars.items():
        if value and any(pattern in key.upper() for pattern in SENSITIVE_ENV_PATTERNS):
            env_vars[key] = "***REDACTED***"

    # Additional check: filter values that look like secrets
    for key, value in env_vars.items():
        if value and isinstance(value, str):
            # Redact if value looks like a token/secret (long random strings)
            if len(value) > 20 and any(c in value for c in "_-"):
                # Check if it's not a known safe pattern (like SHA, trace_id)
                if not any(safe in key.lower() for safe in ["sha", "trace_id", "run_id", "job_id", "pipeline_id"]):
                    env_vars[key] = "***REDACTED***"

    return env_vars


def is_github_actions() -> bool:
    """Check if running in GitHub Actions."""
    return os.getenv("GITHUB_ACTIONS") == "true"


def is_gitlab_ci() -> bool:
    """Check if running in GitLab CI."""
    return os.getenv("GITLAB_CI") == "true"


def get_ci_platform() -> str:
    """Get current CI platform name."""
    if is_github_actions():
        return "github_actions"
    elif is_gitlab_ci():
        return "gitlab_ci"
    else:
        return "other"
