"""
Langfuse instrumentation and initialization.

Single source of truth for the Langfuse client instance.
All modules should use get_langfuse_client() to obtain the shared client.
"""

import logging

from langfuse import Langfuse

from src.observability.config import ObservabilityConfig
from src.observability.data_masking import mask_sensitive_data

logger = logging.getLogger(__name__)

_langfuse_client: Langfuse | None = None


def init_observability(config: ObservabilityConfig | None = None) -> Langfuse | None:
    """Initialize the global Langfuse client.

    This is the single entry point for creating a Langfuse client.
    All other modules should call get_langfuse_client() to obtain
    the shared instance instead of creating their own.

    Args:
        config: Optional ObservabilityConfig. If None, loads from env.

    Returns:
        The initialized Langfuse client, or None if disabled/unconfigured.
    """
    global _langfuse_client

    if config is None:
        config = ObservabilityConfig()

    if not config.enabled:
        logger.info("Observability disabled. Skipping Langfuse initialization.")
        _langfuse_client = None
        return None

    if not config.is_configured():
        logger.warning("Langfuse credentials not configured. Observability will be disabled.")
        _langfuse_client = None
        return None

    _langfuse_client = Langfuse(
        public_key=config.langfuse_public_key,
        secret_key=config.langfuse_secret_key,
        host=config.langfuse_host,
        mask=mask_sensitive_data,  # Global PII data masking
    )

    logger.info("Langfuse initialized successfully (host=%s)", config.langfuse_host)
    return _langfuse_client


def get_langfuse_client() -> Langfuse | None:
    """Get the global Langfuse client instance.

    Returns None if observability has not been initialized or is disabled.
    """
    return _langfuse_client
