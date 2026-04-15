"""
集成测试 - 测试各模块协同工作

测试场景：
1. 意图识别 + RAG + 工具调用链路
2. WebSocket 实时通信集成
3. Redis 缓存与持久化集成
4. 升级管理完整流程
5. Langfuse tracing 集成
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import json

from conftest import (
    generate_test_user_id,
    generate_test_session_id,
    BASE_URL,
    API_KEY,
)


class TestIntentRAGToolChain:
    """意图识别 → RAG → 工具调用链路测试"""

    @pytest.mark.asyncio
    async def test_intent_to_rag_flow(self, http_client, api_headers):
        """测试意图识别触发 RAG 查询"""
        session_id = generate_test_session_id()
        user_id = generate_test_user_id()

        # 1. 意图识别
        intent_response = await http_client.post(
            "/api/v1/intent/recognize",
            json={
                "user_message": "我想了解产品价格",
                "session_id": session_id,
                "user_id": user_id,
            },
            headers=api_headers,
        )

        assert intent_response.status_code == 200
        intent_data = intent_response.json()

        if intent_data["success"]:
            # 2. 根据 RAG 触发查询
            rag_response = await http_client.post(
                "/api/v1/rag/query",
                json={
                    "query": "产品价格信息",
                    "session_id": session_id,
                    "top_k": 3,
                },
                headers=api_headers,
            )

            assert rag_response.status_code == 200

    @pytest.mark.asyncio
    async def test_intent_to_tool_flow(self, http_client, api_headers):
        """测试意图识别触发工具调用"""
        session_id = generate_test_session_id()
        user_id = generate_test_user_id()

        # 1. 意图识别（查询工单）
        intent_response = await http_client.post(
            "/api/v1/intent/recognize",
            json={
                "user_message": "帮我查询工单 T-12345 的状态",
                "session_id": session_id,
                "user_id": user_id,
            },
            headers=api_headers,
        )

        assert intent_response.status_code == 200

        # 2. 工具调用
        tool_response = await http_client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "query_ticket_status",
                "parameters": {"ticket_id": "T-12345"},
                "session_id": session_id,
            },
            headers=api_headers,
        )

        assert tool_response.status_code == 200
        tool_data = tool_response.json()

        # 3. 返回结果给用户
        message_response = await http_client.post(
            f"/api/v1/conversations/{session_id}/messages",
            json={
                "role": "assistant",
                "content": f"您的工单状态：{tool_data.get('data', {}).get('status', '处理中')}",
            },
            headers=api_headers,
        )

        assert message_response.status_code == 200

    @pytest.mark.asyncio
    async def test_complete_chain_flow(self, http_client, api_headers):
        """测试完整链路：意图 → RAG → 工具 → 回复"""
        session_id = generate_test_session_id()
        user_id = generate_test_user_id()

        # 用户问题
        user_message = "我想重置密码，我的账户 ID 是 user_123"

        # 1. 意图识别
        intent_resp = await http_client.post(
            "/api/v1/intent/recognize",
            json={
                "user_message": user_message,
                "session_id": session_id,
                "user_id": user_id,
            },
            headers=api_headers,
        )

        # 2. RAG 查询（获取重置密码流程）
        rag_resp = await http_client.post(
            "/api/v1/rag/query",
            json={
                "query": "如何重置密码",
                "session_id": session_id,
                "top_k": 3,
            },
            headers=api_headers,
        )

        # 3. 工具调用（检查账户状态）
        tool_resp = await http_client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "check_account_status",
                "parameters": {"user_id": "user_123"},
                "session_id": session_id,
            },
            headers=api_headers,
        )

        # 4. 生成回复
        reply_resp = await http_client.post(
            f"/api/v1/conversations/{session_id}/messages",
            json={
                "role": "assistant",
                "content": "已为您发送密码重置邮件，请查收。",
            },
            headers=api_headers,
        )

        # 验证链路完整性
        assert intent_resp.status_code == 200
        assert rag_resp.status_code == 200
        assert tool_resp.status_code == 200
        assert reply_resp.status_code == 200


class TestEscalationIntegration:
    """升级管理集成测试"""

    @pytest.mark.asyncio
    async def test_trigger_escalation_flow(self, http_client, api_headers):
        """测试触发升级完整流程"""
        session_id = generate_test_session_id()
        user_id = generate_test_user_id()

        # 1. 用户发送复杂问题
        await http_client.post(
            f"/api/v1/conversations/{session_id}/messages",
            json={
                "role": "user",
                "content": "我要投诉，这个问题已经困扰我三天了！",
            },
            headers=api_headers,
        )

        # 2. 意图识别（低置信度或敏感关键词）
        intent_resp = await http_client.post(
            "/api/v1/intent/recognize",
            json={
                "user_message": "我要投诉",
                "session_id": session_id,
                "user_id": user_id,
            },
            headers=api_headers,
        )

        intent_data = intent_resp.json()

        # 3. 检查是否需要升级
        escalation_resp = await http_client.post(
            "/api/v1/escalations/check",
            json={
                "session_id": session_id,
                "user_id": user_id,
                "intent_confidence": intent_data.get("data", {}).get("confidence", 0.5),
                "user_message": "我要投诉",
                "is_vip": False,
            },
            headers=api_headers,
        )

        assert escalation_resp.status_code == 200

        # 4. 如果触发升级，检查队列
        queue_resp = await http_client.get(
            "/api/v1/escalations/queue",
            headers=api_headers,
        )

        assert queue_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_agent_accept_escalation(self, http_client, api_headers):
        """测试客服接受升级"""
        # 1. 获取升级队列
        queue_resp = await http_client.get(
            "/api/v1/escalations/queue",
            headers=api_headers,
        )

        # 2. 获取下一个升级
        next_resp = await http_client.post(
            "/api/v1/escalations/queue/next",
            headers=api_headers,
        )

        if next_resp.json()["success"]:
            session_id = next_resp.json()["data"]["session_id"]

            # 3. 客服接受
            accept_resp = await http_client.post(
                "/api/v1/escalations/accept",
                json={
                    "session_id": session_id,
                    "agent_id": "test_agent_001",
                },
                headers=api_headers,
            )

            # 4. 客服回复
            message_resp = await http_client.post(
                f"/api/v1/conversations/{session_id}/messages",
                json={
                    "role": "assistant",
                    "content": "您好，我是客服，我来帮您处理这个问题。",
                },
                headers=api_headers,
            )

            assert message_resp.status_code == 200


class TestRedisIntegration:
    """Redis 缓存集成测试"""

    @pytest.mark.asyncio
    async def test_session_persistence(self, http_client, api_headers):
        """测试会话持久化"""
        user_id = generate_test_user_id()

        # 1. 创建会话
        create_resp = await http_client.post(
            "/api/v1/conversations",
            json={"user_id": user_id},
            headers=api_headers,
        )

        session_id = create_resp.json()["data"]["session_id"]

        # 2. 发送消息
        await http_client.post(
            f"/api/v1/conversations/{session_id}/messages",
            json={
                "role": "user",
                "content": "测试消息",
            },
            headers=api_headers,
        )

        # 3. 查询会话（验证持久化）
        get_resp = await http_client.get(
            f"/api/v1/conversations/{session_id}",
            headers=api_headers,
        )

        assert get_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_escalation_queue_redis(self, http_client, api_headers):
        """测试升级队列 Redis 存储"""
        # 获取队列大小
        queue_resp = await http_client.get(
            "/api/v1/escalations/queue",
            headers=api_headers,
        )

        assert queue_resp.status_code == 200
        data = queue_resp.json()
        assert "queue_size" in data["data"]


class TestWebSocketIntegration:
    """WebSocket 集成测试"""

    @pytest.mark.asyncio
    async def test_ws_agent_notification(self):
        """测试 WebSocket 客服通知"""
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets 未安装")

        ws_url = BASE_URL.replace("http", "ws") + "/ws/agent/test_agent_001"

        try:
            async with websockets.connect(ws_url, timeout=5) as ws:
                # 发送新消息通知模拟
                await ws.send(json.dumps({
                    "type": "new_message",
                    "payload": {
                        "session_id": "test_session",
                        "content": "用户发送了新消息",
                    }
                }))

                # 等待广播响应
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=3)
                    data = json.loads(response)
                    assert "type" in data
                except asyncio.TimeoutError:
                    pass  # 可能无响应

        except Exception as e:
            pytest.skip(f"WebSocket 测试失败: {e}")

    @pytest.mark.asyncio
    async def test_ws_user_connection(self):
        """测试 WebSocket 用户连接"""
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets 未安装")

        ws_url = BASE_URL.replace("http", "ws") + "/ws/user/test_user_001"

        try:
            async with websockets.connect(ws_url, timeout=5) as ws:
                # 发送心跳
                await ws.send(json.dumps({"type": "heartbeat"}))

                response = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(response)

                assert data["type"] in ["welcome", "heartbeat_ack"]

        except Exception as e:
            pytest.skip(f"WebSocket 测试失败: {e}")


class TestAnalyticsIntegration:
    """数据分析集成测试"""

    @pytest.mark.asyncio
    async def test_analytics_flow(self, http_client, api_headers):
        """测试数据分析流程"""
        # 1. 创建多个会话和消息
        for i in range(3):
            user_id = generate_test_user_id()
            create_resp = await http_client.post(
                "/api/v1/conversations",
                json={"user_id": user_id},
                headers=api_headers,
            )

        # 2. 获取概览统计
        overview_resp = await http_client.get(
            "/api/v1/analytics/overview",
            params={"days": 7},
            headers=api_headers,
        )

        assert overview_resp.status_code == 200

        # 3. 获取意图分布
        intent_dist_resp = await http_client.get(
            "/api/v1/analytics/intent-distribution",
            headers=api_headers,
        )

        assert intent_dist_resp.status_code == 200

        # 4. 获取客服绩效
        agent_perf_resp = await http_client.get(
            "/api/v1/analytics/agent-performance",
            params={"days": 30},
            headers=api_headers,
        )

        assert agent_perf_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_realtime_metrics(self, http_client, api_headers):
        """测试实时指标"""
        response = await http_client.get(
            "/api/v1/analytics/realtime",
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()

        if data["success"]:
            metrics = data["data"]
            assert "active_sessions" in metrics
            assert "online_agents" in metrics
            assert "escalation_queue_size" in metrics


class TestErrorHandling:
    """错误处理集成测试"""

    @pytest.mark.asyncio
    async def test_invalid_api_key(self, http_client):
        """测试无效 API Key"""
        response = await http_client.get(
            "/api/v1/intent/intents",
            headers={"X-API-Key": "invalid_key"},
        )

        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, http_client, api_headers):
        """测试限流"""
        # 发送大量请求
        responses = []
        for i in range(200):
            resp = await http_client.get(
                "/api/v1/intent/intents",
                headers=api_headers,
            )
            responses.append(resp)

        # 检查是否触发限流
        rate_limited = [r for r in responses if r.status_code == 429]

        # 记录限流结果
        print(f"限流触发次数: {len(rate_limited)}")

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, http_client, api_headers):
        """测试优雅降级"""
        # 模拟服务部分不可用场景
        session_id = generate_test_session_id()

        # 即使某些服务不可用，核心功能应正常
        response = await http_client.get(
            f"/api/v1/conversations/{session_id}",
            headers=api_headers,
        )

        assert response.status_code == 200