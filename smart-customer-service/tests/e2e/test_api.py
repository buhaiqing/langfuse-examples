"""
API 基础功能测试

测试所有 API 端点的基本功能：
1. 健康检查
2. 意图识别 API
3. RAG API
4. 工具调用 API
5. 会话管理 API
6. 升级管理 API
7. 数据分析 API
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from conftest import (
    BASE_URL,
    API_KEY,
)


class TestHealthCheck:
    """健康检查测试"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, http_client):
        """测试健康检查端点"""
        response = await http_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]

    @pytest.mark.asyncio
    async def test_health_redis_status(self, http_client):
        """测试 Redis 状态"""
        response = await http_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "redis" in data
        assert data["redis"] in ["connected", "disconnected"]


class TestIntentAPI:
    """意图识别 API 测试"""

    @pytest.mark.asyncio
    async def test_recognize_intent_endpoint(self, http_client, api_headers):
        """测试意图识别端点"""
        response = await http_client.post(
            "/api/v1/intent/recognize",
            json={
                "user_message": "我想查询工单状态",
                "session_id": "test_session",
                "user_id": "test_user",
            },
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    @pytest.mark.asyncio
    async def test_list_intents_endpoint(self, http_client, api_headers):
        """测试获取意图列表"""
        response = await http_client.get(
            "/api/v1/intent/intents",
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        if data["success"]:
            assert "data" in data

    @pytest.mark.asyncio
    async def test_intent_with_context(self, http_client, api_headers):
        """测试带上下文的意图识别"""
        response = await http_client.post(
            "/api/v1/intent/recognize",
            json={
                "user_message": "是的，请帮我查一下",
                "session_id": "test_session",
                "user_id": "test_user",
                "context": {
                    "previous_intent": "query_ticket",
                    "slots": {"ticket_id": "T-12345"},
                },
            },
            headers=api_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_intent_empty_message(self, http_client, api_headers):
        """测试空消息"""
        response = await http_client.post(
            "/api/v1/intent/recognize",
            json={
                "user_message": "",
                "session_id": "test_session",
                "user_id": "test_user",
            },
            headers=api_headers,
        )

        # 空消息应该被拒绝
        assert response.status_code in [400, 422]


class TestRAGAPI:
    """RAG API 测试"""

    @pytest.mark.asyncio
    async def test_rag_query_endpoint(self, http_client, api_headers):
        """测试 RAG 查询端点"""
        response = await http_client.post(
            "/api/v1/rag/query",
            json={
                "query": "产品功能介绍",
                "session_id": "test_session",
                "top_k": 3,
            },
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    @pytest.mark.asyncio
    async def test_rag_query_with_filters(self, http_client, api_headers):
        """测试带过滤条件的 RAG 查询"""
        response = await http_client.post(
            "/api/v1/rag/query",
            json={
                "query": "价格信息",
                "session_id": "test_session",
                "top_k": 5,
                "filters": {
                    "category": "pricing",
                    "language": "zh",
                },
            },
            headers=api_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rag_list_documents(self, http_client, api_headers):
        """测试文档列表"""
        response = await http_client.get(
            "/api/v1/rag/documents",
            headers=api_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rag_query_empty(self, http_client, api_headers):
        """测试空查询"""
        response = await http_client.post(
            "/api/v1/rag/query",
            json={
                "query": "",
                "session_id": "test_session",
                "top_k": 3,
            },
            headers=api_headers,
        )

        assert response.status_code in [400, 422]


class TestToolsAPI:
    """工具调用 API 测试"""

    @pytest.mark.asyncio
    async def test_execute_tool_endpoint(self, http_client, api_headers):
        """测试工具执行端点"""
        response = await http_client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "check_account_status",
                "parameters": {"user_id": "test_user"},
                "session_id": "test_session",
            },
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    @pytest.mark.asyncio
    async def test_list_tools_endpoint(self, http_client, api_headers):
        """测试获取工具列表"""
        response = await http_client.get(
            "/api/v1/tools/list",
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

        if data["success"]:
            tools = data["data"]["tools"]
            assert len(tools) > 0

            # 验证工具结构
            for tool in tools:
                assert "name" in tool
                assert "description" in tool
                assert "parameters" in tool

    @pytest.mark.asyncio
    async def test_query_ticket_status_tool(self, http_client, api_headers):
        """测试查询工单状态工具"""
        response = await http_client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "query_ticket_status",
                "parameters": {
                    "ticket_id": "T-12345",
                    "system": "jira",
                },
                "session_id": "test_session",
            },
            headers=api_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_product_info_tool(self, http_client, api_headers):
        """测试获取产品信息工具"""
        response = await http_client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "get_product_info",
                "parameters": {"product_name": "智能客服系统"},
                "session_id": "test_session",
            },
            headers=api_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unknown_tool(self, http_client, api_headers):
        """测试未知工具"""
        response = await http_client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "unknown_tool",
                "parameters": {},
                "session_id": "test_session",
            },
            headers=api_headers,
        )

        assert response.status_code in [400, 404, 422]


class TestConversationAPI:
    """会话管理 API 测试"""

    @pytest.mark.asyncio
    async def test_create_conversation(self, http_client, api_headers):
        """测试创建会话"""
        response = await http_client.post(
            "/api/v1/conversations",
            json={"user_id": "test_user"},
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_conversation(self, http_client, api_headers):
        """测试获取会话"""
        response = await http_client.get(
            "/api/v1/conversations/test_session",
            headers=api_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_add_message(self, http_client, api_headers):
        """测试添加消息"""
        response = await http_client.post(
            "/api/v1/conversations/test_session/messages",
            json={
                "role": "user",
                "content": "测试消息内容",
            },
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_conversations(self, http_client, api_headers):
        """测试会话列表"""
        response = await http_client.get(
            "/api/v1/conversations",
            params={"limit": 10, "offset": 0},
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_delete_conversation(self, http_client, api_headers):
        """测试删除会话"""
        response = await http_client.delete(
            "/api/v1/conversations/test_session",
            headers=api_headers,
        )

        assert response.status_code == 200


class TestEscalationAPI:
    """升级管理 API 测试"""

    @pytest.mark.asyncio
    async def test_check_escalation(self, http_client, api_headers):
        """测试升级检查"""
        response = await http_client.post(
            "/api/v1/escalations/check",
            json={
                "session_id": "test_session",
                "user_id": "test_user",
                "intent_confidence": 0.3,
                "user_message": "我不理解",
                "is_vip": False,
            },
            headers=api_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_escalation_queue(self, http_client, api_headers):
        """测试升级队列"""
        response = await http_client.get(
            "/api/v1/escalations/queue",
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "queue_size" in data["data"]

    @pytest.mark.asyncio
    async def test_get_next_escalation(self, http_client, api_headers):
        """测试获取下一个升级"""
        response = await http_client.post(
            "/api/v1/escalations/queue/next",
            headers=api_headers,
        )

        assert response.status_code == 200


class TestAnalyticsAPI:
    """数据分析 API 测试"""

    @pytest.mark.asyncio
    async def test_analytics_overview(self, http_client, api_headers):
        """测试概览统计"""
        response = await http_client.get(
            "/api/v1/analytics/overview",
            params={"days": 7},
            headers=api_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_intent_distribution(self, http_client, api_headers):
        """测试意图分布"""
        response = await http_client.get(
            "/api/v1/analytics/intent-distribution",
            headers=api_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_agent_performance(self, http_client, api_headers):
        """测试客服绩效"""
        response = await http_client.get(
            "/api/v1/analytics/agent-performance",
            params={"days": 30},
            headers=api_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_realtime_metrics(self, http_client, api_headers):
        """测试实时指标"""
        response = await http_client.get(
            "/api/v1/analytics/realtime",
            headers=api_headers,
        )

        assert response.status_code == 200


class TestAPIDocumentation:
    """API 文档测试"""

    @pytest.mark.asyncio
    async def test_openapi_docs(self, http_client):
        """测试 OpenAPI 文档"""
        response = await http_client.get("/docs")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_json(self, http_client):
        """测试 OpenAPI JSON"""
        response = await http_client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    @pytest.mark.asyncio
    async def test_redoc(self, http_client):
        """测试 ReDoc"""
        response = await http_client.get("/redoc")

        assert response.status_code == 200