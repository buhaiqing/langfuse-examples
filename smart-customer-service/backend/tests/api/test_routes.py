"""API 路由集成测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from backend.api.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestIntentRoutes:
    """意图识别路由测试"""

    def test_recognize_intent_success(self, client):
        """测试意图识别成功"""
        with patch("backend.api.v1.routes.intent.intent_service") as mock_service:
            mock_intent_result = MagicMock()
            mock_intent_result.intent = "api_error_troubleshooting"
            mock_intent_result.confidence = 0.95
            mock_intent_result.slots = {"error_code": "403"}
            mock_intent_result.entities = [{"type": "error_code", "value": "403"}]

            mock_service.recognize = AsyncMock(return_value=mock_intent_result)

            response = client.post(
                "/api/v1/intent/recognize",
                json={
                    "user_message": "我的 API 返回 403 错误",
                    "session_id": "test_123",
                    "user_id": "user_456",
                },
                headers={"X-API-Key": "default-service-key"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["intent"] == "api_error_troubleshooting"

    def test_recognize_intent_invalid_request(self, client):
        """测试无效请求"""
        response = client.post(
            "/api/v1/intent/recognize",
            json={
                "user_message": "",  # 空消息
                "session_id": "test_123",
            },
            headers={"X-API-Key": "default-service-key"},
        )

        # 应该返回错误（可能是验证错误或服务错误）
        assert response.status_code in [400, 422, 500]

    def test_list_intents(self, client):
        """测试获取意图列表"""
        response = client.get(
            "/api/v1/intent/intents", headers={"X-API-Key": "default-service-key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data


class TestRAGRoutes:
    """RAG 路由测试"""

    def test_query_rag_success(self, client):
        """测试 RAG 查询成功"""
        with patch("backend.api.v1.routes.rag.rag_service") as mock_service:
            mock_query_result = MagicMock()
            mock_query_result.answer = "这是答案"
            mock_query_result.documents = [{"content": "参考文档"}]
            mock_query_result.sources = ["doc.pdf"]
            mock_query_result.confidence = 0.9

            mock_service.query = AsyncMock(return_value=mock_query_result)

            response = client.post(
                "/api/v1/rag/query",
                json={"query": "如何解决 API 403 错误", "session_id": "test_123"},
                headers={"X-API-Key": "default-service-key"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["answer"] == "这是答案"

    def test_query_rag_empty_result(self, client):
        """测试 RAG 查询无结果"""
        with patch("backend.api.v1.routes.rag.rag_service") as mock_service:
            mock_query_result = MagicMock()
            mock_query_result.answer = "未找到相关信息"
            mock_query_result.documents = []
            mock_query_result.sources = []
            mock_query_result.confidence = 0.3

            mock_service.query = AsyncMock(return_value=mock_query_result)

            response = client.post(
                "/api/v1/rag/query",
                json={"query": "不相关的问题", "session_id": "test_123"},
                headers={"X-API-Key": "default-service-key"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["answer"] == "未找到相关信息"


class TestToolsRoutes:
    """工具调用路由测试"""

    def test_execute_tool_success(self, client):
        """测试工具执行成功"""
        with patch(
            "backend.api.v1.routes.tools._query_ticket_status", new_callable=AsyncMock
        ) as mock_tool:
            mock_tool.return_value = {"status": "open", "ticket_id": "TKT-123"}

            response = client.post(
                "/api/v1/tools/execute",
                json={
                    "tool_name": "query_ticket_status",
                    "parameters": {"ticket_id": "TKT-123"},
                    "session_id": "test_123",
                },
                headers={"X-API-Key": "default-service-key"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "open"

    def test_execute_tool_unknown_tool(self, client):
        """测试未知工具"""
        response = client.post(
            "/api/v1/tools/execute",
            json={"tool_name": "unknown_tool", "parameters": {}, "session_id": "test_123"},
            headers={"X-API-Key": "default-service-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "未知" in data["message"]

    def test_list_tools(self, client):
        """测试获取工具列表"""
        response = client.get("/api/v1/tools/list", headers={"X-API-Key": "default-service-key"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["tools"]) > 0


class TestConversationsRoutes:
    """会话管理路由测试"""

    def test_get_conversation_success(self, client):
        """测试获取会话成功"""
        with patch("backend.api.v1.routes.conversations.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            response = client.get(
                "/api/v1/conversations/test_123", headers={"X-API-Key": "default-service-key"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data

    def test_add_message_success(self, client):
        """测试添加消息成功"""
        with patch("backend.api.v1.routes.conversations.redis_client") as mock_redis:
            mock_redis.rpush = AsyncMock()

            response = client.post(
                "/api/v1/conversations/test_123/messages",
                json={"role": "user", "content": "新消息"},
                headers={"X-API-Key": "default-service-key"},
            )

            assert response.status_code == 200

    def test_delete_conversation_success(self, client):
        """测试删除会话成功"""
        with patch("backend.api.v1.routes.conversations.redis_client") as mock_redis:
            mock_redis.delete = AsyncMock()

            response = client.delete(
                "/api/v1/conversations/test_123", headers={"X-API-Key": "default-service-key"}
            )

            assert response.status_code == 200


class TestEscalationsRoutes:
    """升级管理路由测试"""

    def test_check_escalation_success(self, client):
        """测试升级检查成功"""
        with patch("backend.api.v1.routes.escalations.escalation_service") as mock_service:
            mock_service.check_escalation = AsyncMock(return_value=True)

            response = client.post(
                "/api/v1/escalations/check",
                json={
                    "session_id": "test_123",
                    "user_id": "user_456",
                    "intent_confidence": 0.3,
                    "user_message": "我要投诉",
                    "is_vip": True,
                },
                headers={"X-API-Key": "default-service-key"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["requires_escalation"] is True

    def test_get_escalation_queue(self, client):
        """测试获取升级队列"""
        with patch("backend.api.v1.routes.escalations.redis_client") as mock_redis:
            mock_redis.get_escalation_queue_size = AsyncMock(return_value=3)

            response = client.get(
                "/api/v1/escalations/queue", headers={"X-API-Key": "default-service-key"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["queue_size"] == 3

    def test_get_next_escalation_empty(self, client):
        """测试获取下一个升级（空队列）"""
        with patch("backend.api.v1.routes.escalations.redis_client") as mock_redis:
            mock_redis.get_next_escalation = AsyncMock(return_value=None)

            response = client.post(
                "/api/v1/escalations/queue/next", headers={"X-API-Key": "default-service-key"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


class TestDocumentsRoutes:
    """文档管理路由测试"""

    def test_upload_document_success(self, client, tmp_path):
        """测试上传文档成功"""
        # 创建临时文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("测试内容")

        with patch("backend.api.v1.routes.documents.rag_service") as mock_service:
            mock_result = MagicMock()
            mock_result.total_chunks = 5
            mock_result.metadata = {"successful_files": 1}
            mock_result.failed_files = []

            mock_service.import_documents = AsyncMock(return_value=mock_result)

            with open(test_file, "rb") as f:
                response = client.post(
                    "/api/v1/documents/upload",
                    files={"files": ("test.txt", f, "text/plain")},
                    data={"metadata": '{"category": "test"}'},
                    headers={"X-API-Key": "default-service-key"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total_chunks"] == 5

    def test_delete_document_success(self, client):
        """测试删除文档成功"""
        with patch("backend.api.v1.routes.documents.rag_service") as mock_service:
            mock_service.delete_documents = MagicMock()

            response = client.delete(
                "/api/v1/documents/doc_123", headers={"X-API-Key": "default-service-key"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_document_stats(self, client):
        """测试获取文档统计"""
        response = client.get(
            "/api/v1/documents/stats", headers={"X-API-Key": "default-service-key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data


class TestAuthMiddlewareIntegration:
    """认证中间件集成测试"""

    def test_request_without_api_key(self, client):
        """测试无 API Key 的请求"""
        response = client.get("/api/v1/conversations")

        assert response.status_code == 401

    def test_request_with_invalid_api_key(self, client):
        """测试无效 API Key"""
        response = client.get("/api/v1/conversations", headers={"X-API-Key": "invalid-key"})

        assert response.status_code == 401

    def test_request_with_valid_api_key(self, client):
        """测试有效 API Key"""
        response = client.get("/api/v1/conversations", headers={"X-API-Key": "default-service-key"})

        # 可能返回 200 或 500（如果 Redis 未连接），但认证应该通过
        assert response.status_code in [200, 500]

    def test_excluded_paths_no_auth_required(self, client):
        """测试排除路径不需要认证"""
        response = client.get("/health")

        assert response.status_code == 200

    def test_docs_no_auth_required(self, client):
        """测试文档页面不需要认证"""
        response = client.get("/docs")

        assert response.status_code == 200
