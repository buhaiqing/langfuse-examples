"""
Unified Configuration Management.

Centralizes all environment variable and configuration settings
for the Skill Observability Toolkit.
"""

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilityConfig(BaseSettings):
    """
    Unified configuration for Skill Observability Toolkit.

    Consolidates all environment variables and settings into a single
    configuration object with validation and type safety.

    Attributes:
        langfuse_public_key: Langfuse public API key
        langfuse_secret_key: Langfuse secret API key
        langfuse_host: Langfuse server host URL
        enable_tracing: Global tracing enable/disable flag
        trace_output_path: Optional file path for NDJSON trace output
        ci_platform: Detected CI platform name
        ci_trace_id: CI pipeline trace ID
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """

    # Langfuse Configuration
    langfuse_public_key: str = Field(default="", description="Langfuse public API key")
    langfuse_secret_key: str = Field(default="", description="Langfuse secret API key")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        description="Langfuse server host URL",
    )

    # Tracing Configuration
    enable_tracing: bool = Field(
        default=True,
        description="Global flag to enable/disable tracing",
    )
    trace_output_path: str | None = Field(
        default=None,
        description="Optional file path for NDJSON trace output",
    )

    # CI Environment Configuration (auto-detected)
    ci_platform: str = Field(
        default="unknown",
        description="Detected CI platform (github_actions, gitlab_ci, other)",
    )
    ci_trace_id: str | None = Field(
        default=None,
        description="CI pipeline trace ID for correlation",
    )

    # Logging Configuration
    log_level: str = Field(
        default="WARNING",
        description="Logging level",
    )

    model_config = SettingsConfigDict(
        env_prefix="",  # Read directly from environment variables
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # Allow additional environment variables
    )

    def is_langfuse_enabled(self) -> bool:
        """Check if Langfuse integration is properly configured."""
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    def detect_ci_environment(self) -> dict[str, str | None]:
        """
        Auto-detect CI environment and update configuration.

        Returns:
            Dictionary of detected CI environment variables
        """
        ci_env = {}

        # GitHub Actions detection
        if os.getenv("GITHUB_ACTIONS") == "true":
            self.ci_platform = "github_actions"
            self.ci_trace_id = os.getenv("GITHUB_RUN_ID")
            ci_env.update({
                "ci_platform": "github_actions",
                "ci_workflow": os.getenv("GITHUB_WORKFLOW"),
                "ci_job": os.getenv("GITHUB_JOB"),
                "ci_run_number": os.getenv("GITHUB_RUN_NUMBER"),
                "ci_actor": os.getenv("GITHUB_ACTOR"),
                "ci_repository": os.getenv("GITHUB_REPOSITORY"),
                "ci_sha": os.getenv("GITHUB_SHA"),
            })

        # GitLab CI detection
        elif os.getenv("GITLAB_CI") == "true":
            self.ci_platform = "gitlab_ci"
            self.ci_trace_id = os.getenv("CI_PIPELINE_ID")
            ci_env.update({
                "ci_platform": "gitlab_ci",
                "ci_pipeline": os.getenv("CI_PIPELINE_IID"),
                "ci_job": os.getenv("CI_JOB_NAME"),
                "ci_stage": os.getenv("CI_JOB_STAGE"),
                "ci_sha": os.getenv("CI_COMMIT_SHA"),
            })

        return ci_env


# Global configuration instance
_config: ObservabilityConfig | None = None


def get_config() -> ObservabilityConfig:
    """
    Get the global configuration instance.

    Returns:
        ObservabilityConfig instance (singleton)
    """
    global _config
    if _config is None:
        _config = ObservabilityConfig()
        # Auto-detect CI environment on first access
        _config.detect_ci_environment()
    return _config


def reload_config() -> ObservabilityConfig:
    """
    Reload configuration from environment variables.

    Useful when environment variables change during runtime.

    Returns:
        New ObservabilityConfig instance
    """
    global _config
    _config = ObservabilityConfig()
    _config.detect_ci_environment()
    return _config


def validate_config() -> list[str]:
    """
    Validate configuration and return any issues.

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    config = get_config()

    # Validate Langfuse configuration if tracing is enabled
    if config.enable_tracing:
        if not config.langfuse_public_key:
            errors.append(
                "LANGFUSE_PUBLIC_KEY not set. Tracing will be disabled. "
                "Set environment variable or disable tracing with ENABLE_TRACING=false"
            )
        if not config.langfuse_secret_key:
            errors.append(
                "LANGFUSE_SECRET_KEY not set. Tracing will be disabled. "
                "Set environment variable or disable tracing with ENABLE_TRACING=false"
            )

    # Validate log level
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if config.log_level.upper() not in valid_log_levels:
        errors.append(
            f"Invalid LOG_LEVEL '{config.log_level}'. "
            f"Must be one of: {', '.join(valid_log_levels)}"
        )

    # Validate trace output path if specified
    if config.trace_output_path:
        path = Path(config.trace_output_path)
        if not path.parent.exists():
            errors.append(
                f"Trace output directory does not exist: {path.parent}"
            )

    return errors