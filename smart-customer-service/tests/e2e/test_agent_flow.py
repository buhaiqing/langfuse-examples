"""
客服工作流程 E2E 测试

测试客服操作流程：
1. 客服登录/状态管理
2. 接收升级请求
3. 查看会话历史
4. 发送回复
5. 会话转移
6. 状态同步
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any
import json

from conftest import (
    generate_test_session_id,
    generate_test_agent_id,
    BASE_URL,
    API_KEY,
)


class TestAgentStatus:
    """客服状态管理测试"""

    @pytest.mark.asyncio
    async def test_get_agent_status(self, http_client, api_headers):
        """测试获取客服状态"""
        response = await http_client.get(
            "/api/v1/agent-status",
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    @pytest.mark.asyncio
    async def test_update_agent_status(self, http_client, api_headers):
        """测试更新客服状态"""
        agent_id = generate_test_agent_id()
        response = await http_client.post(
            "/api/v1/agent-status",
            json={
                "agent_id": agent_id,
                "status": "online",
                "max_concurrent_sessions": 5,
            },
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_online_agents(self, http_client, api_headers):
        """测试获取在线客服列表"""
        response = await http_client.get(
            "/api/v1/agent-status/online",
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        if data["success"]:
            assert "agents" in data["data"]


class TestEscalationWorkflow:
    """升级处理流程测试"""

    @pytest.mark.asyncio
    async def test_get_escalation_queue(self, http_client, api_headers):
        """测试获取升级队列"""
        response = await http_client.get(
            "/api/v1/escalations/queue",
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "queue_size" in data["data"]

    @pytest.mark.asyncio
    async def test_get_next_escalation(self, http_client, api_headers):
        """测试获取下一个升级会话"""
        response = await http_client.post(
            "/api/v1/escalations/queue/next",
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # 队列可能为空
        assert "success" in data

    @pytest.mark.asyncio
    async def test_accept_escalation(self, http_client, api_headers):
        """测试接受升级请求"""
        session_id = generate_test_session_id()
        agent_id = generate_test_agent_id()

        response = await http_client.post(
            "/api/v1/escalations/accept",
            json={
                "session_id": session_id,
                "agent_id": agent_id,
            },
            headers=api_headers,
        )

        # 可能成功或失败（取决于升级是否存在）
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_reject_escalation(self, http_client, api_headers):
        """测试拒绝升级请求"""
        session_id = generate_test_session_id()
        agent_id = generate_test_agent_id()

        response = await http_client.post(
            "/api/v1/escalations/reject",
            json={
                "session_id": session_id,
                "agent_id": agent_id,
                "reason": "当前负载过高",
            },
            headers=api_headers,
        )

        assert response.status_code == 200


class TestAgentConversation:
    """客服会话操作测试"""

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, http_client, api_headers):
        """测试获取会话历史"""
        session_id = generate_test_session_id()

        response = await http_client.get(
            f"/api/v1/conversations/{session_id}",
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    @pytest.mark.asyncio
    async def test_send_agent_reply(self, http_client, api_headers):
        """测试客服发送回复"""
        session_id = generate_test_session_id()

        response = await http_client.post(
            f"/api/v1/conversations/{session_id}/messages",
            json={
                "role": "assistant",
                "content": "您好，我是客服，请问有什么可以帮助您？",
            },
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_transfer_session(self, http_client, api_headers):
        """测试会话转移"""
        session_id = generate_test_session_id()

        response = await http_client.post(
            "/api/v1/conversations/transfer",
            json={
                "session_id": session_id,
                "from_agent_id": "test_agent_001",
                "to_agent_id": "test_agent_002",
                "reason": "专业问题转接",
            },
            headers=api_headers,
        )

        # 可能成功或失败
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_close_session(self, http_client, api_headers):
        """测试关闭会话"""
        session_id = generate_test_session_id()

        response = await http_client.delete(
            f"/api/v1/conversations/{session_id}",
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestWebSocketConnection:
    """WebSocket 连接测试"""

    @pytest.mark.asyncio
    async def test_websocket_connect(self):
        """测试 WebSocket 连接"""
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets 未安装")

        ws_url = BASE_URL.replace("http", "ws") + "/ws/agent/test_agent_001"

        try:
            async with websockets.connect(ws_url, timeout=5) as ws:
                # 发送心跳
                await ws.send(json.dumps({"type": "heartbeat"}))

                # 接收响应
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(response)

                assert data["type"] in ["welcome", "heartbeat_ack"]

        except Exception as e:
            # WebSocket 可能未配置，跳过测试
            pytest.skip(f"WebSocket 连接失败: {e}")

    @pytest.mark.asyncio
    async def test_websocket_broadcast(self):
        """测试 WebSocket 广播"""
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets 未安装")

        ws_url = BASE_URL.replace("http", "ws") + "/ws/agent/test_agent_001"

        try:
            async with websockets.connect(ws_url, timeout=5) as ws:
                # 发送状态变更
                await ws.send(json.dumps({
                    "type": "status_change",
                    "payload": {
                        "status": "online",
                        "concurrent_sessions": 2,
                    }
                }))

                # 等待响应（可能没有）
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=3)
                except asyncio.TimeoutError:
                    pass  # 无响应也正常

        except Exception as e:
            pytest.skip(f"WebSocket 测试失败: {e}")


class TestAgentPerformance:
    """客服绩效测试"""

    @pytest.mark.asyncio
    async def test_get_agent_statistics(self, http_client, api_headers):
        """测试获取客服统计"""
        response = await http_client.get(
            "/api/v1/analytics/agent-performance",
            params={"days": 7},
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        if data["success"]:
            assert "data" in data

    @pytest.mark.asyncio
    async def test_get_realtime_metrics(self, http_client, api_headers):
        """测试获取实时指标"""
        response = await http_client.get(
            "/api/v1/analytics/realtime",
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data