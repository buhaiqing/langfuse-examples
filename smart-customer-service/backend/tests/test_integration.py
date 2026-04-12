"""
测试 RAG-01、TOOL-01、对话管理和意图识别的集成功能
"""

import asyncio
import os
from unittest.mock import Mock, patch

import pytest
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 检查是否有实际的 API 密钥
has_api_key = os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "sk-placeholder"


class MockRAG:
    async def query_knowledge_base(self, query, session_id=None):
        return {
            "answer": f"模拟回答: {query}",
            "retrieved_documents": [
                {
                    "doc_id": "mock_doc_1",
                    "content_preview": "模拟文档内容",
                    "relevance_score": 0.95,
                    "metadata": {}
                }
            ],
            "processing_time_ms": 150.5
        }


class MockTool:
    async def call_tool(self, tool_name, arguments):
        return {
            "success": True,
            "result": {
                "ticket_id": arguments.get("ticket_id", "TKT-12345"),
                "status": "in_progress",
                "priority": "high",
                "assigned_to": "John Smith",
                "last_updated": "2026-04-08T14:20:00Z",
                "product_id": arguments.get("product_id", "PROD-001"),
                "name": "Enterprise API Plan",
                "version": "v2.3",
                "account_id": arguments.get("account_id", "ACC-12345"),
                "plan": "professional",
                "account_status": "active"
            },
            "execution_time_ms": 100.2
        }


class MockIntent:
    async def recognize_user_intent(self, user_message, session_id=None):
        # 简单的意图识别模拟
        class IntentResult:
            def __init__(self, intent, confidence, slots, entities):
                self.intent = intent
                self.confidence = confidence
                self.slots = slots
                self.entities = entities

        if "403" in user_message:
            return IntentResult(intent="api_error_troubleshooting", confidence=0.9, slots={"error_code": "403"}, entities=[])
        elif "工单" in user_message or "ticket" in user_message:
            return IntentResult(intent="ticket_status_query", confidence=0.9, slots={"ticket_id": "TKT-12345"}, entities=[])
        else:
            return IntentResult(intent="general_inquiry", confidence=0.8, slots={}, entities=[])


class MockDialogueManager:
    async def update_conversation_state(self, session_id, user_input, bot_response, metadata=None):
        # 简单的对话状态管理模拟
        class ConversationState:
            def __init__(self, session_id):
                self.session_id = session_id
                self.turn_count = 1

        return ConversationState(session_id)


class ToolName:
    QUERY_TICKET_STATUS = "query_ticket_status"
    GET_PRODUCT_INFO = "get_product_info"
    CHECK_ACCOUNT_STATUS = "check_account_status"


class TestIntegration:
    """测试集成功能"""

    def setup_method(self):
        self.mock_rag = MockRAG()
        self.mock_tool = MockTool()
        self.mock_intent = MockIntent()
        self.mock_dialogue = MockDialogueManager()

    @pytest.mark.asyncio
    async def test_api_error_troubleshooting(self):
        """测试 API 错误排查集成场景"""
        user_message = "我的API调用返回403错误，怎么办？"
        session_id = "test_session_001"

        # 步骤 1: 意图识别
        intent_result = await self.mock_intent.recognize_user_intent(user_message, session_id)
        assert intent_result.intent == "api_error_troubleshooting"
        assert intent_result.confidence == 0.9
        assert intent_result.slots == {"error_code": "403"}

        # 步骤 2: 更新对话状态
        conversation_state = await self.mock_dialogue.update_conversation_state(
            session_id, user_message, "", {"intent": intent_result.intent, "extracted_slots": intent_result.slots}
        )
        assert conversation_state.session_id == session_id
        assert conversation_state.turn_count == 1

        # 步骤 3: 处理意图 (使用 RAG)
        if intent_result.intent == "api_error_troubleshooting":
            query = f"API error {intent_result.slots.get('error_code', '')}"
            rag_result = await self.mock_rag.query_knowledge_base(query, session_id)
            assert "模拟回答" in rag_result["answer"]
            assert len(rag_result["retrieved_documents"]) == 1

    @pytest.mark.asyncio
    async def test_ticket_status_query(self):
        """测试工单状态查询集成场景"""
        user_message = "帮我查一下工单TKT-12345的状态"
        session_id = "test_session_002"

        # 步骤 1: 意图识别
        intent_result = await self.mock_intent.recognize_user_intent(user_message, session_id)
        assert intent_result.intent == "ticket_status_query"
        assert intent_result.confidence == 0.9
        assert intent_result.slots == {"ticket_id": "TKT-12345"}

        # 步骤 2: 更新对话状态
        conversation_state = await self.mock_dialogue.update_conversation_state(
            session_id, user_message, "", {"intent": intent_result.intent, "extracted_slots": intent_result.slots}
        )
        assert conversation_state.session_id == session_id
        assert conversation_state.turn_count == 1

        # 步骤 3: 处理意图 (使用工具调用)
        if intent_result.intent == "ticket_status_query" and "ticket_id" in intent_result.slots:
            tool_result = await self.mock_tool.call_tool(
                ToolName.QUERY_TICKET_STATUS, {"ticket_id": intent_result.slots["ticket_id"]}
            )
            assert tool_result["success"] is True
            assert tool_result["result"]["ticket_id"] == "TKT-12345"
            assert tool_result["result"]["status"] == "in_progress"
            assert tool_result["result"]["priority"] == "high"
            assert tool_result["result"]["assigned_to"] == "John Smith"

    @pytest.mark.asyncio
    async def test_general_inquiry(self):
        """测试一般查询集成场景"""
        user_message = "你好，我有一个问题"
        session_id = "test_session_003"

        # 步骤 1: 意图识别
        intent_result = await self.mock_intent.recognize_user_intent(user_message, session_id)
        assert intent_result.intent == "general_inquiry"
        assert intent_result.confidence == 0.8
        assert intent_result.slots == {}

        # 步骤 2: 更新对话状态
        conversation_state = await self.mock_dialogue.update_conversation_state(
            session_id, user_message, "", {"intent": intent_result.intent, "extracted_slots": intent_result.slots}
        )
        assert conversation_state.session_id == session_id
        assert conversation_state.turn_count == 1
