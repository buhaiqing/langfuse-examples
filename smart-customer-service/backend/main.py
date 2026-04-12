"""
Main entry point for Langfuse Smart Customer Service System
Orchestrates the complete customer service interaction flow
"""

import asyncio
import time
from typing import Any

from core.scoring import add_comprehensive_scores
from core.tracing import create_span, trace_customer_service
from modules.dialogue_manager import update_conversation_state
from modules.escalation import evaluate_escalation_need, get_fallback_response
from modules.intent_recognition import IntentResult, recognize_user_intent
from modules.rag_knowledge import query_knowledge_base
from modules.tool_calling import ToolName, call_tool


class SmartCustomerService:
    """
    Main customer service orchestrator with full Langfuse tracing
    """

    def __init__(self):
        self.name = "Smart Customer Service System"

    @trace_customer_service(name="customer_service_interaction", tags=["tech_support"])
    async def handle_message(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Handle a user message through the complete customer service flow

        Args:
            user_message: User's input message
            session_id: Unique session identifier
            user_id: User identifier
            metadata: Additional metadata

        Returns:
            Response dictionary with answer and metadata
        """
        start_time = time.time()
        metadata = metadata or {}

        # Update trace with session context
        from core.langfuse_client import langfuse
        from utils.data_masking import hash_user_id

        langfuse.update_current_trace(
            session_id=session_id,
            user_id=hash_user_id(user_id),
            tags=["tech_support", metadata.get("channel", "web")],
            metadata={"message_length": len(user_message), **metadata},
        )

        try:
            # Step 1: Intent Recognition
            intent_span = create_span(
                name="step_1_intent_recognition", input_data={"user_message": user_message}
            )
            intent_result = await recognize_user_intent(user_message, session_id)
            intent_span.end(
                output_data={"intent": intent_result.intent, "confidence": intent_result.confidence}
            )

            # Step 2: Update Dialogue State
            state_span = create_span(
                name="step_2_state_update", input_data={"session_id": session_id}
            )
            conversation_state = await update_conversation_state(
                session_id=session_id,
                user_input=user_message,
                bot_response="",  # Will be filled later
                metadata={"intent": intent_result.intent, "extracted_slots": intent_result.slots},
            )
            state_span.end(output_data={"turn_count": conversation_state.turn_count})

            # Step 3: Analyze User Sentiment (simplified)
            sentiment = self._analyze_sentiment(user_message)

            # Step 4: Evaluate Escalation Need
            escalation_span = create_span(
                name="step_3_escalation_evaluation",
                input_data={
                    "intent_confidence": intent_result.confidence,
                    "turn_count": conversation_state.turn_count,
                    "sentiment": sentiment,
                },
            )
            escalation_decision = await evaluate_escalation_need(
                session_id=session_id,
                intent_result=intent_result,
                conversation_state=conversation_state,
                user_sentiment=sentiment,
            )
            escalation_span.end(
                output_data={
                    "should_escalate": escalation_decision.should_escalate,
                    "reason": (
                        escalation_decision.reason.value if escalation_decision.reason else None
                    ),
                }
            )

            # Step 5: Generate Response
            if escalation_decision.should_escalate:
                # Escalation path
                response_span = create_span(
                    name="step_4_fallback_response",
                    input_data={"reason": escalation_decision.reason.value},
                )

                response_text = await get_fallback_response(
                    session_id=session_id, reason=escalation_decision.reason
                )

                response_span.end(output_data={"response": response_text})

                # Update dialogue state with bot response
                await update_conversation_state(
                    session_id=session_id,
                    user_input=user_message,
                    bot_response=response_text,
                    metadata={},
                )

                # Score the interaction
                processing_time = (time.time() - start_time) * 1000
                add_comprehensive_scores(
                    intent_confidence=intent_result.confidence,
                    issue_resolved=False,
                    response_latency_ms=processing_time,
                    failure_type="escalation_required",
                    escalation_required=True,
                    escalation_reason=escalation_decision.reason.value,
                )

                return {
                    "success": True,
                    "response": response_text,
                    "escalated": True,
                    "escalation_reason": escalation_decision.reason.value,
                    "intent": intent_result.intent,
                    "session_id": session_id,
                    "turn_count": conversation_state.turn_count + 1,
                    "processing_time_ms": processing_time,
                }

            else:
                # Normal processing path
                response_span = create_span(
                    name="step_4_normal_processing", input_data={"intent": intent_result.intent}
                )

                response_text = await self._process_by_intent(intent_result, session_id)

                response_span.end(output_data={"response_length": len(response_text)})

                # Update dialogue state with bot response
                await update_conversation_state(
                    session_id=session_id,
                    user_input=user_message,
                    bot_response=response_text,
                    metadata={},
                )

                # Determine if issue is resolved (simplified logic)
                issue_resolved = self._check_if_resolved(intent_result, response_text)

                # Score the interaction
                processing_time = (time.time() - start_time) * 1000
                add_comprehensive_scores(
                    intent_confidence=intent_result.confidence,
                    issue_resolved=issue_resolved,
                    response_latency_ms=processing_time,
                    escalation_required=False,
                )

                return {
                    "success": True,
                    "response": response_text,
                    "escalated": False,
                    "intent": intent_result.intent,
                    "issue_resolved": issue_resolved,
                    "session_id": session_id,
                    "turn_count": conversation_state.turn_count + 1,
                    "processing_time_ms": processing_time,
                }

        except Exception as e:
            # Error handling
            error_span = create_span(
                name="error_handling",
                input_data={"error": str(e)},
            )
            error_span.end()

            error_response = "抱歉，系统遇到了一些问题。请稍后重试或联系人工客服。"

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000

            # Update state
            await update_conversation_state(
                session_id=session_id,
                user_input=user_message,
                bot_response=error_response,
                metadata={},
            )

            return {
                "success": False,
                "response": error_response,
                "error": str(e),
                "escalated": True,
                "session_id": session_id,
                "processing_time_ms": processing_time,
            }

    async def _process_by_intent(self, intent_result: IntentResult, session_id: str) -> str:
        """Process request based on detected intent"""
        intent = intent_result.intent
        slots = intent_result.slots

        if intent == "api_error_troubleshooting":
            # Use RAG to find troubleshooting steps
            query = f"API error {slots.get('error_code', '')}"
            result = await query_knowledge_base(query, session_id)
            return result["answer"]

        elif intent == "ticket_status_query":
            # Call tool to query ticket status
            if "ticket_id" in slots:
                tool_result = await call_tool(
                    ToolName.QUERY_TICKET_STATUS.value, {"ticket_id": slots["ticket_id"]}
                )
                if tool_result["success"]:
                    data = tool_result["result"]
                    return (
                        f"工单 {data['ticket_id']} 的状态是: {data['status']}\n"
                        f"优先级: {data['priority']}\n"
                        f"负责人: {data['assigned_to']}\n"
                        f"最后更新: {data['last_updated']}"
                    )
            return "请提供工单号以便我为您查询状态。"

        elif intent == "product_information":
            # Use RAG to get product info
            result = await query_knowledge_base(
                f"product information {slots.get('product_name', '')}", session_id
            )
            return result["answer"]

        elif intent == "general_inquiry":
            # General inquiry - use RAG
            result = await query_knowledge_base(slots.get('query', 'general question'), session_id)
            return result["answer"]

        else:
            # Default to RAG for other intents
            result = await query_knowledge_base(slots.get('query', 'general question'), session_id)
            return result["answer"]

    def _analyze_sentiment(self, text: str) -> float:
        """Simple sentiment analysis (mock implementation)"""
        negative_words = ["糟糕", "失望", "愤怒", "不满", "差劲", "terrible", "angry", "frustrated"]
        positive_words = ["很好", "满意", "感谢", "excellent", "great", "thanks"]

        text_lower = text.lower()

        negative_count = sum(1 for word in negative_words if word in text_lower)
        positive_count = sum(1 for word in positive_words if word in text_lower)

        # Simple sentiment score (-1 to 1)
        if negative_count > positive_count:
            return -0.8
        elif positive_count > negative_count:
            return 0.8
        else:
            return 0.0

    def _check_if_resolved(self, intent_result: IntentResult, response: str) -> bool:
        """Check if the issue is likely resolved (simplified logic)"""
        # In production, use LLM to evaluate or get explicit user feedback
        # For now, use simple heuristics
        unresolved_indicators = ["抱歉", "无法", "未找到", "不清楚", "sorry", "cannot", "unable"]

        return not any(indicator in response for indicator in unresolved_indicators)


# Global instance
customer_service = SmartCustomerService()


async def main():
    """Example usage of the customer service system"""
    print("=" * 60)
    print("Langfuse Smart Customer Service System - Demo")
    print("=" * 60)

    # Example 1: API error troubleshooting
    print("\n[Example 1] API Error Troubleshooting")
    print("-" * 60)

    response = await customer_service.handle_message(
        user_message="我的API调用返回403错误，怎么办？",
        session_id="session_demo_001",
        user_id="user_demo_123",
        metadata={"channel": "web_chat"},
    )

    print(f"Response: {response['response']}")
    print(f"Escalated: {response['escalated']}")
    print(f"Processing Time: {response['processing_time_ms']:.0f}ms")

    # Example 2: Ticket status query
    print("\n[Example 2] Ticket Status Query")
    print("-" * 60)

    response = await customer_service.handle_message(
        user_message="帮我查一下工单TKT-12345的状态",
        session_id="session_demo_002",
        user_id="user_demo_456",
        metadata={"channel": "mobile_app"},
    )

    print(f"Response: {response['response']}")
    print(f"Escalated: {response['escalated']}")
    print(f"Processing Time: {response['processing_time_ms']:.0f}ms")

    # Example 3: Complex issue that might trigger escalation
    print("\n[Example 3] Complex Issue (Multiple Turns)")
    print("-" * 60)

    session_id = "session_demo_003"
    user_id = "user_demo_789"

    # Turn 1
    response = await customer_service.handle_message(
        user_message="我的系统出问题了",
        session_id=session_id,
        user_id=user_id,
        metadata={"channel": "web_chat"},
    )
    print(f"Turn 1 - Response: {response['response'][:100]}...")

    # Turn 2
    response = await customer_service.handle_message(
        user_message="就是那个API的问题",
        session_id=session_id,
        user_id=user_id,
        metadata={"channel": "web_chat"},
    )
    print(f"Turn 2 - Response: {response['response'][:100]}...")

    # Turn 3
    response = await customer_service.handle_message(
        user_message="我要转人工客服",
        session_id=session_id,
        user_id=user_id,
        metadata={"channel": "web_chat"},
    )
    print(f"Turn 3 - Response: {response['response']}")
    print(f"Escalated: {response['escalated']}")

    print("\n" + "=" * 60)
    print("Demo completed! Check Langfuse dashboard for traces.")
    print("=" * 60)

    # Flush traces to Langfuse
    from core.langfuse_client import flush_traces

    flush_traces()


if __name__ == "__main__":
    # Note: You need to set OPENAI_API_KEY in .env file
    import os

    from dotenv import load_dotenv

    load_dotenv()

    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "sk-placeholder":
        print("Warning: OPENAI_API_KEY not set. Using mock responses.")
        # 模拟实现
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
                        "status": "active"
                    },
                    "execution_time_ms": 100.2
                }

        class MockIntent:
            async def recognize_user_intent(self, user_message, session_id=None):
                from modules.intent_recognition import IntentResult
                # 简单的意图识别模拟
                if "403" in user_message:
                    return IntentResult(intent="api_error_troubleshooting", confidence=0.9, slots={"error_code": "403"}, entities=[])
                elif "工单" in user_message or "ticket" in user_message:
                    return IntentResult(intent="ticket_status_query", confidence=0.9, slots={"ticket_id": "TKT-12345"}, entities=[])
                else:
                    return IntentResult(intent="general_inquiry", confidence=0.8, slots={}, entities=[])

        # 替换导入的函数
        import modules.rag_knowledge
        import modules.tool_calling
        import modules.intent_recognition

        mock_rag = MockRAG()
        mock_tool = MockTool()
        mock_intent = MockIntent()

        modules.rag_knowledge.query_knowledge_base = mock_rag.query_knowledge_base
        modules.tool_calling.call_tool = mock_tool.call_tool
        modules.intent_recognition.recognize_user_intent = mock_intent.recognize_user_intent

    asyncio.run(main())
