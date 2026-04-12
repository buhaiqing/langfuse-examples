"""
Langfuse client initialization and configuration
"""

from langfuse import Langfuse

from config.settings import (
    ENVIRONMENT,
    LANGFUSE_FLUSH_AT,
    LANGFUSE_FLUSH_INTERVAL,
    LANGFUSE_HOST,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    RELEASE_VERSION,
    validate_config,
)
from utils.data_masking import mask_sensitive_data

# Validate configuration before initialization
validate_config()

# Initialize Langfuse client with global masking
langfuse = Langfuse(
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY,
    host=LANGFUSE_HOST,
    environment=ENVIRONMENT,
    release=RELEASE_VERSION,
    mask=mask_sensitive_data,  # Global sensitive data masking
    flush_at=LANGFUSE_FLUSH_AT,
    flush_interval=LANGFUSE_FLUSH_INTERVAL,
    debug=False,  # Set to True for detailed logging during development
)


def get_langfuse_client() -> Langfuse:
    """
    Get the configured Langfuse client instance

    Returns:
        Configured Langfuse client
    """
    return langfuse


def flush_traces():
    """
    Flush all pending traces to Langfuse.
    Call this before application shutdown to ensure all data is sent.
    """
    langfuse.flush()
    print("All traces flushed to Langfuse")


# Export the client for easy import
__all__ = ["langfuse", "get_langfuse_client", "flush_traces"]
