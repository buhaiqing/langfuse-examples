"""
MCP Server entry point.
"""

import logging

from fastmcp import FastMCP

from src.observability import (
    ObservabilityConfig,
    init_observability,
    observe_tool,
)
from src.observability.alert_config_loader import load_alert_rules
from src.observability.alert_monitor import start_alert_monitor
from src.observability.feedback import (
    record_acceptance,
    record_comment,
    record_rating,
    record_rejection,
)
from src.observability.health import get_health_status
from src.observability.session import get_session_id
from src.observability.smart_alerting import SmartAlertManager

logger = logging.getLogger(__name__)

mcp = FastMCP("MCP Langfuse Observability Server")


# ============================================================================
# Feedback Tools - User Satisfaction Collection
# ============================================================================


@mcp.tool()
def health_check() -> dict:
    """
    Check the health status of the MCP server and all components.

    Returns comprehensive health information including:
    - Langfuse connection status
    - Alert manager status and loaded rules
    - Alert monitor running status
    - Smart alert manager (ML anomaly detection) status
    - Metrics cache statistics

    Returns:
        Dictionary containing health status of all components.
    """
    return get_health_status()


# ============================================================================
# Feedback Tools - User Satisfaction Collection
# ============================================================================


@mcp.tool()
@observe_tool(name="submit_feedback_accept")
def submit_feedback_accept(
    trace_id: str,
    comment: str | None = None,
) -> dict:
    """
    Submit positive feedback (accept) for a response.

    Args:
        trace_id: Trace ID of the response being rated.
        comment: Optional comment explaining acceptance.

    Returns:
        Confirmation dictionary.
    """
    record_acceptance(
        trace_id=trace_id,
        user_id=get_session_id(),
        comment=comment,
    )

    return {
        "status": "success",
        "message": "Feedback recorded",
        "feedback_type": "accept",
    }


@mcp.tool()
@observe_tool(name="submit_feedback_reject")
def submit_feedback_reject(
    trace_id: str,
    reason: str | None = None,
    comment: str | None = None,
) -> dict:
    """
    Submit negative feedback (reject) for a response.

    Args:
        trace_id: Trace ID of the response being rated.
        reason: Optional reason for rejection.
        comment: Optional detailed comment.

    Returns:
        Confirmation dictionary.
    """
    record_rejection(
        trace_id=trace_id,
        user_id=get_session_id(),
        reason=reason,
        comment=comment,
    )

    return {
        "status": "success",
        "message": "Feedback recorded",
        "feedback_type": "reject",
    }


@mcp.tool()
@observe_tool(name="submit_feedback_rating")
def submit_feedback_rating(
    trace_id: str,
    rating: int,
    comment: str | None = None,
) -> dict:
    """
    Submit a rating (1-5) for a response.

    Args:
        trace_id: Trace ID of the response being rated.
        rating: Rating value (1-5).
        comment: Optional comment.

    Returns:
        Confirmation dictionary.
    """
    if rating < 1 or rating > 5:
        return {
            "status": "error",
            "message": "Rating must be between 1 and 5",
        }

    record_rating(
        trace_id=trace_id,
        rating=rating,
        user_id=get_session_id(),
        comment=comment,
    )

    return {
        "status": "success",
        "message": f"Rating {rating}/5 recorded",
        "feedback_type": "rating",
    }


@mcp.tool()
@observe_tool(name="submit_feedback_comment")
def submit_feedback_comment(
    trace_id: str,
    comment: str,
) -> dict:
    """
    Submit a text comment for a response.

    Args:
        trace_id: Trace ID of the response being commented on.
        comment: Comment text.

    Returns:
        Confirmation dictionary.
    """
    record_comment(
        trace_id=trace_id,
        comment=comment,
        user_id=get_session_id(),
    )

    return {
        "status": "success",
        "message": "Comment recorded",
        "feedback_type": "comment",
    }


def main() -> None:
    """Run the MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = ObservabilityConfig()
    init_observability(config)

    logger.info("Loading alert rules...")
    try:
        rules_count = load_alert_rules()
        if rules_count == 0:
            logger.warning("No alert rules loaded. Use API or scripts to configure alerts.")
    except Exception as e:
        logger.error("Failed to load alert rules: %s", e)
        logger.info("Server will start without alert rules.")

    logger.info("Starting rule-based alert monitoring...")
    try:
        import os

        check_interval = int(os.getenv("ALERT_CHECK_INTERVAL_MINUTES", "5"))
        monitor = start_alert_monitor(check_interval_minutes=check_interval)
        logger.info("Rule-based alert monitoring enabled (every %d minutes)", check_interval)
    except Exception as e:
        logger.error("Failed to start rule-based alert monitor: %s", e)
        logger.info("Server will run without automatic rule-based alert checking.")

    logger.info("Starting smart ML-based anomaly detection...")
    try:
        smart_check_interval = int(os.getenv("SMART_ALERT_CHECK_INTERVAL_MINUTES", "10"))
        smart_manager = SmartAlertManager(detection_interval_minutes=smart_check_interval)
        smart_manager.start_monitoring()
        logger.info(
            "Smart ML anomaly detection enabled (every %d minutes) - "
            "Prophet time series + PyOD multivariate + auto-detect metrics",
            smart_check_interval,
        )
    except Exception as e:
        logger.error("Failed to start smart ML anomaly detection: %s", e)
        logger.info(
            "Server will run without ML-based anomaly detection. "
            "Install dependencies: pip install prophet pyod pandas numpy scikit-learn"
        )

    mcp.run()


if __name__ == "__main__":
    main()
