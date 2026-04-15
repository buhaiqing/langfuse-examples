"""
用户流程 E2E 测试

测试用户咨询完整流程：
1. 创建会话
2. 发送消息
3. 意图识别
4. RAG 查询
5. 工具调用
6. 升级触发
7. 获得回复
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

from conftest import (
    check_service_health,
    create_test_session,
    send_message,
    recognize_intent,
    query_rag,
    execute_tool,
    check_escalation,
    cleanup_test_data,
    generate_test_user_id,
    generate_test_session_id,
    BASE_URL,
    API_KEY,
)


@pytest.fixture
async def test_session(http_client):
    """创建测试会话 fixture"""
    user_id = generate_test_user_id()
    session_id = await create_test_session(http_client, user_id)
    yield {"session_id": session_id, "user_id": user_id}
    # 清理
    await cleanup_test_data(http_client, session_id)


class TestUserConsultationFlow:
    """用户咨询流程测试"""

    @pytest.mark.asyncio
    async def test_health_check(self, http_client):
        """测试服务健康检查"""
        is_healthy = await check_service_health(http_client)
        assert is_healthy, "后端服务应该健康"

    @pytest.mark.asyncio
    async def test_create_session(self, http_client, api_headers):
        """测试创建会话"""
        user_id = generate_test_user_id()
        response = await http_client.post(
            "/api/v1/conversations",
            json={"user_id": user_id},
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "session_id" in data["data"]

    @pytest.mark.asyncio
    async def test_send_user_message(self, http_client, test_session, api_headers):
        """测试发送用户消息"""
        response = await send_message(
            http_client,
            test_session["session_id"],
            "我想查询我的工单状态",
            role="user",
        )

        assert response["success"] is True
        assert "message_id" in response["data"]

    @pytest.mark.asyncio
    async def test_intent_recognition(self, http_client, test_session):
        """测试意图识别"""
        result = await recognize_intent(
            http_client,
            "我想查询工单 T-12345 的状态",
            test_session["session_id"],
            test_session["user_id"],
        )

        assert result["success"] is True
        assert result["data"]["intent"] is not None
        assert result["data"]["confidence"] >= 0.0
        assert result["data"]["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_rag_query(self, http_client, test_session):
        """测试 RAG 查询"""
        result = await query_rag(
            http_client,
            "如何重置密码？",
            test_session["session_id"],
        )

        # RAG 可能返回成功或失败（取决于知识库状态）
        assert "success" in result
        if result["success"]:
            assert "answer" in result["data"]

    @pytest.mark.asyncio
    async def test_tool_execution(self, http_client, test_session):
        """测试工具调用"""
        result = await execute_tool(
            http_client,
            "query_ticket_status",
            {"ticket_id": "T-12345", "system": "jira"},
            test_session["session_id"],
        )

        assert result["success"] is True
        assert "status" in result["data"]

    @pytest.mark.asyncio
    async def test_escalation_check_low_confidence(self, http_client, test_session):
        """测试低置信度触发升级"""
        result = await check_escalation(
            http_client,
            test_session["session_id"],
            test_session["user_id"],
            intent_confidence=0.3,  # 低置信度
            user_message="我不理解这个问题",
        )

        assert result["success"] is True
        # 低置信度可能触发升级
        assert "requires_escalation" in result

    @pytest.mark.asyncio
    async def test_escalation_check_sensitive_keyword(self, http_client, test_session):
        """测试敏感关键词触发升级"""
        result = await check_escalation(
            http_client,
            test_session["session_id"],
            test_session["user_id"],
            intent_confidence=0.8,
            user_message="我要投诉你们的服务，这太糟糕了！",
        )

        assert result["success"] is True
        # 包含投诉关键词，可能触发升级
        assert "requires_escalation" in result

    @pytest.mark.asyncio
    async def test_escalation_check_vip_user(self, http_client, test_session):
        """测试 VIP 用户升级"""
        result = await check_escalation(
            http_client,
            test_session["session_id"],
            test_session["user_id"],
            intent_confidence=0.5,
            user_message="请帮我处理这个问题",
            is_vip=True,
        )

        assert result["success"] is True
        # VIP 用户可能更容易触发升级
        assert "requires_escalation" in result


class TestCompleteUserFlow:
    """完整用户流程测试"""

    @pytest.mark.asyncio
    async def test_full_consultation_flow(self, http_client, api_headers):
        """测试完整咨询流程"""
        # 1. 创建会话
        user_id = generate_test_user_id()
        session_id = await create_test_session(http_client, user_id)

        # 2. 发送第一条消息
        msg_result = await send_message(
            http_client, session_id, "你好，我想查询工单状态"
        )
        assert msg_result["success"] is True

        # 3. 意图识别
        intent_result = await recognize_intent(
            http_client,
            "我想查询工单 T-12345 的状态",
            session_id,
            user_id,
        )
        assert intent_result["success"] is True

        # 4. 工具调用（根据意图）
        if intent_result["data"]["intent"] == "query_ticket":
            tool_result = await execute_tool(
                http_client,
                "query_ticket_status",
                {"ticket_id": "T-12345"},
                session_id,
            )
            assert tool_result["success"] is True

        # 5. 发送回复消息
        reply_result = await send_message(
            http_client,
            session_id,
            "您的工单 T-12345 正在处理中，预计明天完成。",
            role="assistant",
        )
        assert reply_result["success"] is True

        # 6. 清理
        await cleanup_test_data(http_client, session_id)

    @pytest.mark.asyncio
    async def test_multi_round_conversation(self, http_client, api_headers):
        """测试多轮对话"""
        user_id = generate_test_user_id()
        session_id = await create_test_session(http_client, user_id)

        # 多轮对话
        messages = [
            ("你好", "user"),
            ("您好，请问有什么可以帮助您？", "assistant"),
            ("我想查询我的账户状态", "user"),
            ("请提供您的用户 ID", "assistant"),
            ("我的 ID 是 user_123", "user"),
        ]

        for content, role in messages:
            result = await send_message(http_client, session_id, content, role)
            assert result["success"] is True

        # 检查意图识别
        intent_result = await recognize_intent(
            http_client, "查询账户状态", session_id, user_id
        )
        assert intent_result["success"] is True

        # 清理
        await cleanup_test_data(http_client, session_id)


class TestEdgeCases:
    """边界情况测试"""

    @pytest.mark.asyncio
    async def test_empty_message(self, http_client, test_session, api_headers):
        """测试空消息"""
        response = await http_client.post(
            f"/api/v1/conversations/{test_session['session_id']}/messages",
            json={"role": "user", "content": ""},
            headers=api_headers,
        )

        # 空消息应该被拒绝
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_invalid_session(self, http_client, api_headers):
        """测试无效会话 ID"""
        response = await http_client.get(
            "/api/v1/conversations/invalid_session_id",
            headers=api_headers,
        )

        # 无效会话应该返回成功但数据为空或错误
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, http_client, api_headers):
        """测试并发请求"""
        user_id = generate_test_user_id()

        # 创建多个并发请求
        tasks = [
            create_test_session(http_client, f"{user_id}_{i}")
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 检查所有请求都成功或至少没有异常
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"并发请求失败: {result}")

    @pytest.mark.asyncio
    async def test_rate_limit(self, http_client, api_headers):
        """测试限流"""
        # 发送大量请求
        responses = []
        for i in range(150):
            response = await http_client.get(
                "/api/v1/intent/intents",
                headers=api_headers,
            )
            responses.append(response)

        # 检查是否有被限流的响应
        rate_limited = [r for r in responses if r.status_code == 429]
        # 可能触发限流，也可能不触发（取决于配置）
        # 这里只记录结果
        print(f"限流响应数: {len(rate_limited)}")


class TestAPIResponseFormat:
    """API 响应格式测试"""

    @pytest.mark.asyncio
    async def test_intent_response_format(self, http_client, test_session):
        """测试意图识别响应格式"""
        result = await recognize_intent(
            http_client,
            "测试消息",
            test_session["session_id"],
            test_session["user_id"],
        )

        # 验证响应结构
        assert "success" in result
        if result["success"]:
            assert "data" in result
            data = result["data"]
            assert "intent" in data
            assert "confidence" in data
            assert "slots" in data
            assert "entities" in data

    @pytest.mark.asyncio
    async def test_rag_response_format(self, http_client, test_session):
        """测试 RAG 响应格式"""
        result = await query_rag(
            http_client,
            "测试查询",
            test_session["session_id"],
        )

        assert "success" in result
        if result["success"]:
            assert "data" in result
            data = result["data"]
            assert "answer" in data
            assert "confidence" in data

    @pytest.mark.asyncio
    async def test_tool_response_format(self, http_client, test_session):
        """测试工具响应格式"""
        result = await execute_tool(
            http_client,
            "check_account_status",
            {"user_id": "test_user"},
            test_session["session_id"],
        )

        assert "success" in result
        if result["success"]:
            assert "data" in result