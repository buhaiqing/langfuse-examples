"""工具调用服务测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.services.tool_calling.service import ToolCallingService
from backend.adapters.account_adapter import AccountService
from backend.adapters.product_adapter import ProductService
from backend.adapters.monitoring_adapter import MonitoringService


class TestToolCallingService:
    """工具调用服务测试"""

    @pytest.fixture
    def tool_service(self):
        """创建工具调用服务实例"""
        return ToolCallingService()

    def test_init(self, tool_service):
        """测试初始化"""
        assert tool_service.tools is not None
        assert len(tool_service.tools) > 0

    def test_register_tool(self, tool_service):
        """测试注册工具"""
        mock_tool = AsyncMock()

        tool_service.register_tool("test_tool", mock_tool)

        assert "test_tool" in tool_service.tools

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, tool_service):
        """测试成功执行工具"""
        mock_tool = AsyncMock(return_value={"result": "success"})
        tool_service.register_tool("test_tool", mock_tool)

        result = await tool_service.execute_tool(
            tool_name="test_tool", parameters={"param1": "value1"}, session_id="sess_123"
        )

        assert result["success"] is True
        assert result["data"]["result"] == "success"
        mock_tool.assert_called_once_with(param1="value1")

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, tool_service):
        """测试工具不存在"""
        result = await tool_service.execute_tool(
            tool_name="nonexistent_tool", parameters={}, session_id="sess_123"
        )

        assert result["success"] is False
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_tool_with_error(self, tool_service):
        """测试工具执行错误"""
        mock_tool = AsyncMock(side_effect=Exception("Tool error"))
        tool_service.register_tool("error_tool", mock_tool)

        result = await tool_service.execute_tool(
            tool_name="error_tool", parameters={}, session_id="sess_123"
        )

        assert result["success"] is False
        assert "error" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_tool_with_langfuse(self, tool_service):
        """测试工具执行 Langfuse 埋点"""
        mock_tool = AsyncMock(return_value={"result": "success"})
        tool_service.register_tool("test_tool", mock_tool)

        with patch("backend.services.tool_calling.service.create_span") as mock_span:
            mock_span.return_value.__enter__ = MagicMock()
            mock_span.return_value.__exit__ = MagicMock()

            await tool_service.execute_tool(
                tool_name="test_tool", parameters={}, session_id="sess_123"
            )

            mock_span.assert_called()


class TestAccountAdapter:
    """账户适配器测试"""

    @pytest.fixture
    def account_service(self):
        """创建账户服务实例"""
        return AccountService(base_url="https://account.example.com")

    @pytest.mark.asyncio
    async def test_check_account_status(self, account_service):
        """测试检查账户状态"""
        with patch.object(
            account_service.client, "check_account_status", new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = {
                "user_id": "user_123",
                "status": "active",
                "account_type": "enterprise",
            }

            result = await account_service.check_status("user_123")

            assert result["status"] == "active"
            assert result["account_type"] == "enterprise"

    @pytest.mark.asyncio
    async def test_reset_password(self, account_service):
        """测试重置密码"""
        with patch.object(
            account_service.client, "reset_password", new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = {"success": True, "message": "Password reset email sent"}

            result = await account_service.reset_password("user_123", channel="email")

            assert result["success"] is True
            mock_method.assert_called_once_with("user_123", channel="email")

    @pytest.mark.asyncio
    async def test_update_profile(self, account_service):
        """测试更新用户资料"""
        with patch.object(
            account_service.client, "update_profile", new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = {"updated": True, "profile": {"name": "New Name"}}

            result = await account_service.client.update_profile("user_123", {"name": "New Name"})

            assert result["updated"] is True


class TestProductAdapter:
    """产品适配器测试"""

    @pytest.fixture
    def product_service(self):
        """创建产品服务实例"""
        return ProductService(base_url="https://product.example.com")

    @pytest.mark.asyncio
    async def test_get_product_info_cached(self, product_service):
        """测试获取产品信息（缓存）"""
        product_service.redis = MagicMock()
        product_service.redis.get = AsyncMock(return_value=str({"name": "Cached Product"}))

        result = await product_service.get_product_info("product_123")

        assert result["name"] == "Cached Product"
        product_service.redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_product_info_from_api(self, product_service):
        """测试从 API 获取产品信息"""
        product_service.redis = MagicMock()
        product_service.redis.get = AsyncMock(return_value=None)
        product_service.redis.setex = AsyncMock()

        with patch.object(
            product_service.client, "get_product_info", new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = {"name": "API Product", "price": "$99"}

            result = await product_service.get_product_info("product_123")

            assert result["name"] == "API Product"
            product_service.redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, product_service):
        """测试使缓存失效"""
        product_service.redis = MagicMock()
        product_service.redis.delete = AsyncMock()

        await product_service.invalidate_cache("product_123")

        product_service.redis.delete.assert_called_once()


class TestMonitoringAdapter:
    """监控适配器测试"""

    @pytest.fixture
    def monitoring_service(self):
        """创建监控服务实例"""
        return MonitoringService(prometheus_url="http://prometheus:9090")

    @pytest.mark.asyncio
    async def test_check_service_status_up(self, monitoring_service):
        """测试服务状态检查（运行中）"""
        with patch.object(
            monitoring_service.prometheus, "query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = {
                "data": {"result": [{"metric": {"service": "api"}, "value": [1234567890, "1"]}]}
            }

            result = await monitoring_service.check_service_status("api")

            assert result["status"] == "up"
            assert result["service_name"] == "api"

    @pytest.mark.asyncio
    async def test_check_service_status_down(self, monitoring_service):
        """测试服务状态检查（宕机）"""
        with patch.object(
            monitoring_service.prometheus, "query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = {"data": {"result": []}}

            result = await monitoring_service.check_service_status("api")

            assert result["status"] == "down"

    @pytest.mark.asyncio
    async def test_get_recent_alerts(self, monitoring_service):
        """测试获取最近告警"""
        with patch.object(
            monitoring_service.prometheus, "query_range", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = {
                "data": {
                    "result": [
                        {
                            "metric": {"alertname": "HighCPU", "severity": "critical"},
                            "values": [[1234567890, "1"]],
                        }
                    ]
                }
            }

            alerts = await monitoring_service.get_recent_alerts(hours=24)

            assert len(alerts) > 0
            assert alerts[0]["alert_name"] == "HighCPU"
            assert alerts[0]["severity"] == "critical"
