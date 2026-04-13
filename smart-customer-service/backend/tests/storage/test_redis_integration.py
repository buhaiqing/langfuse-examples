"""Redis 集成测试"""

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from backend.storage.redis_client import redis_client, RedisKeys


class TestRateLimitRedis:
    """限流 Redis 测试"""

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self):
        """测试限流检查 - 允许通过"""
        client_id = "test_client_1"
        max_requests = 100
        window_seconds = 60

        is_allowed, retry_after = await redis_client.check_rate_limit(
            client_id, max_requests, window_seconds
        )

        assert is_allowed is True
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self):
        """测试限流检查 - 超过限制"""
        client_id = "test_client_2"
        max_requests = 5
        window_seconds = 60

        # 先添加一些请求
        key = RedisKeys.RATE_LIMIT.format(client_id=client_id)
        current_time = time.time()

        pipe = redis_client.client.pipeline()
        for i in range(10):
            pipe.zadd(key, {f"req_{i}": current_time - i})
        await pipe.execute()

        # 检查限流
        is_allowed, retry_after = await redis_client.check_rate_limit(
            client_id, max_requests, window_seconds
        )

        assert is_allowed is False
        assert retry_after > 0

        # 清理
        await redis_client.reset_rate_limit(client_id)

    @pytest.mark.asyncio
    async def test_check_rate_limit_pipeline(self):
        """测试限流检查使用 pipeline"""
        client_id = "test_client_3"

        # 多次调用测试 pipeline
        for _ in range(5):
            is_allowed, _ = await redis_client.check_rate_limit(client_id, 100, 60)
            assert is_allowed is True

    @pytest.mark.asyncio
    async def test_get_rate_limit_count(self):
        """测试获取限流计数"""
        client_id = "test_client_4"
        window_seconds = 60

        # 添加请求
        key = RedisKeys.RATE_LIMIT.format(client_id=client_id)
        current_time = time.time()

        await redis_client.client.zadd(key, {f"req_{i}": current_time for i in range(5)})

        count = await redis_client.get_rate_limit_count(client_id, window_seconds)
        assert count == 5

        # 清理
        await redis_client.reset_rate_limit(client_id)

    @pytest.mark.asyncio
    async def test_reset_rate_limit(self):
        """测试重置限流"""
        client_id = "test_client_5"

        # 添加请求
        await redis_client.client.zadd(
            RedisKeys.RATE_LIMIT.format(client_id=client_id), {"req_1": time.time()}
        )

        # 验证添加成功
        count_before = await redis_client.get_rate_limit_count(client_id, 60)
        assert count_before > 0

        # 重置
        await redis_client.reset_rate_limit(client_id)

        # 验证已重置
        count_after = await redis_client.get_rate_limit_count(client_id, 60)
        assert count_after == 0


class TestWebSocketRedis:
    """WebSocket Redis 测试"""

    @pytest.mark.asyncio
    async def test_add_websocket_connection(self):
        """测试添加 WebSocket 连接"""
        client_id = "agent_test_1"
        connection_data = {
            "is_agent": True,
            "status": "online",
            "connected_at": "2026-04-13T10:00:00Z",
        }

        await redis_client.add_websocket_connection(client_id, connection_data)

        # 验证添加成功
        data = await redis_client.get_websocket_connection(client_id)
        assert data is not None
        assert data["is_agent"] is True
        assert data["status"] == "online"

        # 清理
        await redis_client.remove_websocket_connection(client_id)

    @pytest.mark.asyncio
    async def test_remove_websocket_connection(self):
        """测试移除 WebSocket 连接"""
        client_id = "agent_test_2"

        # 先添加
        await redis_client.add_websocket_connection(client_id, {"is_agent": True})

        # 验证存在
        assert await redis_client.get_websocket_connection(client_id) is not None

        # 移除
        await redis_client.remove_websocket_connection(client_id)

        # 验证已移除
        assert await redis_client.get_websocket_connection(client_id) is None

    @pytest.mark.asyncio
    async def test_get_websocket_stats(self):
        """测试获取 WebSocket 统计"""
        # 添加一些连接
        for i in range(3):
            await redis_client.add_websocket_connection(f"agent_{i}", {"is_agent": True})

        for i in range(5):
            await redis_client.add_websocket_connection(f"user_{i}", {"is_agent": False})

        stats = await redis_client.get_websocket_stats()

        assert stats["total_connections"] == 8
        assert stats["agent_connections"] == 3
        assert stats["user_connections"] == 5

        # 清理
        for i in range(3):
            await redis_client.remove_websocket_connection(f"agent_{i}")
        for i in range(5):
            await redis_client.remove_websocket_connection(f"user_{i}")

    @pytest.mark.asyncio
    async def test_get_websocket_agents(self):
        """测试获取客服列表"""
        # 添加客服
        for i in range(3):
            await redis_client.add_websocket_connection(f"agent_{i}", {"is_agent": True})

        agents = await redis_client.get_websocket_agents()

        assert len(agents) == 3
        assert f"agent_0" in agents

        # 清理
        for i in range(3):
            await redis_client.remove_websocket_connection(f"agent_{i}")

    @pytest.mark.asyncio
    async def test_publish_websocket_message(self):
        """测试发布 WebSocket 消息"""
        message = {"type": "test", "payload": {"key": "value"}}

        # 发布消息
        count = await redis_client.publish_websocket_message("test_channel", message)

        # Pub/Sub 发布返回订阅者数量
        assert count >= 0


class TestAgentStatusRedis:
    """客服状态 Redis 测试"""

    @pytest.mark.asyncio
    async def test_set_agent_status(self):
        """测试设置客服状态"""
        agent_id = "agent_status_1"

        await redis_client.set_agent_status(agent_id, status="online", concurrent_chats=10)

        # 验证设置成功
        status = await redis_client.get_agent_status(agent_id)
        assert status is not None
        assert status["status"] == "online"
        assert status["concurrent_chats"] == 10
        assert "updated_at" in status

    @pytest.mark.asyncio
    async def test_set_agent_status_offline(self):
        """测试设置客服离线状态"""
        agent_id = "agent_status_2"

        await redis_client.set_agent_status(agent_id, status="offline", concurrent_chats=0)

        status = await redis_client.get_agent_status(agent_id)
        assert status["status"] == "offline"
        assert status["concurrent_chats"] == 0

    @pytest.mark.asyncio
    async def test_get_agent_status_not_exists(self):
        """测试获取不存在的客服状态"""
        agent_id = "agent_not_exists"

        status = await redis_client.get_agent_status(agent_id)

        assert status is None

    @pytest.mark.asyncio
    async def test_agent_status_expire(self):
        """测试客服状态过期"""
        agent_id = "agent_expire_1"

        # 设置状态（TTL 1 小时）
        await redis_client.set_agent_status(agent_id, status="online", concurrent_chats=5)

        # 验证 TTL 存在
        key = RedisKeys.AGENT_STATUS.format(agent_id=agent_id)
        ttl = await redis_client.client.ttl(key)
        assert ttl > 0
        assert ttl <= 3600  # 1 小时


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
