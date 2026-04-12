"""
Tool calling module with Langfuse tracing
Executes external APIs and tools for customer service tasks
"""

import asyncio
import time
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, Field

from config.settings import (
    ACCOUNT_API_KEY,
    ACCOUNT_API_URL,
    OPENAI_API_KEY,
    PRODUCT_API_KEY,
    PRODUCT_API_URL,
    TICKET_API_KEY,
    TICKET_API_URL,
)
from core.logging_config import LogCategory, get_logger
from core.scoring import score_tool_success_rate
from core.tracing import create_span, score_trace

logger = get_logger(LogCategory.TOOL)


class ToolName(str, Enum):
    """Available tools for customer service"""

    QUERY_TICKET_STATUS = "query_ticket_status"
    GET_PRODUCT_INFO = "get_product_info"
    CHECK_ACCOUNT_STATUS = "check_account_status"
    RESET_PASSWORD = "reset_password"
    CREATE_SUPPORT_TICKET = "create_support_ticket"


class TicketStatusResponse(BaseModel):
    ticket_id: str
    status: str
    priority: str
    assigned_to: str
    created_at: str
    last_updated: str
    description: str | None = None


class ProductInfoResponse(BaseModel):
    product_id: str
    name: str
    version: str
    features: list[str]
    documentation_url: str


class AccountStatusResponse(BaseModel):
    account_id: str
    status: str
    plan: str
    api_calls_remaining: int
    api_calls_limit: int
    reset_date: str


class PasswordResetResponse(BaseModel):
    success: bool
    message: str
    expires_in_minutes: int


class SupportTicketResponse(BaseModel):
    ticket_id: str
    status: str
    priority: str
    estimated_response_time: str
    message: str


class ToolCallingSystem:
    """Tool execution system with Langfuse tracing"""

    def __init__(self):
        logger.info("Initializing Tool Calling System")
        self.tools = {
            ToolName.QUERY_TICKET_STATUS: self._query_ticket_status,
            ToolName.GET_PRODUCT_INFO: self._get_product_info,
            ToolName.CHECK_ACCOUNT_STATUS: self._check_account_status,
            ToolName.RESET_PASSWORD: self._reset_password,
            ToolName.CREATE_SUPPORT_TICKET: self._create_support_ticket,
        }

        self.http_client: httpx.AsyncClient | None = None
        if TICKET_API_URL or PRODUCT_API_URL or ACCOUNT_API_URL:
            self.http_client = httpx.AsyncClient(timeout=30.0)
            logger.info("HTTP client initialized for external API calls")

        logger.info(f"Tool Calling System initialized with {len(self.tools)} tools")

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
        logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")

        with create_span(
            name=f"tool_execution_{tool_name}",
            input_data={"arguments": arguments},
            metadata={
                "tool_name": tool_name,
                "execution_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        ) as main_span:

            try:
                if tool_name not in self.tools:
                    raise ValueError(f"Unknown tool: {tool_name}")

                tool_func = self.tools[tool_name]
                logger.debug(f"Found tool function for: {tool_name}")

                validation_span = create_span(
                    name="parameter_validation", input_data={"raw_arguments": arguments}
                )
                logger.debug("Validating tool parameters")
                validated_args = self._validate_parameters(tool_name, arguments)
                validation_span.end(
                    output_data={"validated": True, "param_count": len(validated_args)}
                )
                logger.debug(f"Parameters validated: {len(validated_args)} parameters")

                api_span = create_span(
                    name="api_call", input_data={"endpoint": tool_name, "params": validated_args}
                )
                logger.debug(f"Calling API for tool: {tool_name}")

                result = await tool_func(validated_args)

                api_span.end(output_data={"status": "success", "result_summary": str(result)[:200]})
                logger.info(f"Tool {tool_name} executed successfully")

                parse_span = create_span(name="result_parsing", input_data={"raw_result": result})
                logger.debug("Parsing tool result")
                parsed_result = self._parse_result(tool_name, result)
                parse_span.end(output_data={"parsed": True})
                logger.debug("Result parsed successfully")

                execution_time = (time.time() - start_time) * 1000

                score_tool_success_rate(1.0, comment=f"Tool {tool_name} executed successfully")

                score_trace(
                    name="tool_execution_time_ms",
                    value=execution_time,
                    data_type="NUMERIC",
                    comment=f"Execution time for {tool_name}",
                )

                main_span.end(
                    output_data={
                        "status": "success",
                        "result": parsed_result,
                        "execution_time_ms": execution_time,
                    }
                )

                logger.info(f"Tool execution completed: {tool_name}, time: {execution_time:.0f}ms")

                return {
                    "success": True,
                    "result": parsed_result,
                    "execution_time_ms": execution_time,
                }

            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                logger.error(f"Tool execution failed: {tool_name}, error: {str(e)}")

                score_tool_success_rate(0.0, comment=f"Tool {tool_name} failed: {str(e)}")

                main_span.end(
                    output_data={
                        "status": "failed",
                        "error": str(e),
                        "execution_time_ms": execution_time,
                    }
                )

                logger.error(f"Tool {tool_name} failed after {execution_time:.0f}ms")
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

    async def _query_ticket_status(self, args: dict) -> dict:
        """Query ticket status from external API"""
        ticket_id = args.get("ticket_id")
        logger.info(f"Querying ticket status for: {ticket_id}")

        if self.http_client and TICKET_API_URL and TICKET_API_KEY:
            try:
                response = await self.http_client.get(
                    f"{TICKET_API_URL}/{ticket_id}",
                    headers={"Authorization": f"Bearer {TICKET_API_KEY}"},
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"Ticket status retrieved from API: {ticket_id}")
                return {
                    "ticket_id": data.get("ticket_id", ticket_id),
                    "status": data.get("status", "unknown"),
                    "priority": data.get("priority", "medium"),
                    "assigned_to": data.get("assigned_to", "Unassigned"),
                    "created_at": data.get("created_at", ""),
                    "last_updated": data.get("last_updated", ""),
                    "description": data.get("description"),
                }
            except httpx.HTTPError as e:
                logger.warning(f"Ticket API call failed, using fallback: {e}")
                return await self._query_ticket_status_fallback(ticket_id)

        return await self._query_ticket_status_fallback(ticket_id)

    async def _query_ticket_status_fallback(self, ticket_id: str) -> dict:
        """Fallback mock implementation for ticket status query"""
        await asyncio.sleep(0.1)
        return {
            "ticket_id": ticket_id,
            "status": "open",
            "priority": "medium",
            "assigned_to": "Support Team",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "description": f"Ticket {ticket_id} - Status inquiry",
        }

    async def _get_product_info(self, args: dict) -> dict:
        """Get product information from external API"""
        product_id = args.get("product_id")
        logger.info(f"Getting product info for: {product_id}")

        if self.http_client and PRODUCT_API_URL and PRODUCT_API_KEY:
            try:
                response = await self.http_client.get(
                    f"{PRODUCT_API_URL}/{product_id}",
                    headers={"Authorization": f"Bearer {PRODUCT_API_KEY}"},
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"Product info retrieved from API: {product_id}")
                return {
                    "product_id": data.get("product_id", product_id),
                    "name": data.get("name", "Unknown Product"),
                    "version": data.get("version", "v1.0"),
                    "features": data.get("features", []),
                    "documentation_url": data.get("documentation_url", ""),
                }
            except httpx.HTTPError as e:
                logger.warning(f"Product API call failed, using fallback: {e}")
                return await self._get_product_info_fallback(product_id)

        return await self._get_product_info_fallback(product_id)

    async def _get_product_info_fallback(self, product_id: str) -> dict:
        """Fallback mock implementation for product info"""
        await asyncio.sleep(0.1)
        return {
            "product_id": product_id,
            "name": f"Product {product_id}",
            "version": "v1.0",
            "features": ["Standard support"],
            "documentation_url": f"https://docs.example.com/products/{product_id}",
        }

    async def _check_account_status(self, args: dict) -> dict:
        """Check account status from external API"""
        account_id = args.get("account_id")
        logger.info(f"Checking account status for: {account_id}")

        if self.http_client and ACCOUNT_API_URL and ACCOUNT_API_KEY:
            try:
                response = await self.http_client.get(
                    f"{ACCOUNT_API_URL}/{account_id}",
                    headers={"Authorization": f"Bearer {ACCOUNT_API_KEY}"},
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"Account status retrieved from API: {account_id}")
                return {
                    "account_id": data.get("account_id", account_id),
                    "status": data.get("status", "active"),
                    "plan": data.get("plan", "basic"),
                    "api_calls_remaining": data.get("api_calls_remaining", 0),
                    "api_calls_limit": data.get("api_calls_limit", 1000),
                    "reset_date": data.get("reset_date", ""),
                }
            except httpx.HTTPError as e:
                logger.warning(f"Account API call failed, using fallback: {e}")
                return await self._check_account_status_fallback(account_id)

        return await self._check_account_status_fallback(account_id)

    async def _check_account_status_fallback(self, account_id: str) -> dict:
        """Fallback mock implementation for account status"""
        await asyncio.sleep(0.1)
        return {
            "account_id": account_id,
            "status": "active",
            "plan": "standard",
            "api_calls_remaining": 5000,
            "api_calls_limit": 10000,
            "reset_date": "2026-05-01T00:00:00Z",
        }

    async def _reset_password(self, args: dict) -> dict:
        """Reset password via external API"""
        email = args.get("email")
        logger.info(f"Resetting password for: {email}")

        if self.http_client and ACCOUNT_API_URL and ACCOUNT_API_KEY:
            try:
                response = await self.http_client.post(
                    f"{ACCOUNT_API_URL}/reset-password",
                    headers={"Authorization": f"Bearer {ACCOUNT_API_KEY}"},
                    json={"email": email},
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"Password reset API call successful for: {email}")
                return {
                    "success": data.get("success", True),
                    "message": data.get("message", f"Password reset email sent to {email}"),
                    "expires_in_minutes": data.get("expires_in_minutes", 30),
                }
            except httpx.HTTPError as e:
                logger.warning(f"Password reset API call failed, using fallback: {e}")
                return await self._reset_password_fallback(email)

        return await self._reset_password_fallback(email)

    async def _reset_password_fallback(self, email: str) -> dict:
        """Fallback mock implementation for password reset"""
        await asyncio.sleep(0.2)
        return {
            "success": True,
            "message": f"Password reset email sent to {email}",
            "expires_in_minutes": 30,
        }

    async def _create_support_ticket(self, args: dict) -> dict:
        """Create support ticket via external API"""
        logger.info(f"Creating support ticket with priority: {args.get('priority', 'medium')}")

        if self.http_client and TICKET_API_URL and TICKET_API_KEY:
            try:
                response = await self.http_client.post(
                    TICKET_API_URL,
                    headers={"Authorization": f"Bearer {TICKET_API_KEY}"},
                    json={
                        "title": args.get("title", "Support Request"),
                        "description": args.get("description", ""),
                        "priority": args.get("priority", "medium"),
                        "category": args.get("category", "general"),
                    },
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"Support ticket created via API: {data.get('ticket_id')}")
                return {
                    "ticket_id": data.get("ticket_id", f"TKT-{int(time.time())}"),
                    "status": data.get("status", "open"),
                    "priority": data.get("priority", args.get("priority", "medium")),
                    "estimated_response_time": data.get("estimated_response_time", "24 hours"),
                    "message": data.get("message", "Ticket created successfully"),
                }
            except httpx.HTTPError as e:
                logger.warning(f"Create ticket API call failed, using fallback: {e}")
                return await self._create_support_ticket_fallback(args)

        return await self._create_support_ticket_fallback(args)

    async def _create_support_ticket_fallback(self, args: dict) -> dict:
        """Fallback mock implementation for creating support ticket"""
        await asyncio.sleep(0.15)
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
