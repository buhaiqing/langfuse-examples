"""
Configuration management for Langfuse observability.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class ObservabilityConfig(BaseSettings):
    """Langfuse observability configuration."""

    langfuse_public_key: str = Field(
        default="",
        description="Langfuse public key",
    )
    langfuse_secret_key: str = Field(
        default="",
        description="Langfuse secret key",
    )
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        description="Langfuse API host",
    )
    enabled: bool = Field(
        default=True,
        description="Enable/disable observability",
    )
    sampling_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Sampling rate (0.0-1.0)",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session ID for tracing",
    )
    user_id: str | None = Field(
        default=None,
        description="Optional user ID for tracing",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def is_configured(self) -> bool:
        """Check if Langfuse credentials are configured."""
        return bool(self.langfuse_public_key and self.langfuse_secret_key)
