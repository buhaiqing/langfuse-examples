"""
MCP Server Langfuse Observability Platform.

This package provides instrumentation and observability for MCP servers
using Langfuse for tracing, metrics, and monitoring.
"""

from src.observability.alert_config_loader import validate_alert_config
from src.observability.alert_monitor import (
    AlertMonitorScheduler,
    get_alert_monitor,
    start_alert_monitor,
    stop_alert_monitor,
)
from src.observability.alerting import (
    Alert,
    AlertChannel,
    AlertManager,
    AlertRule,
    AlertSeverity,
    check_latency,
    check_success_rate,
    configure_latency_alert,
    configure_success_rate_alert,
    get_alert_manager,
)
from src.observability.anomaly_detector import AnomalyDetector
from src.observability.config import ObservabilityConfig
from src.observability.decorators import observe_tool, track_prompt_version, track_session
from src.observability.feedback import (
    Feedback,
    FeedbackCollector,
    FeedbackType,
    get_acceptance_rate,
    get_feedback_collector,
    get_feedback_statistics,
    record_acceptance,
    record_comment,
    record_rating,
    record_rejection,
)
from src.observability.instrumentation import get_langfuse_client, init_observability
from src.observability.metrics_collector import MetricsCollector
from src.observability.session import (
    SessionManager,
    clear_session,
    get_session_id,
    get_user_id,
    set_session,
)
from src.observability.smart_alerting import SmartAlertManager

__all__ = [
    "Alert",
    "AlertChannel",
    "AlertManager",
    "AlertMonitorScheduler",
    "AlertRule",
    "AlertSeverity",
    "AnomalyDetector",
    "Feedback",
    "FeedbackCollector",
    "FeedbackType",
    "MetricsCollector",
    "ObservabilityConfig",
    "SessionManager",
    "SmartAlertManager",
    "check_latency",
    "check_success_rate",
    "clear_session",
    "configure_latency_alert",
    "configure_success_rate_alert",
    "get_acceptance_rate",
    "get_alert_manager",
    "get_alert_monitor",
    "get_feedback_collector",
    "get_feedback_statistics",
    "get_langfuse_client",
    "get_session_id",
    "get_user_id",
    "init_observability",
    "observe_tool",
    "record_acceptance",
    "record_comment",
    "record_rating",
    "record_rejection",
    "set_session",
    "start_alert_monitor",
    "stop_alert_monitor",
    "track_prompt_version",
    "track_session",
    "validate_alert_config",
]
