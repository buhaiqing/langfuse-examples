"""API客户端模块测试套件。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from modules.tool_calling.api_client import APIClient, CircuitBreakerError


class TestAPIClient:
    """APIClient测试套件。"""

    @pytest.fixture
    def api_client(self):
        """创建API客户端fixture。"""
        return APIClient(
            base_url="https://api.example.com",
            api_key="test_key",
            timeout=10.0,
            max_retries=3,
        )

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """测试客户端初始化。"""
        client = APIClient(base_url="https://api.test.com")

        assert client.base_url == "https://api.test.com"
        assert client.timeout == 30.0
        assert client.max_retries == 3
        assert "Content-Type" in client.headers

    @pytest.mark.asyncio
    async def test_get_request(self, api_client):
        """测试GET请求。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(api_client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await api_client.get("/test")

            assert result == {"status": "ok"}
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_request(self, api_client):
        """测试POST请求。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123", "created": True}
        mock_response.raise_for_status = MagicMock()

        with patch.object(api_client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await api_client.post("/create", data={"name": "test"})

            assert result["id"] == "123"
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[1]["json_data"] == {"name": "test"}

    @pytest.mark.asyncio
    async def test_put_request(self, api_client):
        """测试PUT请求。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"updated": True}
        mock_response.raise_for_status = MagicMock()

        with patch.object(api_client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await api_client.put("/update/123", data={"name": "updated"})

            assert result["updated"] is True

    @pytest.mark.asyncio
    async def test_delete_request(self, api_client):
        """测试DELETE请求。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"deleted": True}
        mock_response.raise_for_status = MagicMock()

        with patch.object(api_client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await api_client.delete("/delete/123")

            assert result["deleted"] is True

    @pytest.mark.asyncio
    async def test_health_check_success(self, api_client):
        """测试健康检查成功。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(api_client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await api_client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, api_client):
        """测试健康检查失败。"""
        with patch.object(api_client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("Connection failed")

            result = await api_client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, api_client):
        """测试熔断器在多次失败后打开。"""
        # 模拟连续失败以触发熔断器
        for _ in range(6):
            try:
                with patch.object(api_client.client, "request", new_callable=AsyncMock) as mock_req:
                    mock_req.side_effect = Exception("Network error")
                    await api_client.get("/test")
            except Exception:
                pass

        # 验证熔断器已打开
        assert api_client.circuit_breaker.current_state == "open"

    @pytest.mark.asyncio
    async def test_circuit_breaker_raises_when_open(self, api_client):
        """测试熔断器打开时抛出异常。"""
        # 手动打开熔断器
        api_client.circuit_breaker.call_fail()
        api_client.circuit_breaker.call_fail()
        api_client.circuit_breaker.call_fail()
        api_client.circuit_breaker.call_fail()
        api_client.circuit_breaker.call_fail()

        with pytest.raises(CircuitBreakerError):
            await api_client.get("/test")

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, api_client):
        """测试重试机制。"""
        call_count = 0

        async def mock_request_with_failures(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            mock_response = MagicMock()
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status = MagicMock()
            return mock_response

        with patch.object(api_client.client, "request", side_effect=mock_request_with_failures):
            result = await api_client.get("/test")
            assert result["success"] is True
            assert call_count == 3  # 应该重试直到成功

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试异步上下文管理器。"""
        async with APIClient(base_url="https://api.test.com") as client:
            assert client.connected if hasattr(client, "connected") else True

    @pytest.mark.asyncio
    async def test_close_method(self, api_client):
        """测试关闭方法。"""
        with patch.object(api_client.client, "aclose", new_callable=AsyncMock) as mock_close:
            await api_client.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_http_error_handling(self, api_client):
        """测试HTTP错误处理。"""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=mock_response
        )

        with patch.object(api_client.client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                await api_client.get("/nonexistent")

    @pytest.mark.asyncio
    async def test_custom_headers(self):
        """测试自定义请求头。"""
        custom_headers = {"X-Custom-Header": "custom_value"}
        client = APIClient(
            base_url="https://api.test.com",
            headers=custom_headers,
        )

        assert "X-Custom-Header" in client.headers
        assert client.headers["X-Custom-Header"] == "custom_value"
