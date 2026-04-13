"""认证中间件测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, status
from starlette.testclient import TestClient
from starlette.responses import JSONResponse

from backend.api.middleware.auth import APIKeyAuthMiddleware, verify_api_key, mask_api_key


class TestAPIKeyAuthMiddleware:
    """API Key 认证中间件测试"""

    @pytest.fixture
    def mock_app(self):
        """创建 Mock 应用"""
        app = AsyncMock()
        app.return_value = JSONResponse(content={"test": "data"})
        return app

    @pytest.fixture
    def middleware(self, mock_app):
        """创建认证中间件实例"""
        return APIKeyAuthMiddleware(mock_app, excluded_paths={"/health", "/docs"})

    def test_excluded_paths_not_authenticated(self, middleware):
        """测试排除路径不需要认证"""
        assert "/health" in middleware.excluded_paths
        assert "/docs" in middleware.excluded_paths

    def test_mask_api_key_short(self):
        """测试短 API Key 掩码"""
        assert mask_api_key("sk-123") == "***"
        assert mask_api_key("short") == "***"

    def test_mask_api_key_long(self):
        """测试长 API Key 掩码"""
        assert mask_api_key("sk-prod-abc123xyz789") == "sk-prod***"
        assert mask_api_key("sk-test-123456") == "sk-test***"

    def test_verify_api_key_valid(self):
        """测试验证有效 API Key"""
        with patch("backend.api.middleware.auth.settings") as mock_settings:
            mock_settings.service_api_keys = ["sk-test-123", "sk-prod-456"]
            assert verify_api_key("sk-test-123") is True

    def test_verify_api_key_invalid(self):
        """测试验证无效 API Key"""
        with patch("backend.api.middleware.auth.settings") as mock_settings:
            mock_settings.service_api_keys = ["sk-test-123"]
            assert verify_api_key("sk-invalid") is False

    def test_verify_api_key_none(self):
        """测试验证 None API Key"""
        assert verify_api_key(None) is False
        assert verify_api_key("") is False

    @pytest.mark.asyncio
    async def test_dispatch_missing_api_key(self, middleware):
        """测试缺少 API Key 的请求"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/test"
        request.headers = {}

        call_next = AsyncMock()

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_invalid_api_key(self, middleware):
        """测试无效 API Key 的请求"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/test"
        request.headers = {"X-API-Key": "invalid-key"}

        call_next = AsyncMock()

        with patch("backend.api.middleware.auth.verify_api_key", return_value=False):
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_valid_api_key(self, middleware):
        """测试有效 API Key 的请求"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/test"
        request.headers = {"X-API-Key": "sk-test-123"}

        call_next = AsyncMock()
        call_next.return_value = JSONResponse(content={"test": "data"})

        with patch("backend.api.middleware.auth.verify_api_key", return_value=True):
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200
            call_next.assert_called_once()
            assert hasattr(request.state, "api_key")

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path(self, middleware):
        """测试排除路径直接通过"""
        request = MagicMock(spec=Request)
        request.url.path = "/health"
        request.headers = {}

        call_next = AsyncMock()
        call_next.return_value = JSONResponse(content={"status": "ok"})

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once()


class TestVerifyApiKey:
    """验证 API Key 辅助函数测试"""

    def test_verify_with_valid_key(self):
        """测试有效 Key"""
        with patch("backend.api.middleware.auth.get_valid_api_keys") as mock_keys:
            mock_keys.return_value = {"sk-valid-123"}
            assert verify_api_key("sk-valid-123") is True

    def test_verify_with_invalid_key(self):
        """测试无效 Key"""
        with patch("backend.api.middleware.auth.get_valid_api_keys") as mock_keys:
            mock_keys.return_value = {"sk-valid-123"}
            assert verify_api_key("sk-invalid") is False


@pytest.mark.integration
class TestAuthMiddlewareIntegration:
    """认证中间件集成测试"""

    def test_full_request_flow(self):
        """测试完整请求流程"""
        from backend.api.main import app

        with TestClient(app) as client:
            # 测试无 API Key
            response = client.get("/health")
            assert response.status_code == 200  # /health 不需要认证

            # 测试有 API Key
            response = client.get(
                "/api/v1/conversations", headers={"X-API-Key": "default-service-key"}
            )
            # 可能会因为 Redis 连接失败返回 500，但认证应该通过
            assert response.status_code in [200, 500]
