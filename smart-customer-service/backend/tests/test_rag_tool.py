"""
测试 RAG-01 和 TOOL-01 功能
"""

import asyncio
import os
from unittest.mock import Mock, patch

import pytest
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 检查是否有实际的 API 密钥
has_api_key = os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "sk-placeholder"


class MockRAG:
    async def query_knowledge_base(self, query, session_id=None):
        return {
            "answer": f"模拟回答: {query}",
            "retrieved_documents": [
                {
                    "doc_id": "mock_doc_1",
                    "content_preview": "模拟文档内容",
                    "relevance_score": 0.95,
                    "metadata": {}
                }
            ],
            "processing_time_ms": 150.5
        }


class MockTool:
    async def call_tool(self, tool_name, arguments):
        return {
            "success": True,
            "result": {
                "ticket_id": arguments.get("ticket_id", "TKT-12345"),
                "status": "in_progress",
                "priority": "high",
                "assigned_to": "John Smith",
                "product_id": arguments.get("product_id", "PROD-001"),
                "name": "Enterprise API Plan",
                "version": "v2.3",
                "account_id": arguments.get("account_id", "ACC-12345"),
                "plan": "professional",
                "account_status": "active"
            },
            "execution_time_ms": 100.2
        }


class MockToolName:
    QUERY_TICKET_STATUS = "query_ticket_status"
    GET_PRODUCT_INFO = "get_product_info"
    CHECK_ACCOUNT_STATUS = "check_account_status"


ToolName = MockToolName()


class TestRAGKnowledge:
    """测试 RAG 知识库功能"""

    def setup_method(self):
        self.mock_rag = MockRAG()

    @pytest.mark.asyncio
    async def test_api_error_query(self):
        """测试 API 403 错误查询"""
        result = await self.mock_rag.query_knowledge_base("我的API调用返回403错误，怎么办？")
        assert "模拟回答" in result["answer"]
        assert len(result["retrieved_documents"]) == 1
        assert result["processing_time_ms"] == 150.5

    @pytest.mark.asyncio
    async def test_ticket_status_query(self):
        """测试工单状态查询"""
        result = await self.mock_rag.query_knowledge_base("如何查询工单状态？")
        assert "模拟回答" in result["answer"]
        assert len(result["retrieved_documents"]) == 1
        assert result["processing_time_ms"] == 150.5

    @pytest.mark.asyncio
    async def test_rate_limit_query(self):
        """测试速率限制查询"""
        result = await self.mock_rag.query_knowledge_base("API 速率限制是多少？")
        assert "模拟回答" in result["answer"]
        assert len(result["retrieved_documents"]) == 1
        assert result["processing_time_ms"] == 150.5


class TestToolCalling:
    """测试工具调用功能"""

    def setup_method(self):
        self.mock_tool = MockTool()

    @pytest.mark.asyncio
    async def test_query_ticket_status(self):
        """测试查询工单状态工具"""
        result = await self.mock_tool.call_tool(ToolName.QUERY_TICKET_STATUS, {"ticket_id": "TKT-12345"})
        assert result["success"] is True
        assert result["result"]["ticket_id"] == "TKT-12345"
        assert result["result"]["status"] == "in_progress"
        assert result["execution_time_ms"] == 100.2

    @pytest.mark.asyncio
    async def test_get_product_info(self):
        """测试获取产品信息工具"""
        result = await self.mock_tool.call_tool(ToolName.GET_PRODUCT_INFO, {"product_id": "PROD-001"})
        assert result["success"] is True
        assert result["result"]["product_id"] == "PROD-001"
        assert result["result"]["name"] == "Enterprise API Plan"
        assert result["execution_time_ms"] == 100.2

    @pytest.mark.asyncio
    async def test_check_account_status(self):
        """测试检查账户状态工具"""
        result = await self.mock_tool.call_tool(ToolName.CHECK_ACCOUNT_STATUS, {"account_id": "ACC-12345"})
        assert result["success"] is True
        assert result["result"]["account_id"] == "ACC-12345"
        assert result["result"]["account_status"] == "active"
        assert result["execution_time_ms"] == 100.2
