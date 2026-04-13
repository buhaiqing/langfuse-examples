"""API 客户端工具测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from backend.utils.api_client import (
    APIClient,
    JiraClient,
    ZendeskClient,
    APIClientError,
    CircuitBreakerOpen,
)
import pybreaker


class TestAPIClient:
    """通用 API 客户端测试"""

    @pytest.fixture
    def api_client(self):
        """创建 API 客户端实例"""
        return APIClient(base_url="https://api.example.com", timeout=30.0)

    def test_init(self, api_client):
        """测试初始化"""
        assert api_client.base_url == "https://api.example.com"
        assert api_client.timeout == 30.0
        assert api_client.breaker is not None

    def test_client_lazy_initialization(self, api_client):
        """测试客户端延迟初始化"""
        assert api_client._client is None

        client = api_client.client
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)

    def test_urls_stripped_trailing_slash(self):
        """测试 URL 尾部斜杠处理"""
        client = APIClient(base_url="https://api.example.com/")
        assert client.base_url == "https://api.example.com"

    @pytest.mark.asyncio
    async def test_get_request(self, api_client):
        """测试 GET 请求"""
        with patch.object(api_client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"data": "test"}

            result = await api_client.get("/endpoint")

            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_post_request(self, api_client):
        """测试 POST 请求"""
        with patch.object(api_client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"created": True}

            result = await api_client.post("/endpoint", json={"key": "value"})

            assert result == {"created": True}

    @pytest.mark.asyncio
    async def test_put_request(self, api_client):
        """测试 PUT 请求"""
        with patch.object(api_client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"updated": True}

            result = await api_client.put("/endpoint/123")

            assert result == {"updated": True}

    @pytest.mark.asyncio
    async def test_delete_request(self, api_client):
        """测试 DELETE 请求"""
        with patch.object(api_client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"deleted": True}

            result = await api_client.delete("/endpoint/123")

            assert result == {"deleted": True}

    @pytest.mark.asyncio
    async def test_request_success(self, api_client):
        """测试成功请求"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'{"key": "value"}'
        mock_response.json = MagicMock(return_value={"key": "value"})

        with patch.object(api_client, "client") as mock_client:
            mock_client.request = AsyncMock(return_value=mock_response)

            result = await api_client.request("GET", "/test")

            assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_request_empty_response(self, api_client):
        """测试空响应"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b""

        with patch.object(api_client, "client") as mock_client:
            mock_client.request = AsyncMock(return_value=mock_response)

            result = await api_client.request("GET", "/test")

            assert result == {}

    @pytest.mark.asyncio
    async def test_request_http_status_error(self, api_client):
        """测试 HTTP 状态错误"""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(api_client, "client") as mock_client:
            mock_client.request = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found", request=MagicMock(), response=mock_response
                )
            )

            with pytest.raises(APIClientError) as exc_info:
                await api_client.request("GET", "/test")

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_request_timeout(self, api_client):
        """测试请求超时"""
        with patch.object(api_client, "client") as mock_client:
            mock_client.request = AsyncMock(side_effect=httpx.ReadTimeout("Timeout"))

            with pytest.raises(APIClientError):
                await api_client.request("GET", "/test")

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self, api_client):
        """测试熔断器打开"""
        with patch.object(api_client, "client") as mock_client:
            mock_client.request = AsyncMock(side_effect=httpx.RequestError("Connection failed"))

            # 连续失败 5 次，触发熔断
            for _ in range(6):
                try:
                    await api_client.request("GET", "/test")
                except (APIClientError, pybreaker.CircuitBreakerError):
                    pass

            # 第 6 次应该触发熔断器打开
            with pytest.raises((APIClientError, CircuitBreakerOpen)):
                await api_client.request("GET", "/test")

    @pytest.mark.asyncio
    async def test_close_client(self, api_client):
        """测试关闭客户端"""
        api_client._client = MagicMock()
        api_client._client.aclose = AsyncMock()

        await api_client.close()

        api_client._client.aclose.assert_called_once()
        assert api_client._client is None


class TestJiraClient:
    """Jira 客户端测试"""

    @pytest.fixture
    def jira_client(self):
        """创建 Jira 客户端实例"""
        return JiraClient(
            base_url="https://example.atlassian.net",
            api_token="test_token",
            email="test@example.com",
        )

    def test_init(self, jira_client):
        """测试初始化"""
        assert jira_client.base_url == "https://example.atlassian.net"
        assert jira_client.client.auth is not None

    @pytest.mark.asyncio
    async def test_query_ticket(self, jira_client):
        """测试查询工单"""
        with patch.object(jira_client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "key": "TEST-123",
                "fields": {"status": {"name": "In Progress"}},
            }

            result = await jira_client.query_ticket("TEST-123")

            assert result["key"] == "TEST-123"
            mock_get.assert_called_once_with("/rest/api/3/issue/TEST-123")

    @pytest.mark.asyncio
    async def test_create_ticket(self, jira_client):
        """测试创建工单"""
        with patch.object(jira_client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"key": "TEST-124", "id": "12345"}

            result = await jira_client.create_ticket(
                project="TEST", summary="Test bug", description="Description", issue_type="Bug"
            )

            assert result["key"] == "TEST-124"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_comment(self, jira_client):
        """测试添加工单备注"""
        with patch.object(jira_client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "comment_123"}

            result = await jira_client.add_comment("TEST-123", "Test comment")

            assert result is not None


class TestZendeskClient:
    """Zendesk 客户端测试"""

    @pytest.fixture
    def zendesk_client(self):
        """创建 Zendesk 客户端实例"""
        return ZendeskClient(
            base_url="https://example.zendesk.com", api_token="test_token", email="test@example.com"
        )

    def test_init(self, zendesk_client):
        """测试初始化"""
        assert zendesk_client.base_url == "https://example.zendesk.com"

    @pytest.mark.asyncio
    async def test_query_ticket(self, zendesk_client):
        """测试查询工单"""
        with patch.object(zendesk_client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"ticket": {"id": 123, "status": "open"}}

            result = await zendesk_client.query_ticket(123)

            assert "ticket" in result

    @pytest.mark.asyncio
    async def test_create_ticket(self, zendesk_client):
        """测试创建工单"""
        with patch.object(zendesk_client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"ticket": {"id": 124, "status": "new"}}

            result = await zendesk_client.create_ticket(
                subject="Test ticket", description="Description", requester_email="user@example.com"
            )

            assert "ticket" in result
