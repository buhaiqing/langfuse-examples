"""
Tool calling module with Langfuse tracing
Executes external APIs and tools for customer service tasks
"""

import asyncio
import time
from enum import Enum
from typing import Any

from core.scoring import score_tool_success_rate
from core.tracing import create_span, score_trace


class ToolName(str, Enum):
    """Available tools for customer service"""

    QUERY_TICKET_STATUS = "query_ticket_status"
    GET_PRODUCT_INFO = "get_product_info"
    CHECK_ACCOUNT_STATUS = "check_account_status"
    RESET_PASSWORD = "reset_password"
    CREATE_SUPPORT_TICKET = "create_support_ticket"


class ToolCallingSystem:
    """Tool execution system with Langfuse tracing"""

    def __init__(self):
        self.tools = {
            ToolName.QUERY_TICKET_STATUS: self._query_ticket_status,
            ToolName.GET_PRODUCT_INFO: self._get_product_info,
            ToolName.CHECK_ACCOUNT_STATUS: self._check_account_status,
            ToolName.RESET_PASSWORD: self._reset_password,
            ToolName.CREATE_SUPPORT_TICKET: self._create_support_ticket,
        }

    async def execute_tool(
        self, tool_name: str, arguments: dict[str, Any], trace_context: dict | None = None
    ) -> dict[str, Any]:
        """
        Execute a tool with full Langfuse tracing

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            trace_context: Optional trace context

        Returns:
            Tool execution result
        """
        start_time = time.time()

        # Create main span for tool execution
        with create_span(
            name=f"tool_execution_{tool_name}",
            input_data={"arguments": arguments},
            metadata={
                "tool_name": tool_name,
                "execution_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        ) as main_span:

            try:
                # Get tool function
                if tool_name not in self.tools:
                    raise ValueError(f"Unknown tool: {tool_name}")

                tool_func = self.tools[tool_name]

                # Step 1: Parameter validation
                validation_span = create_span(
                    name="parameter_validation", input_data={"raw_arguments": arguments}
                )
                validated_args = self._validate_parameters(tool_name, arguments)
                validation_span.end(
                    output_data={"validated": True, "param_count": len(validated_args)}
                )

                # Step 2: API call
                api_span = create_span(
                    name="api_call", input_data={"endpoint": tool_name, "params": validated_args}
                )

                result = await tool_func(validated_args)

                api_span.end(output_data={"status": "success", "result_summary": str(result)[:200]})

                # Step 3: Result parsing
                parse_span = create_span(name="result_parsing", input_data={"raw_result": result})
                parsed_result = self._parse_result(tool_name, result)
                parse_span.end(output_data={"parsed": True})

                # Calculate execution time
                execution_time = (time.time() - start_time) * 1000

                # Add success score
                score_tool_success_rate(1.0, comment=f"Tool {tool_name} executed successfully")

                score_trace(
                    name="tool_execution_time_ms",
                    value=execution_time,
                    data_type="NUMERIC",
                    comment=f"Execution time for {tool_name}",
                )

                # Update main span
                main_span.end(
                    output_data={
                        "status": "success",
                        "result": parsed_result,
                        "execution_time_ms": execution_time,
                    }
                )

                return {
                    "success": True,
                    "result": parsed_result,
                    "execution_time_ms": execution_time,
                }

            except Exception as e:
                execution_time = (time.time() - start_time) * 1000

                # Record failure
                score_tool_success_rate(0.0, comment=f"Tool {tool_name} failed: {str(e)}")

                # Update main span with error
                main_span.end(
                    output_data={
                        "status": "failed",
                        "error": str(e),
                        "execution_time_ms": execution_time,
                    }
                )

                return {"success": False, "error": str(e), "execution_time_ms": execution_time}

    def _validate_parameters(self, tool_name: str, arguments: dict) -> dict:
        """Validate tool parameters"""
        # Add validation logic based on tool
        if tool_name == ToolName.QUERY_TICKET_STATUS:
            if "ticket_id" not in arguments:
                raise ValueError("ticket_id is required")

        elif tool_name == ToolName.GET_PRODUCT_INFO:
            if "product_id" not in arguments:
                raise ValueError("product_id is required")

        return arguments

    def _parse_result(self, tool_name: str, result: Any) -> dict:
        """Parse tool result into standardized format"""
        if isinstance(result, dict):
            return result
        return {"data": result}

    # Mock tool implementations (replace with real API calls)
    async def _query_ticket_status(self, args: dict) -> dict:
        """Query ticket status (mock implementation)"""
        # Simulate API call delay
        await asyncio.sleep(0.2)

        ticket_id = args.get("ticket_id", "UNKNOWN")

        # Mock response
        return {
            "ticket_id": ticket_id,
            "status": "in_progress",
            "priority": "high",
            "assigned_to": "John Smith",
            "created_at": "2026-04-05T10:30:00Z",
            "last_updated": "2026-04-08T14:20:00Z",
            "description": "API authentication issue - 403 error",
        }

    async def _get_product_info(self, args: dict) -> dict:
        """Get product information (mock implementation)"""
        await asyncio.sleep(0.15)

        product_id = args.get("product_id", "PROD-001")

        return {
            "product_id": product_id,
            "name": "Enterprise API Plan",
            "version": "v2.3",
            "features": ["Unlimited API calls", "Priority support", "Custom rate limits"],
            "documentation_url": f"https://docs.example.com/products/{product_id}",
        }

    async def _check_account_status(self, args: dict) -> dict:
        """Check account status (mock implementation)"""
        await asyncio.sleep(0.1)

        account_id = args.get("account_id", "ACC-12345")

        return {
            "account_id": account_id,
            "status": "active",
            "plan": "professional",
            "api_calls_remaining": 8500,
            "api_calls_limit": 10000,
            "reset_date": "2026-05-01T00:00:00Z",
        }

    async def _reset_password(self, args: dict) -> dict:
        """Reset password (mock implementation)"""
        await asyncio.sleep(0.3)

        email = args.get("email", "user@example.com")

        return {
            "success": True,
            "message": f"Password reset email sent to {email}",
            "expires_in_minutes": 30,
        }

    async def _create_support_ticket(self, args: dict) -> dict:
        """Create support ticket (mock implementation)"""
        await asyncio.sleep(0.25)

        return {
            "ticket_id": f"TKT-{int(time.time())}",
            "status": "open",
            "priority": args.get("priority", "medium"),
            "estimated_response_time": "24 hours",
            "message": "Ticket created successfully. You will receive an email confirmation.",
        }


# Singleton instance
tool_system = ToolCallingSystem()


async def call_tool(
    tool_name: str, arguments: dict[str, Any], trace_context: dict | None = None
) -> dict[str, Any]:
    """
    Convenience function to call a tool

    Args:
        tool_name: Name of the tool
        arguments: Tool arguments
        trace_context: Optional trace context

    Returns:
        Tool execution result
    """
    return await tool_system.execute_tool(tool_name, arguments, trace_context)


# Export
__all__ = ["ToolCallingSystem", "call_tool", "ToolName"]
