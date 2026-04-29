"""
Health check endpoints for MCP server monitoring.

Provides health status information for all core components
including Langfuse connection, alert system, and monitoring status.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Track server start time
START_TIME = time.time()


def get_health_status() -> dict[str, Any]:
    """
    Get comprehensive health status of the MCP server.

    Returns:
        Dictionary containing health status of all components.
    """
    status = {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime_seconds": time.time() - START_TIME,
        "components": {},
    }

    # Check Langfuse connection
    try:
        from src.observability.instrumentation import get_langfuse_client

        client = get_langfuse_client()
        status["components"]["langfuse"] = {
            "status": "connected" if client else "disconnected",
            "available": client is not None,
        }
        if client is None:
            status["status"] = "degraded"
    except Exception as e:
        status["components"]["langfuse"] = {
            "status": "error",
            "error": str(e),
        }
        status["status"] = "degraded"

    # Check alert manager
    try:
        from src.observability.alerting import get_alert_manager

        manager = get_alert_manager()
        rules = manager.list_rules()
        status["components"]["alert_manager"] = {
            "status": "healthy",
            "rules_loaded": len(rules),
        }
    except Exception as e:
        status["components"]["alert_manager"] = {
            "status": "error",
            "error": str(e),
        }
        status["status"] = "degraded"

    # Check alert monitor
    try:
        from src.observability.alert_monitor import get_alert_monitor

        monitor = get_alert_monitor()
        monitor_status = monitor.get_status()
        status["components"]["alert_monitor"] = {
            "status": "running" if monitor_status["is_running"] else "stopped",
            "is_running": monitor_status["is_running"],
            "check_interval_minutes": monitor_status["check_interval_minutes"],
        }
    except Exception as e:
        status["components"]["alert_monitor"] = {
            "status": "error",
            "error": str(e),
        }
        status["status"] = "degraded"

    # Check smart alert manager
    try:
        from src.observability.smart_alerting import SmartAlertManager

        smart_manager = SmartAlertManager()
        smart_status = smart_manager.get_status()
        status["components"]["smart_alert_manager"] = {
            "status": "running" if smart_status["is_running"] else "stopped",
            "is_running": smart_status["is_running"],
            "detection_interval_minutes": smart_status["detection_interval_minutes"],
            "last_detection": smart_status["last_detection"],
        }
    except Exception as e:
        status["components"]["smart_alert_manager"] = {
            "status": "error",
            "error": str(e),
        }
        status["status"] = "degraded"

    # Check metrics collector cache
    try:
        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        cache_stats = collector.get_cache_stats()
        status["components"]["metrics_cache"] = {
            "status": "healthy",
            "hit_rate": cache_stats["hit_rate"],
            "size": cache_stats["size"],
            "ttl_seconds": cache_stats["ttl_seconds"],
        }
    except Exception as e:
        status["components"]["metrics_cache"] = {
            "status": "error",
            "error": str(e),
        }
        status["status"] = "degraded"

    return status
