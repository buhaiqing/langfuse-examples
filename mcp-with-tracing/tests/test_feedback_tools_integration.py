"""
Integration tests for MCP feedback tools.

Tests the integration of feedback tools with the main MCP server.
"""

from unittest.mock import Mock, patch

import pytest

from src.server import mcp


# Get the original functions from FunctionTool objects
def get_tool_function(tool_name: str):
    """Extract the original function from a registered tool."""
    import asyncio

    async def _get():
        tools = await mcp._tool_manager.list_tools()
        for tool in tools:
            if tool.name == tool_name:
                return tool.fn
        return None

    return asyncio.run(_get())


class TestFeedbackToolsIntegration:
    """Test feedback tools are properly integrated with MCP server."""

    @pytest.mark.asyncio
    async def test_all_feedback_tools_registered(self):
        """Test that all feedback tools are registered in MCP server."""
        tools = await mcp._tool_manager.list_tools()
        tool_names = [tool.name for tool in tools]

        # Check all feedback tools are registered
        assert "submit_feedback_accept" in tool_names
        assert "submit_feedback_reject" in tool_names
        assert "submit_feedback_rating" in tool_names
        assert "submit_feedback_comment" in tool_names

    @pytest.mark.asyncio
    async def test_feedback_tools_have_correct_descriptions(self):
        """Test that feedback tools have proper descriptions."""
        tools = await mcp._tool_manager.list_tools()
        tools_dict = {tool.name: tool for tool in tools}

        # Verify descriptions exist
        assert "submit_feedback_accept" in tools_dict
        assert tools_dict["submit_feedback_accept"].description
        assert "accept" in tools_dict["submit_feedback_accept"].description.lower()

        assert "submit_feedback_reject" in tools_dict
        assert tools_dict["submit_feedback_reject"].description
        assert "reject" in tools_dict["submit_feedback_reject"].description.lower()

    @pytest.mark.asyncio
    async def test_total_tool_count(self):
        """Test that server has expected number of tools."""
        tools = await mcp._tool_manager.list_tools()

        # Should have: 4 feedback tools = 4 total
        assert len(tools) == 4


class TestFeedbackToolFunctions:
    """Test feedback tool functions directly."""

    def setup_method(self):
        """Setup test fixtures."""
        self.test_trace_id = "test-trace-123"
        self.test_user_id = "test-user-456"

        # Get original functions from registered tools
        self.submit_feedback_accept = get_tool_function("submit_feedback_accept")
        self.submit_feedback_reject = get_tool_function("submit_feedback_reject")
        self.submit_feedback_rating = get_tool_function("submit_feedback_rating")
        self.submit_feedback_comment = get_tool_function("submit_feedback_comment")

    @patch("src.server.get_session_id")
    @patch("src.server.record_acceptance")
    def test_submit_feedback_accept_success(self, mock_record, mock_get_session):
        """Test submit_feedback_accept returns correct response."""
        mock_get_session.return_value = self.test_user_id
        mock_record.return_value = Mock(trace_id=self.test_trace_id)

        result = self.submit_feedback_accept(
            trace_id=self.test_trace_id,
            comment="Great response!",
        )

        assert result["status"] == "success"
        assert result["message"] == "Feedback recorded"
        assert result["feedback_type"] == "accept"
        mock_record.assert_called_once_with(
            trace_id=self.test_trace_id,
            user_id=self.test_user_id,
            comment="Great response!",
        )

    @patch("src.server.get_session_id")
    @patch("src.server.record_rejection")
    def test_submit_feedback_reject_success(self, mock_record, mock_get_session):
        """Test submit_feedback_reject returns correct response."""
        mock_get_session.return_value = self.test_user_id
        mock_record.return_value = Mock(trace_id=self.test_trace_id)

        result = self.submit_feedback_reject(
            trace_id=self.test_trace_id,
            reason="inaccurate",
            comment="Wrong information",
        )

        assert result["status"] == "success"
        assert result["message"] == "Feedback recorded"
        assert result["feedback_type"] == "reject"
        mock_record.assert_called_once_with(
            trace_id=self.test_trace_id,
            user_id=self.test_user_id,
            reason="inaccurate",
            comment="Wrong information",
        )

    @patch("src.server.get_session_id")
    @patch("src.server.record_rating")
    def test_submit_feedback_rating_success(self, mock_record, mock_get_session):
        """Test submit_feedback_rating returns correct response."""
        mock_get_session.return_value = self.test_user_id
        mock_record.return_value = Mock(trace_id=self.test_trace_id)

        result = self.submit_feedback_rating(
            trace_id=self.test_trace_id,
            rating=5,
            comment="Excellent!",
        )

        assert result["status"] == "success"
        assert result["message"] == "Rating 5/5 recorded"
        assert result["feedback_type"] == "rating"
        mock_record.assert_called_once_with(
            trace_id=self.test_trace_id,
            rating=5,
            user_id=self.test_user_id,
            comment="Excellent!",
        )

    @patch("src.server.get_session_id")
    @patch("src.server.record_rating")
    def test_submit_feedback_rating_invalid(self, mock_record, mock_get_session):
        """Test submit_feedback_rating rejects invalid ratings."""
        # Rating too low
        result = self.submit_feedback_rating(
            trace_id=self.test_trace_id,
            rating=0,
        )
        assert result["status"] == "error"
        assert "must be between 1 and 5" in result["message"]

        # Rating too high
        result = self.submit_feedback_rating(
            trace_id=self.test_trace_id,
            rating=6,
        )
        assert result["status"] == "error"
        assert "must be between 1 and 5" in result["message"]

    @patch("src.server.get_session_id")
    @patch("src.server.record_comment")
    def test_submit_feedback_comment_success(self, mock_record, mock_get_session):
        """Test submit_feedback_comment returns correct response."""
        mock_get_session.return_value = self.test_user_id
        mock_record.return_value = Mock(trace_id=self.test_trace_id)

        result = self.submit_feedback_comment(
            trace_id=self.test_trace_id,
            comment="This was very helpful!",
        )

        assert result["status"] == "success"
        assert result["message"] == "Comment recorded"
        assert result["feedback_type"] == "comment"
        mock_record.assert_called_once_with(
            trace_id=self.test_trace_id,
            comment="This was very helpful!",
            user_id=self.test_user_id,
        )


class TestFeedbackToolObservability:
    """Test that feedback tools have proper observability decorators."""

    @pytest.mark.asyncio
    async def test_tools_have_observe_decorator(self):
        """Test that all feedback tools are properly registered with tracing."""
        # All feedback tools should be registered in the MCP server
        tools = await mcp._tool_manager.list_tools()
        tool_names = [tool.name for tool in tools]

        # Verify all feedback tools are registered
        assert "submit_feedback_accept" in tool_names
        assert "submit_feedback_reject" in tool_names
        assert "submit_feedback_rating" in tool_names
        assert "submit_feedback_comment" in tool_names

    @pytest.mark.asyncio
    async def test_tools_have_correct_span_names(self):
        """Test that tools have correct names for tracing."""
        tools = await mcp._tool_manager.list_tools()
        tools_dict = {tool.name: tool for tool in tools}

        # Verify tool names match expected span names
        assert "submit_feedback_accept" in tools_dict
        assert "submit_feedback_reject" in tools_dict
        assert "submit_feedback_rating" in tools_dict
        assert "submit_feedback_comment" in tools_dict


class TestFeedbackToolEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Setup test fixtures."""
        self.test_trace_id = "test-trace-123"
        self.test_user_id = "test-user-456"

        # Get original functions from registered tools
        self.submit_feedback_accept = get_tool_function("submit_feedback_accept")
        self.submit_feedback_reject = get_tool_function("submit_feedback_reject")

    @patch("src.server.get_session_id")
    @patch("src.server.record_acceptance")
    def test_feedback_without_comment(self, mock_record, mock_get_session):
        """Test feedback submission without optional comment."""
        mock_get_session.return_value = self.test_user_id
        mock_record.return_value = Mock(trace_id=self.test_trace_id)

        result = self.submit_feedback_accept(trace_id=self.test_trace_id)

        assert result["status"] == "success"
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args[1]
        assert call_kwargs["comment"] is None

    @patch("src.server.get_session_id")
    @patch("src.server.record_rejection")
    def test_feedback_without_reason(self, mock_record, mock_get_session):
        """Test rejection without optional reason."""
        mock_get_session.return_value = self.test_user_id
        mock_record.return_value = Mock(trace_id=self.test_trace_id)

        result = self.submit_feedback_reject(trace_id=self.test_trace_id)

        assert result["status"] == "success"
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args[1]
        assert call_kwargs["reason"] is None
        assert call_kwargs["comment"] is None
