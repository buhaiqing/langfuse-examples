"""工具调用 API 路由"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from utils.api_client import api_client, JiraClient, ZendeskClient
from core.exceptions import (
    ToolExecutionFailed,
    ValidationException,
    ErrorCode,
)


router = APIRouter(prefix="/tools", tags=["工具调用"])


class ToolExecuteRequest(BaseModel):
    """工具执行请求"""

    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(..., description="工具参数")
    session_id: str = Field(..., description="会话 ID")


class ToolExecuteResponse(BaseModel):
    """工具执行响应"""

    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(request: ToolExecuteRequest):
    """
    工具调用接口

    支持的工具:
    - query_ticket_status: 查询工单状态
    - create_ticket: 创建工单
    - check_account_status: 检查账户状态
    - reset_password: 重置密码
    - get_product_info: 获取产品信息
    - check_service_status: 检查服务状态

    Raises:
        ValidationException: 参数验证失败
        ToolExecutionFailed: 工具执行失败
    """
    # 支持的工具列表
    supported_tools = {
        "query_ticket_status": _query_ticket_status,
        "check_account_status": _check_account_status,
        "get_product_info": _get_product_info,
    }

    # 检查工具是否存在
    if request.tool_name not in supported_tools:
        raise ValidationException(
            message=f"未知的工具：{request.tool_name}",
            details={"supported_tools": list(supported_tools.keys())},
        )

    try:
        # 执行工具
        tool_func = supported_tools[request.tool_name]
        result = await tool_func(request.parameters)

        return ToolExecuteResponse(
            success=True,
            data=result,
            message=None,
        )

    except Exception as e:
        # 转换为业务异常
        raise ToolExecutionFailed(
            tool_name=request.tool_name,
            message=str(e),
        )


async def _query_ticket_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """查询工单状态"""
    ticket_id = params.get("ticket_id")
    system = params.get("system", "jira")

    # TODO: 从配置读取 Jira/Zendesk 凭证
    if system == "jira":
        # client = JiraClient(...)
        # return await client.query_ticket(ticket_id)
        return {"status": "mock", "ticket_id": ticket_id}
    else:
        # client = ZendeskClient(...)
        # return await client.query_ticket(ticket_id)
        return {"status": "mock", "ticket_id": ticket_id}


async def _check_account_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """检查账户状态"""
    user_id = params.get("user_id")
    # TODO: 实现真实的账户系统对接
    return {
        "user_id": user_id,
        "status": "active",
        "account_type": "enterprise",
    }


async def _get_product_info(params: Dict[str, Any]) -> Dict[str, Any]:
    """获取产品信息"""
    product_name = params.get("product_name")
    # TODO: 实现真实的产品信息系统对接
    return {
        "product_name": product_name or "示例产品",
        "description": "这是一个示例产品",
        "price": "¥999/月",
    }


@router.get("/list")
async def list_tools():
    """获取所有可用工具"""
    return {
        "success": True,
        "data": {
            "tools": [
                {
                    "name": "query_ticket_status",
                    "description": "查询工单状态",
                    "parameters": ["ticket_id", "system"],
                },
                {
                    "name": "create_ticket",
                    "description": "创建工单",
                    "parameters": ["project", "summary", "description"],
                },
                {
                    "name": "check_account_status",
                    "description": "检查账户状态",
                    "parameters": ["user_id"],
                },
                {
                    "name": "reset_password",
                    "description": "重置密码",
                    "parameters": ["user_id", "channel"],
                },
                {
                    "name": "get_product_info",
                    "description": "获取产品信息",
                    "parameters": ["product_name"],
                },
                {
                    "name": "check_service_status",
                    "description": "检查服务状态",
                    "parameters": ["service_name"],
                },
            ],
        },
    }
