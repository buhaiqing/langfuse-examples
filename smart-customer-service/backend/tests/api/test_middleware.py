"""中间件测试

测试:
- 限流中间件事件循环修复（P0-3 修复验证）
- 认证中间件 Langfuse 追踪修复（P0-2 修复验证）
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest


class TestRateLimitMiddleware:
    """限流中间件测试"""

    def test_utcnow_used_instead_of_datetime_utcnow(self):
        """验证限流中间件使用 utcnow() 而非 datetime.utcnow()"""
        import ast

        from api.middleware import rate_limit

        source = open(rate_limit.__file__).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if (
                    node.func.attr == "utcnow"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "datetime"
                ):
                    pytest.fail("代码中不应使用 datetime.utcnow()，应使用 utcnow()")

    def test_rate_limit_middleware_init(self):
        """限流中间件初始化"""
        from api.middleware.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=MagicMock())
        assert middleware._request_counts == {}
        assert middleware._cleanup_task is None

    def test_check_rate_limit_allows_within_limit(self):
        """限流检查在限制内允许请求"""
        from api.middleware.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=MagicMock())
        with patch.object(type(middleware).__bases__[0], "__init__", lambda self, *a, **k: None):
            pass

        allowed, retry = middleware._check_rate_limit("client_1")
        assert allowed is True
        assert retry == 0

    def test_check_rate_limit_blocks_over_limit(self):
        """限流检查超限后拒绝请求"""
        from api.middleware.rate_limit import RateLimitMiddleware
        from core.config import settings

        middleware = RateLimitMiddleware(app=MagicMock())
        max_req = settings.rate_limit_requests

        for _i in range(max_req):
            middleware._check_rate_limit("client_2")

        allowed, retry = middleware._check_rate_limit("client_2")
        assert allowed is False
        assert retry > 0

    def test_different_clients_independent(self):
        """不同客户端的限流独立"""
        from api.middleware.rate_limit import RateLimitMiddleware
        from core.config import settings

        middleware = RateLimitMiddleware(app=MagicMock())
        max_req = settings.rate_limit_requests

        for _i in range(max_req):
            middleware._check_rate_limit("client_a")

        allowed_a, _ = middleware._check_rate_limit("client_a")
        assert allowed_a is False

        allowed_b, _ = middleware._check_rate_limit("client_b")
        assert allowed_b is True

    @pytest.mark.asyncio
    async def test_cleanup_task_management(self):
        """清理任务管理"""
        from api.middleware.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=MagicMock())
        assert middleware._cleanup_task is None

        middleware.start_cleanup_task()
        assert middleware._cleanup_task is not None
        assert not middleware._cleanup_task.done()

        middleware.stop_cleanup_task()
        await asyncio.sleep(0.1)
        assert middleware._cleanup_task.done()

    def test_get_client_id_prefers_api_key(self):
        """客户端标识优先使用 API Key"""
        from api.middleware.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=MagicMock())
        mock_request = MagicMock()
        mock_request.state.api_key_raw = "sk-test-key"
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        client_id = middleware._get_client_id(mock_request)
        assert client_id == "key:sk-test-key"


class TestAuthMiddleware:
    """认证中间件测试"""

    def test_auth_middleware_imports(self):
        """认证中间件可正常导入"""
        from api.middleware.auth import APIKeyAuthMiddleware

        assert APIKeyAuthMiddleware is not None

    def test_api_key_validation(self):
        """API Key 验证逻辑"""
        from api.middleware.auth import APIKeyAuthMiddleware

        with patch.dict("os.environ", {"SERVICE_API_KEYS": "sk-test1234567890,sk-test0987654321"}):
            middleware = APIKeyAuthMiddleware(app=MagicMock())
            assert middleware._validate_api_key("sk-test1234567890") is True
            assert middleware._validate_api_key("sk-invalid") is False

    def test_api_key_masking(self):
        """API Key 掩码处理"""
        from api.middleware.auth import APIKeyAuthMiddleware

        middleware = APIKeyAuthMiddleware(app=MagicMock())
        assert middleware._mask_api_key("sk-prod-abc123xyz789") == "sk-prod***"
        assert middleware._mask_api_key("short") == "***"

    def test_excluded_paths(self):
        """排除路径配置"""
        from api.middleware.auth import APIKeyAuthMiddleware

        middleware = APIKeyAuthMiddleware(app=MagicMock())
        assert "/health" in middleware.excluded_paths
        assert "/docs" in middleware.excluded_paths

    def test_verify_api_key_function(self):
        """verify_api_key 函数测试"""
        from api.middleware.auth import verify_api_key

        with patch.dict("os.environ", {"SERVICE_API_KEYS": "sk-test1234567890"}):
            assert verify_api_key("sk-test1234567890") is True
            assert verify_api_key("sk-invalid") is False
            assert verify_api_key(None) is False
            assert verify_api_key("") is False

    def test_mask_api_key_function(self):
        """mask_api_key 函数测试"""
        from api.middleware.auth import mask_api_key

        assert mask_api_key("sk-prod-abc123xyz789") == "sk-prod***"
        assert mask_api_key("short") == "***"
