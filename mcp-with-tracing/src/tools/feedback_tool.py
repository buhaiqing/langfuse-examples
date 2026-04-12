"""
MCP Feedback Tool for user satisfaction collection.

Provides MCP tools for collecting user feedback on responses.
"""

from fastmcp import FastMCP
from src.observability import observe_tool
from src.observability.feedback import (
    record_acceptance,
    record_rejection,
    record_rating,
    record_comment,
)
from src.observability.session import get_session_id


mcp = FastMCP("Feedback Tools")


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
    feedback = record_acceptance(
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
    feedback = record_rejection(
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

    feedback = record_rating(
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
    feedback = record_comment(
        trace_id=trace_id,
        comment=comment,
        user_id=get_session_id(),
    )

    return {
        "status": "success",
        "message": "Comment recorded",
        "feedback_type": "comment",
    }
