"""
MCP Server entry point.
"""

import asyncio
from fastmcp import FastMCP

from src.observability import (
    ObservabilityConfig,
    init_observability,
    observe_tool,
)
from src.observability.feedback import (
    record_acceptance,
    record_comment,
    record_rejection,
    record_rating,
)
from src.observability.session import get_session_id
from src.observability.alert_config_loader import load_alert_rules
from src.observability.alert_monitor import start_alert_monitor
from src.observability.smart_alerting import SmartAlertManager

mcp = FastMCP("MCP Langfuse Observability Server")


# ============================================================================
# Feedback Tools - User Satisfaction Collection
# ============================================================================


@mcp.tool()
@observe_tool(name="submit_feedback_accept")
def submit_feedback_accept(
    trace_id: str,
    comment: str = None,
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
    reason: str = None,
    comment: str = None,
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
    comment: str = None,
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


def main():
    """Run the MCP server."""
    config = ObservabilityConfig()
    init_observability(config)

    # Load alert rules from configuration file
    print("\n" + "=" * 60)
    print("Loading alert rules...")
    print("=" * 60)
    try:
        rules_count = load_alert_rules()
        if rules_count == 0:
            print("⚠️  No alert rules loaded. Use API or scripts to configure alerts.")
    except Exception as e:
        print(f"❌ Failed to load alert rules: {e}")
        print("   Server will start without alert rules.")
    print("=" * 60 + "\n")

    # Start background alert monitoring (Phase 5: Rule-based)
    print("=" * 60)
    print("Starting rule-based alert monitoring...")
    print("=" * 60)
    try:
        import os

        check_interval = int(os.getenv("ALERT_CHECK_INTERVAL_MINUTES", "5"))
        monitor = start_alert_monitor(check_interval_minutes=check_interval)
        print(f"✅ Rule-based alert monitoring enabled (every {check_interval} minutes)")
    except Exception as e:
        print(f"❌ Failed to start rule-based alert monitor: {e}")
        print("   Server will run without automatic rule-based alert checking.")
    print("=" * 60 + "\n")

    # Start smart ML-based anomaly detection (Phase 6)
    print("=" * 60)
    print("Starting smart ML-based anomaly detection...")
    print("=" * 60)
    try:
        smart_check_interval = int(os.getenv("SMART_ALERT_CHECK_INTERVAL_MINUTES", "10"))
        smart_manager = SmartAlertManager(detection_interval_minutes=smart_check_interval)
        smart_manager.start_monitoring()
        print(f"✅ Smart ML anomaly detection enabled (every {smart_check_interval} minutes)")
        print(f"   - Prophet time series forecasting")
        print(f"   - PyOD multivariate anomaly detection")
        print(f"   - Auto-detects: success_rate, latency_p95, request_rate, satisfaction")
    except Exception as e:
        print(f"❌ Failed to start smart ML anomaly detection: {e}")
        print("   Server will run without ML-based anomaly detection.")
        print("   Install dependencies: pip install prophet pyod pandas numpy scikit-learn")
    print("=" * 60 + "\n")

    mcp.run()


if __name__ == "__main__":
    main()
