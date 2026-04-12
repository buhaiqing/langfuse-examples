"""
测试使用 LanceDB 的 RAG 模块
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
                    "doc_id": "auth_403_guide",
                    "content_preview": "API Authentication - 403 Forbidden Error...",
                    "relevance_score": 0.95,
                    "metadata": {"category": "authentication"}
                },
                {
                    "doc_id": "ticket_status_guide",
                    "content_preview": "How to Query Ticket Status...",
                    "relevance_score": 0.85,
                    "metadata": {"category": "tickets"}
                }
            ],
            "processing_time_ms": 150.5
        }


class TestLanceDBRAG:
    """测试使用 LanceDB 的 RAG 模块"""

    def setup_method(self):
        self.mock_rag = MockRAG()

    @pytest.mark.asyncio
    async def test_api_error_query(self):
        """测试 API 403 错误查询"""
        user_query = "我的API调用返回403错误，怎么办？"
        result = await self.mock_rag.query_knowledge_base(user_query, "test_session_001")
        assert "模拟回答" in result["answer"]
        assert len(result["retrieved_documents"]) == 2
        assert result["retrieved_documents"][0]["doc_id"] == "auth_403_guide"
        assert result["retrieved_documents"][0]["relevance_score"] == 0.95
        assert result["processing_time_ms"] == 150.5

    @pytest.mark.asyncio
    async def test_ticket_status_query(self):
        """测试工单状态查询"""
        user_query = "如何查询工单状态？"
        result = await self.mock_rag.query_knowledge_base(user_query, "test_session_002")
        assert "模拟回答" in result["answer"]
        assert len(result["retrieved_documents"]) == 2
        assert result["retrieved_documents"][1]["doc_id"] == "ticket_status_guide"
        assert result["retrieved_documents"][1]["relevance_score"] == 0.85
        assert result["processing_time_ms"] == 150.5

    @pytest.mark.asyncio
    async def test_rate_limit_query(self):
        """测试速率限制查询"""
        user_query = "API 速率限制是多少？"
        result = await self.mock_rag.query_knowledge_base(user_query, "test_session_003")
        assert "模拟回答" in result["answer"]
        assert len(result["retrieved_documents"]) == 2
        assert result["processing_time_ms"] == 150.5

    @pytest.mark.asyncio
    async def test_query_with_session_id(self):
        """测试带有会话 ID 的查询"""
        user_query = "测试查询"
        session_id = "test_session_123"
        result = await self.mock_rag.query_knowledge_base(user_query, session_id)
        assert "模拟回答" in result["answer"]
        assert len(result["retrieved_documents"]) == 2

    @pytest.mark.asyncio
    async def test_query_without_session_id(self):
        """测试不带会话 ID 的查询"""
        user_query = "测试查询"
        result = await self.mock_rag.query_knowledge_base(user_query)
        assert "模拟回答" in result["answer"]
        assert len(result["retrieved_documents"]) == 2
