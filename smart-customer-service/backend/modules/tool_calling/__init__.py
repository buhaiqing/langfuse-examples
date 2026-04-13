"""Tool calling module with API client and tool implementations"""

from modules.tool_calling.api_client import APIClient, CircuitBreakerError

__all__ = ["APIClient", "CircuitBreakerError"]
