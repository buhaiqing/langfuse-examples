"""
Tests for tool calling module with logging
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from modules.tool_calling import ToolCallingSystem, ToolName, tool_system


class TestToolCallingSystem:
    """Test suite for ToolCallingSystem class"""

    def test_initialization(self):
        """Arrange-Act-Assert: Verify ToolCallingSystem initializes correctly"""
        system = ToolCallingSystem()
        assert system is not None
        assert len(system.tools) == 5

    def test_tool_names_defined(self):
        """Arrange-Act-Assert: Verify all tool names are defined"""
        assert ToolName.QUERY_TICKET_STATUS.value == "query_ticket_status"
        assert ToolName.GET_PRODUCT_INFO.value == "get_product_info"
        assert ToolName.CHECK_ACCOUNT_STATUS.value == "check_account_status"
        assert ToolName.RESET_PASSWORD.value == "reset_password"
        assert ToolName.CREATE_SUPPORT_TICKET.value == "create_support_ticket"


class TestToolExecution:
    """Test suite for tool execution"""

    @pytest.mark.asyncio
    async def test_execute_query_ticket_status(self):
        """Arrange-Act-Assert: Verify query ticket status tool executes correctly"""
        system = ToolCallingSystem()
        result = await system.execute_tool(
            "query_ticket_status",
            {"ticket_id": "TKT-001"}
        )
        assert result["success"] is True
        assert "result" in result
        assert result["result"]["ticket_id"] == "TKT-001"

    @pytest.mark.asyncio
    async def test_execute_get_product_info(self):
        """Arrange-Act-Assert: Verify get product info tool executes correctly"""
        system = ToolCallingSystem()
        result = await system.execute_tool(
            "get_product_info",
            {"product_id": "PROD-001"}
        )
        assert result["success"] is True
        assert result["result"]["product_id"] == "PROD-001"
        assert "name" in result["result"]

    @pytest.mark.asyncio
    async def test_execute_check_account_status(self):
        """Arrange-Act-Assert: Verify check account status tool executes correctly"""
        system = ToolCallingSystem()
        result = await system.execute_tool(
            "check_account_status",
            {"account_id": "ACC-12345"}
        )
        assert result["success"] is True
        assert result["result"]["account_id"] == "ACC-12345"

    @pytest.mark.asyncio
    async def test_execute_reset_password(self):
        """Arrange-Act-Assert: Verify reset password tool executes correctly"""
        system = ToolCallingSystem()
        result = await system.execute_tool(
            "reset_password",
            {"email": "test@example.com"}
        )
        assert result["success"] is True
        assert result["result"]["success"] is True

    @pytest.mark.asyncio
    async def test_execute_create_support_ticket(self):
        """Arrange-Act-Assert: Verify create support ticket tool executes correctly"""
        system = ToolCallingSystem()
        result = await system.execute_tool(
            "create_support_ticket",
            {"priority": "high", "description": "Test issue"}
        )
        assert result["success"] is True
        assert "ticket_id" in result["result"]


class TestToolValidation:
    """Test suite for tool parameter validation"""

    @pytest.mark.asyncio
    async def test_query_ticket_requires_ticket_id(self):
        """Arrange-Act-Assert: Verify query ticket requires ticket_id"""
        system = ToolCallingSystem()
        result = await system.execute_tool(
            "query_ticket_status",
            {}
        )
        assert result["success"] is False
        assert "ticket_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_product_requires_product_id(self):
        """Arrange-Act-Assert: Verify get product requires product_id"""
        system = ToolCallingSystem()
        result = await system.execute_tool(
            "get_product_info",
            {}
        )
        assert result["success"] is False
        assert "product_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Arrange-Act-Assert: Verify unknown tool returns error"""
        system = ToolCallingSystem()
        result = await system.execute_tool(
            "unknown_tool",
            {}
        )
        assert result["success"] is False
        assert "Unknown tool" in result["error"]


class TestToolExecutionTime:
    """Test suite for execution time tracking"""

    @pytest.mark.asyncio
    async def test_execution_time_recorded(self):
        """Arrange-Act-Assert: Verify execution time is recorded"""
        system = ToolCallingSystem()
        result = await system.execute_tool(
            "query_ticket_status",
            {"ticket_id": "TKT-001"}
        )
        assert "execution_time_ms" in result
        assert result["execution_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_failed_execution_time_recorded(self):
        """Arrange-Act-Assert: Verify failed execution also records time"""
        system = ToolCallingSystem()
        result = await system.execute_tool(
            "query_ticket_status",
            {}
        )
        assert "execution_time_ms" in result
        assert result["execution_time_ms"] >= 0


class TestToolSingleton:
    """Test suite for singleton instance"""

    def test_tool_system_singleton(self):
        """Arrange-Act-Assert: Verify tool_system is a singleton instance"""
        from modules.tool_calling import tool_system as ts1
        from modules.tool_calling import tool_system as ts2
        assert ts1 is ts2


class TestCallToolFunction:
    """Test suite for call_tool convenience function"""

    @pytest.mark.asyncio
    async def test_call_tool_function(self):
        """Arrange-Act-Assert: Verify call_tool convenience function works"""
        from modules.tool_calling import call_tool
        result = await call_tool(
            "get_product_info",
            {"product_id": "PROD-001"}
        )
        assert result["success"] is True
