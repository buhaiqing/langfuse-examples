"""
Langfuse client wrapper for real trace tracking.
"""

from typing import Any, Optional
from contextlib import contextmanager
from datetime import datetime, timezone

from langfuse import Langfuse, propagate_attributes, Langfuse
from src.observability.config import ObservabilityConfig
from src.observability.session import SessionManager
from src.observability.prompt_versioning import get_prompt_version_manager
from langfuse import Langfuse


class LangfuseObserver:
    """Langfuse observer for tracking MCP tool executions."""

    def __init__(self, config: Optional[ObservabilityConfig] = None):
        self.config = config or ObservabilityConfig()
        self.client: Optional[Langfuse] = None

        if self.config.enabled and self.config.is_configured():
            self.client = Langfuse(
                public_key=self.config.langfuse_public_key,
                secret_key=self.config.langfuse_secret_key,
                host=self.config.langfuse_host,
            )
            print(f"Langfuse initialized (host={self.config.langfuse_host})")
        else:
            print("Langfuse disabled or not configured")

    @contextmanager
    def trace_tool_call(
        self,
        tool_name: str,
        input_args: dict[str, Any],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        prompt_version: Optional[str] = None,
    ):
        """Context manager for tracing a tool call."""
        if not self.client:
            yield None
            return

        if session_id:
            SessionManager.set_session(session_id, user_id)

        with SessionManager.propagate_session_ctx():
            with self.client.start_as_current_observation(
                name=tool_name,
                as_type="tool",
                input=input_args,
                metadata={
                    "tool_name": tool_name,
                    "prompt_version": prompt_version,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                version=prompt_version,
            ) as observation:
                try:
                    yield observation
                except Exception as e:
                    observation.update(
                        level="ERROR",
                        status_message=str(e),
                    )
                    raise
                else:
                    observation.update(
                        metadata={"status": "success"},
                    )

    def flush(self) -> None:
        """Flush all pending traces to Langfuse."""
        if self.client:
            self.client.flush()

    def shutdown(self) -> None:
        """Shutdown the Langfuse client."""
        if self.client:
            self.client.shutdown()


_observer: Optional[LangfuseObserver] = None


def get_observer() -> LangfuseObserver:
    """Get the global observer instance."""
    global _observer
    if _observer is None:
        _observer = LangfuseObserver()
    return _observer


def init_observer(config: ObservabilityConfig = None) -> LangfuseObserver:
    """Initialize the global observer."""
    global _observer
    _observer = LangfuseObserver(config)
    return _observer
