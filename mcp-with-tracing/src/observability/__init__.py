"""
MCP Server Langfuse Observability Platform.

This package provides instrumentation and observability for MCP servers
using Langfuse for tracing, metrics, and monitoring.
"""

from src.observability.config import ObservabilityConfig
from src.observability.instrumentation import init_observability, get_langfuse_client
from src.observability.session import (
    SessionManager,
    get_session_id,
    get_user_id,
    set_session,
    clear_session,
)
from src.observability.decorators import observe_tool, track_session, track_prompt_version
from src.observability.alerting import (
    AlertManager,
    AlertRule,
    Alert,
    AlertSeverity,
    AlertChannel,
    get_alert_manager,
    configure_success_rate_alert,
    configure_latency_alert,
    check_success_rate,
    check_latency,
)
from src.observability.feedback import (
    FeedbackCollector,
    FeedbackType,
    Feedback,
    get_feedback_collector,
    record_acceptance,
    record_rejection,
    record_rating,
    record_comment,
    get_acceptance_rate,
    get_feedback_statistics,
)

__all__ = [
    "ObservabilityConfig",
    "init_observability",
    "get_langfuse_client",
    "SessionManager",
    "get_session_id",
    "get_user_id",
    "set_session",
    "clear_session",
    "observe_tool",
    "track_session",
    "track_prompt_version",
    "AlertManager",
    "AlertRule",
    "Alert",
    "AlertSeverity",
    "AlertChannel",
    "get_alert_manager",
    "configure_success_rate_alert",
    "configure_latency_alert",
    "check_success_rate",
    "check_latency",
    "FeedbackCollector",
    "FeedbackType",
    "Feedback",
    "get_feedback_collector",
    "record_acceptance",
    "record_rejection",
    "record_rating",
    "record_comment",
    "get_acceptance_rate",
    "get_feedback_statistics",
]
