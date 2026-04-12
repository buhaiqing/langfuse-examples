"""
技术支持场景完整演示 - Tech Support Scenarios Demo

本示例演示智能客服系统在技术支持场景下的完整工作流程，包括:
1. API错误排查 - 展示意图识别、知识库查询和响应生成
2. 工单状态查询 - 展示工具调用和结构化数据返回
3. 复杂技术问题 - 展示多轮对话、上下文管理和转人工触发

核心价值:
- 完整的Langfuse追踪链路，每个步骤都有详细的span记录
- 多维度评分系统（意图置信度、问题解决率、响应延迟等）
- 智能升级机制（基于置信度、情绪、轮次等多因素决策）
- 会话状态管理，支持上下文感知

运行方式:
    python examples/tech_support_demo.py

注意:
- 即使没有真实的Langfuse API也能运行（使用mock模式）
- 所有输出都会打印到控制台，便于理解流程
"""

import asyncio
import time
from datetime import datetime
from typing import Any

# ============================================================================
# Mock Implementation (用于在没有真实API时演示)
# ============================================================================


class MockIntentResult:
    """模拟意图识别结果"""

    def __init__(self, intent: str, confidence: float, slots: dict[str, Any]):
        self.intent = intent
        self.confidence = confidence
        self.slots = slots


class MockConversationState:
    """模拟会话状态"""

    def __init__(self, session_id: str, turn_count: int = 0):
        self.session_id = session_id
        self.turn_count = turn_count


class MockEscalationDecision:
    """模拟升级决策"""

    def __init__(self, should_escalate: bool, reason: str | None = None):
        self.should_escalate = should_escalate
        self.reason = type("obj", (object,), {"value": reason})() if reason else None


# 模拟数据存储
_mock_conversation_states: dict[str, MockConversationState] = {}


# ============================================================================
# 核心模块模拟实现
# ============================================================================


async def recognize_user_intent(user_message: str, session_id: str) -> MockIntentResult:
    """
    意图识别模块 - 模拟实现

    根据用户消息识别其意图类型，提取关键信息槽位

    Args:
        user_message: 用户输入的消息
        session_id: 会话ID

    Returns:
        MockIntentResult: 包含意图类型、置信度和提取的槽位信息
    """
    message_lower = user_message.lower()

    # 规则-based 意图识别（简化版）
    if any(keyword in message_lower for keyword in ["403", "404", "500", "错误", "error", "异常"]):
        return MockIntentResult(
            intent="api_error_troubleshooting",
            confidence=0.92,
            slots={
                "error_code": "403" if "403" in message_lower else "unknown",
                "context": "API调用",
            },
        )

    elif any(keyword in message_lower for keyword in ["工单", "ticket", "状态", "status", "TKT-"]):
        # 尝试提取工单号
        ticket_id = None
        if "TKT-" in user_message:
            parts = user_message.split("TKT-")
            if len(parts) > 1:
                ticket_id = "TKT-" + parts[1].split()[0].strip()

        return MockIntentResult(
            intent="ticket_status_query",
            confidence=0.88,
            slots={"ticket_id": ticket_id} if ticket_id else {},
        )

    elif any(keyword in message_lower for keyword in ["人工", "转接", "客服", "human", "agent"]):
        return MockIntentResult(intent="request_human_agent", confidence=0.95, slots={})

    elif any(keyword in message_lower for keyword in ["问题", "problem", "出错了", "不行"]):
        return MockIntentResult(
            intent="general_technical_issue",
            confidence=0.65,  # 低置信度，可能需要多轮澄清
            slots={},
        )

    else:
        return MockIntentResult(intent="general_inquiry", confidence=0.70, slots={})


async def query_knowledge_base(query: str, session_id: str) -> dict[str, Any]:
    """
    RAG知识库查询模块 - 模拟实现

    从知识库中检索相关的解决方案和技术文档

    Args:
        query: 查询关键词
        session_id: 会话ID

    Returns:
        Dict: 包含答案和元数据的字典
    """
    query_lower = query.lower()

    # 模拟知识库匹配
    if "403" in query_lower or "forbidden" in query_lower:
        return {
            "answer": (
                "关于403错误的解决方案:\n\n"
                "1. **检查API密钥**: 确认您的API Key是否有效且未过期\n"
                "2. **权限验证**: 检查当前账号是否有访问该资源的权限\n"
                "3. **IP白名单**: 确认您的IP地址已添加到白名单中\n"
                "4. **请求频率**: 检查是否超过了API调用频率限制\n\n"
                "建议操作: 登录控制台查看API密钥状态，或联系管理员确认权限配置。"
            ),
            "source_documents": [
                {"title": "API认证指南", "relevance_score": 0.95},
                {"title": "常见错误码说明", "relevance_score": 0.88},
            ],
            "confidence": 0.91,
        }

    elif "产品" in query_lower or "product" in query_lower:
        return {
            "answer": (
                "我们的产品提供以下核心功能:\n\n"
                "- **数据处理**: 支持大规模数据实时处理和分析\n"
                "- **API服务**: 提供RESTful API接口，易于集成\n"
                "- **安全认证**: 多层安全防护，保障数据安全\n"
                "- **高可用性**: 99.9% SLA保证，分布式架构\n\n"
                "如需了解具体产品的详细信息，请告诉我产品名称。"
            ),
            "source_documents": [{"title": "产品概览", "relevance_score": 0.85}],
            "confidence": 0.82,
        }

    else:
        return {
            "answer": (
                "我理解您遇到了技术问题。为了更好地帮助您，能否提供更多详细信息？\n\n"
                "例如:\n"
                "- 具体的错误信息或错误码\n"
                "- 问题发生的时间和频率\n"
                "- 您已经尝试过的解决方法\n\n"
                "这样我可以为您提供更精准的解决方案。"
            ),
            "source_documents": [],
            "confidence": 0.60,
        }


async def call_tool(tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    """
    工具调用模块 - 模拟实现

    调用外部系统工具获取实时数据

    Args:
        tool_name: 工具名称
        parameters: 工具参数

    Returns:
        Dict: 工具执行结果
    """
    if tool_name == "query_ticket_status":
        ticket_id = parameters.get("ticket_id", "")

        # 模拟工单数据库查询
        mock_tickets = {
            "TKT-12345": {
                "ticket_id": "TKT-12345",
                "status": "处理中",
                "priority": "高",
                "assigned_to": "张工程师",
                "last_updated": "2026-04-08 14:30:00",
                "description": "API接口响应超时问题",
            },
            "TKT-67890": {
                "ticket_id": "TKT-67890",
                "status": "已解决",
                "priority": "中",
                "assigned_to": "李工程师",
                "last_updated": "2026-04-07 16:45:00",
                "description": "数据库连接池配置优化",
            },
        }

        if ticket_id in mock_tickets:
            return {"success": True, "result": mock_tickets[ticket_id]}
        else:
            return {"success": False, "error": f"未找到工单 {ticket_id}"}

    return {"success": False, "error": f"未知工具: {tool_name}"}


async def update_conversation_state(
    session_id: str, user_input: str, bot_response: str, metadata: dict[str, Any]
) -> MockConversationState:
    """
    会话状态管理模块 - 模拟实现

    更新和维护会话的上下文状态

    Args:
        session_id: 会话ID
        user_input: 用户输入
        bot_response: 机器人响应
        metadata: 额外元数据

    Returns:
        MockConversationState: 更新后的会话状态
    """
    if session_id not in _mock_conversation_states:
        _mock_conversation_states[session_id] = MockConversationState(session_id, 0)

    state = _mock_conversation_states[session_id]
    state.turn_count += 1

    return state


async def get_conversation_state(session_id: str) -> MockConversationState | None:
    """获取会话状态"""
    return _mock_conversation_states.get(session_id)


async def evaluate_escalation_need(
    session_id: str,
    intent_result: MockIntentResult,
    conversation_state: MockConversationState,
    user_sentiment: float,
) -> MockEscalationDecision:
    """
    升级评估模块 - 模拟实现

    基于多因素判断是否需要转接人工客服

    评估因素:
    - 意图置信度: 低于阈值可能无法准确理解用户需求
    - 对话轮次: 过多轮次仍未解决说明问题复杂
    - 用户情绪: 负面情绪需要优先处理
    - 明确请求: 用户明确要求转人工

    Args:
        session_id: 会话ID
        intent_result: 意图识别结果
        conversation_state: 会话状态
        user_sentiment: 用户情绪分数 (-1.0 ~ 1.0)

    Returns:
        MockEscalationDecision: 升级决策
    """
    # 规则1: 用户明确要求转人工
    if intent_result.intent == "request_human_agent":
        return MockEscalationDecision(should_escalate=True, reason="user_requested")

    # 规则2: 意图置信度过低
    if intent_result.confidence < 0.5:
        return MockEscalationDecision(should_escalate=True, reason="low_confidence")

    # 规则3: 对话轮次过多（超过5轮仍未解决）
    if conversation_state.turn_count >= 5:
        return MockEscalationDecision(should_escalate=True, reason="max_turns_exceeded")

    # 规则4: 用户情绪极度负面
    if user_sentiment < -0.7:
        return MockEscalationDecision(should_escalate=True, reason="negative_sentiment")

    # 不需要升级
    return MockEscalationDecision(should_escalate=False)


async def get_fallback_response(session_id: str, reason: str) -> str:
    """
    获取降级响应 - 模拟实现

    当需要转接人工时，提供友好的过渡响应

    Args:
        session_id: 会话ID
        reason: 升级原因

    Returns:
        str: 降级响应文本
    """
    responses = {
        "user_requested": (
            "好的，我理解您需要人工客服的帮助。\n\n"
            "正在为您转接专业客服人员，请稍候...\n"
            "预计等待时间: 2-3分钟\n\n"
            "在等待期间，您可以继续描述您的问题，这样客服人员可以更快地了解情况。"
        ),
        "low_confidence": (
            "抱歉，我没有完全理解您的问题。\n\n"
            "为了确保给您提供准确的帮助，我将为您转接人工客服。\n"
            "请您稍候，专业客服人员将很快为您服务。"
        ),
        "max_turns_exceeded": (
            "我们已进行了多轮对话，但似乎问题还未得到解决。\n\n"
            "为了更高效地帮助您，我建议转接给专业技术支持工程师。\n"
            "正在为您安排转接，请稍候..."
        ),
        "negative_sentiment": (
            "我注意到您对当前的服务体验不太满意，非常抱歉给您带来困扰。\n\n"
            "我将立即为您转接高级客服专员，他们将全力协助您解决问题。\n"
            "请稍候，正在为您优先安排..."
        ),
    }

    return responses.get(reason, "正在为您转接人工客服，请稍候...")


def analyze_sentiment(text: str) -> float:
    """
    简单的情绪分析 - 模拟实现

    Args:
        text: 待分析的文本

    Returns:
        float: 情绪分数 (-1.0 ~ 1.0)，负值表示负面情绪
    """
    negative_words = [
        "糟糕",
        "失望",
        "愤怒",
        "不满",
        "差劲",
        "垃圾",
        "投诉",
        "terrible",
        "angry",
        "frustrated",
        "bad",
        "worst",
    ]
    positive_words = [
        "很好",
        "满意",
        "感谢",
        "不错",
        "excellent",
        "great",
        "thanks",
        "good",
        "happy",
    ]

    text_lower = text.lower()

    negative_count = sum(1 for word in negative_words if word in text_lower)
    positive_count = sum(1 for word in positive_words if word in text_lower)

    if negative_count > positive_count:
        return -0.8
    elif positive_count > negative_count:
        return 0.8
    else:
        return 0.0


def check_if_resolved(intent_result: MockIntentResult, response: str) -> bool:
    """
    检查问题是否可能已解决 - 启发式判断

    Args:
        intent_result: 意图识别结果
        response: 系统响应

    Returns:
        bool: 问题是否可能已解决
    """
    unresolved_indicators = [
        "抱歉",
        "无法",
        "未找到",
        "不清楚",
        "sorry",
        "cannot",
        "unable",
        "需要更多信息",
    ]

    return not any(indicator in response for indicator in unresolved_indicators)


# ============================================================================
# Langfuse追踪装饰器（简化版，用于演示）
# ============================================================================


def trace_customer_service(name: str = "customer_service", tags: list = None):
    """
    Langfuse追踪装饰器 - 简化版

    在实际项目中，这会创建完整的Langfuse trace
    这里仅作演示，打印追踪信息
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            print(f"\n📊 [Langfuse Trace] 创建追踪: {name}")
            print(f"   Tags: {tags or []}")
            print(f"   Session ID: {kwargs.get('session_id', 'N/A')}")
            print(f"   User ID: {kwargs.get('user_id', 'N/A')}")
            result = await func(*args, **kwargs)
            print("   ✓ 追踪完成")
            return result

        return wrapper

    return decorator


def create_span(name: str, input_data: dict = None):
    """
    创建Span - 简化版

    在实际项目中，这会创建Langfuse span用于细粒度追踪
    """

    class MockSpan:
        def __init__(self, name, input_data):
            self.name = name
            self.input_data = input_data
            self.start_time = time.time()
            print(f"   └─ Span开始: {name}")
            if input_data:
                print(f"      输入: {str(input_data)[:100]}")

        def end(self, output_data: dict = None):
            duration = (time.time() - self.start_time) * 1000
            print(f"      ✓ Span结束 (耗时: {duration:.0f}ms)")
            if output_data:
                print(f"      输出: {str(output_data)[:100]}")

    return MockSpan(name, input_data)


def add_comprehensive_scores(**kwargs):
    """
    添加综合评分 - 简化版

    在实际项目中，这会将多个维度的评分发送到Langfuse
    """
    print("   📈 [Scores] 添加评分指标:")
    for key, value in kwargs.items():
        print(f"      - {key}: {value}")


# ============================================================================
# 主客户服务类
# ============================================================================


class SmartCustomerService:
    """
    智能客服系统 - 完整实现

     orchestrates the complete customer service interaction flow
    with full Langfuse tracing integration
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
        处理用户消息的完整流程

        流程步骤:
        1. 意图识别 - 理解用户想要什么
        2. 会话状态更新 - 维护对话上下文
        3. 情绪分析 - 评估用户情绪状态
        4. 升级评估 - 判断是否需要转人工
        5. 响应生成 - 根据意图生成合适响应
        6. 评分记录 - 记录交互质量指标

        Args:
            user_message: 用户输入消息
            session_id: 唯一会话标识符
            user_id: 用户标识符
            metadata: 额外元数据（渠道、优先级等）

        Returns:
            Dict: 包含响应内容和元数据的字典
        """
        start_time = time.time()
        metadata = metadata or {}

        print(f"\n{'='*70}")
        print("💬 收到用户消息")
        print(f"{'='*70}")
        print(f"消息内容: {user_message}")
        print(f"会话ID: {session_id}")
        print(f"用户ID: {user_id}")
        print(f"元数据: {metadata}")

        try:
            # ===== Step 1: 意图识别 =====
            print(f"\n{'─'*70}")
            print("🔍 Step 1: 意图识别")
            print(f"{'─'*70}")

            intent_span = create_span(
                name="step_1_intent_recognition", input_data={"user_message": user_message}
            )
            intent_result = await recognize_user_intent(user_message, session_id)
            intent_span.end(
                output_data={"intent": intent_result.intent, "confidence": intent_result.confidence}
            )
            print(f"   识别结果: {intent_result.intent}")
            print(f"   置信度: {intent_result.confidence:.2f}")
            print(f"   提取槽位: {intent_result.slots}")

            # ===== Step 2: 更新会话状态 =====
            print(f"\n{'─'*70}")
            print("📝 Step 2: 会话状态更新")
            print(f"{'─'*70}")

            state_span = create_span(
                name="step_2_state_update", input_data={"session_id": session_id}
            )
            conversation_state = await update_conversation_state(
                session_id=session_id,
                user_input=user_message,
                bot_response="",
                metadata={"intent": intent_result.intent, "extracted_slots": intent_result.slots},
            )
            state_span.end(output_data={"turn_count": conversation_state.turn_count})
            print(f"   当前轮次: {conversation_state.turn_count}")

            # ===== Step 3: 情绪分析 =====
            print(f"\n{'─'*70}")
            print("😊 Step 3: 用户情绪分析")
            print(f"{'─'*70}")

            sentiment = analyze_sentiment(user_message)
            sentiment_label = (
                "正面" if sentiment > 0.3 else ("负面" if sentiment < -0.3 else "中性")
            )
            print(f"   情绪分数: {sentiment:.2f} ({sentiment_label})")

            # ===== Step 4: 升级评估 =====
            print(f"\n{'─'*70}")
            print("⚠️  Step 4: 升级需求评估")
            print(f"{'─'*70}")

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
            print(f"   是否需要升级: {escalation_decision.should_escalate}")
            if escalation_decision.should_escalate:
                print(f"   升级原因: {escalation_decision.reason.value}")

            # ===== Step 5: 生成响应 =====
            if escalation_decision.should_escalate:
                # --- 升级路径 ---
                print(f"\n{'─'*70}")
                print("🔄 Step 5: 生成降级响应（升级路径）")
                print(f"{'─'*70}")

                response_span = create_span(
                    name="step_4_fallback_response",
                    input_data={"reason": escalation_decision.reason.value},
                )

                response_text = await get_fallback_response(
                    session_id=session_id, reason=escalation_decision.reason.value
                )

                response_span.end(output_data={"response_length": len(response_text)})
                print(f"   响应长度: {len(response_text)} 字符")

                # 更新会话状态
                await update_conversation_state(
                    session_id=session_id,
                    user_input=user_message,
                    bot_response=response_text,
                    metadata={},
                )

                # 记录评分
                processing_time = (time.time() - start_time) * 1000
                add_comprehensive_scores(
                    intent_confidence=intent_result.confidence,
                    issue_resolved=False,
                    response_latency_ms=processing_time,
                    failure_type="escalation_required",
                    escalation_required=True,
                    escalation_reason=escalation_decision.reason.value,
                )

                result = {
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
                # --- 正常处理路径 ---
                print(f"\n{'─'*70}")
                print("✅ Step 5: 生成响应（正常路径）")
                print(f"{'─'*70}")

                response_span = create_span(
                    name="step_4_normal_processing", input_data={"intent": intent_result.intent}
                )

                response_text = await self._process_by_intent(
                    intent_result, session_id, user_message
                )

                response_span.end(output_data={"response_length": len(response_text)})
                print(f"   响应长度: {len(response_text)} 字符")

                # 更新会话状态
                await update_conversation_state(
                    session_id=session_id,
                    user_input=user_message,
                    bot_response=response_text,
                    metadata={},
                )

                # 判断问题是否解决
                issue_resolved = check_if_resolved(intent_result, response_text)

                # 记录评分
                processing_time = (time.time() - start_time) * 1000
                add_comprehensive_scores(
                    intent_confidence=intent_result.confidence,
                    issue_resolved=issue_resolved,
                    response_latency_ms=processing_time,
                    escalation_required=False,
                )

                result = {
                    "success": True,
                    "response": response_text,
                    "escalated": False,
                    "intent": intent_result.intent,
                    "issue_resolved": issue_resolved,
                    "session_id": session_id,
                    "turn_count": conversation_state.turn_count + 1,
                    "processing_time_ms": processing_time,
                }

            # 打印最终结果
            print(f"\n{'='*70}")
            print("📤 系统响应")
            print(f"{'='*70}")
            print(result["response"])
            print(f"\n处理耗时: {result['processing_time_ms']:.0f}ms")
            print(f"是否升级: {result['escalated']}")
            if result.get("issue_resolved") is not None:
                print(f"问题解决: {result['issue_resolved']}")

            return result

        except Exception as e:
            # 错误处理
            print(f"\n❌ 错误: {str(e)}")
            error_response = "抱歉，系统遇到了一些问题。请稍后重试或联系人工客服。"

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
            }

    async def _process_by_intent(
        self, intent_result: MockIntentResult, session_id: str, user_message: str = ""
    ) -> str:
        """
        根据识别的意图处理请求

        Args:
            intent_result: 意图识别结果
            session_id: 会话ID
            user_message: 用户原始消息（用于通用查询）

        Returns:
            str: 生成的响应文本
        """
        intent = intent_result.intent
        slots = intent_result.slots

        if intent == "api_error_troubleshooting":
            # 使用RAG查询故障排除方案
            query = f"API error {slots.get('error_code', '')}"
            result = await query_knowledge_base(query, session_id)
            return result["answer"]

        elif intent == "ticket_status_query":
            # 调用工具查询工单状态
            if "ticket_id" in slots and slots["ticket_id"]:
                tool_result = await call_tool(
                    "query_ticket_status", {"ticket_id": slots["ticket_id"]}
                )
                if tool_result["success"]:
                    data = tool_result["result"]
                    return (
                        f"📋 工单查询结果:\n\n"
                        f"工单号: {data['ticket_id']}\n"
                        f"状态: {data['status']}\n"
                        f"优先级: {data['priority']}\n"
                        f"负责人: {data['assigned_to']}\n"
                        f"最后更新: {data['last_updated']}\n"
                        f"问题描述: {data['description']}"
                    )
            return "请提供工单号以便我为您查询状态。"

        elif intent == "product_information":
            # 使用RAG获取产品信息
            result = await query_knowledge_base(
                f"product information {slots.get('product_name', '')}", session_id
            )
            return result["answer"]

        elif intent == "general_inquiry" or intent == "general_technical_issue":
            # 一般咨询 - 使用RAG
            result = await query_knowledge_base(user_message, session_id)
            return result["answer"]

        else:
            # 默认使用RAG处理其他意图
            result = await query_knowledge_base(user_message, session_id)
            return result["answer"]


# ============================================================================
# 演示场景
# ============================================================================


async def scenario_1_api_error_troubleshooting():
    """
    场景1: API错误排查

    演示:
    - 用户报告API调用返回403错误
    - 系统识别意图为"api_error_troubleshooting"
    - 从知识库检索相关解决方案
    - 返回结构化的故障排除步骤

    预期结果:
    - 意图置信度高 (>0.9)
    - 成功从知识库获取解决方案
    - 问题标记为已解决
    - 无需升级
    """
    print("\n" + "=" * 70)
    print("📌 场景1: API错误排查")
    print("=" * 70)
    print("\n场景描述:")
    print("  用户在调用API时收到403 Forbidden错误，寻求技术支持。")
    print("  系统需要识别问题类型，从知识库检索解决方案，并提供清晰的")
    print("  故障排除步骤。")
    print("\n核心价值展示:")
    print("  ✓ 意图识别准确性")
    print("  ✓ RAG知识库检索能力")
    print("  ✓ 结构化响应生成")
    print("  ✓ 完整的Langfuse追踪链路")
    print("=" * 70)

    service = SmartCustomerService()

    response = await service.handle_message(
        user_message="我的API调用返回403错误，怎么办？",
        session_id="session_tech_demo_001",
        user_id="user_demo_123",
        metadata={"channel": "web_chat", "priority": "high"},
    )

    print("\n" + "-" * 70)
    print("📊 场景1分析总结:")
    print("-" * 70)
    print(f"  意图类型: {response['intent']}")
    print("  置信度: 0.92 (高)")
    print(f"  是否升级: {response['escalated']}")
    print(f"  问题解决: {response.get('issue_resolved', 'N/A')}")
    print(f"  处理耗时: {response['processing_time_ms']:.0f}ms")
    print("\n  💡 关键点:")
    print("     - 系统准确识别了'403错误'这一技术关键词")
    print("     - 从知识库返回了4条具体的排查步骤")
    print("     - 响应包含 actionable 的建议，而非泛泛而谈")
    print("     - 整个流程在Langfuse中有完整的trace记录")


async def scenario_2_ticket_status_query():
    """
    场景2: 工单状态查询

    演示:
    - 用户查询特定工单的状态
    - 系统提取工单号作为槽位
    - 调用外部工具查询工单详情
    - 返回格式化的工单信息

    预期结果:
    - 正确提取工单号 TKT-12345
    - 成功调用工具获取工单数据
    - 返回结构化的工单信息
    """
    print("\n" + "=" * 70)
    print("📌 场景2: 工单状态查询")
    print("=" * 70)
    print("\n场景描述:")
    print("  用户想要查询工单TKT-12345的当前状态和处理进度。")
    print("  系统需要从用户消息中提取工单号，调用工单系统API，")
    print("  并返回清晰的状态信息。")
    print("\n核心价值展示:")
    print("  ✓ 实体提取能力（工单号识别）")
    print("  ✓ 工具调用集成")
    print("  ✓ 结构化数据展示")
    print("  ✓ 实时数据获取")
    print("=" * 70)

    service = SmartCustomerService()

    response = await service.handle_message(
        user_message="帮我查一下工单TKT-12345的状态",
        session_id="session_tech_demo_002",
        user_id="user_demo_456",
        metadata={"channel": "mobile_app"},
    )

    print("\n" + "-" * 70)
    print("📊 场景2分析总结:")
    print("-" * 70)
    print(f"  意图类型: {response['intent']}")
    print("  置信度: 0.88 (高)")
    print(f"  是否升级: {response['escalated']}")
    print(f"  问题解决: {response.get('issue_resolved', 'N/A')}")
    print(f"  处理耗时: {response['processing_time_ms']:.0f}ms")
    print("\n  💡 关键点:")
    print("     - 系统成功从自然语言中提取了工单号'TKT-12345'")
    print("     - 调用了query_ticket_status工具获取实时数据")
    print("     - 返回了包含状态、优先级、负责人等信息的完整工单详情")
    print("     - 展示了系统与外部工具的无缝集成能力")


async def scenario_3_complex_multi_turn_with_escalation():
    """
    场景3: 复杂技术问题（多轮对话 + 转人工触发）

    演示:
    - 第1轮: 用户模糊描述问题，系统尝试澄清
    - 第2轮: 用户提供更多上下文，但仍不够明确
    - 第3轮: 用户明确要求转人工，触发升级

    预期结果:
    - 前两轮正常处理，尝试提供帮助
    - 第三轮检测到"转人工"意图，触发升级
    - 展示完整的升级流程和友好提示
    """
    print("\n" + "=" * 70)
    print("📌 场景3: 复杂技术问题（多轮对话 + 转人工）")
    print("=" * 70)
    print("\n场景描述:")
    print("  用户遇到一个复杂的技术问题，经过多轮对话后仍未能解决，")
    print("  最终要求转接人工客服。此场景展示系统的上下文管理能力")
    print("  和智能升级机制。")
    print("\n对话流程:")
    print("  Turn 1: '我的系统出问题了' → 系统尝试澄清")
    print("  Turn 2: '就是那个API的问题' → 系统继续追问细节")
    print("  Turn 3: '我要转人工客服' → 触发升级流程")
    print("\n核心价值展示:")
    print("  ✓ 多轮对话上下文管理")
    print("  ✓ 会话状态跟踪")
    print("  ✓ 智能升级决策")
    print("  ✓ 优雅的降级体验")
    print("=" * 70)

    service = SmartCustomerService()
    session_id = "session_tech_demo_003"
    user_id = "user_demo_789"

    # Turn 1: 模糊问题描述
    print("\n" + "-" * 70)
    print("🗣️  Turn 1: 用户模糊描述问题")
    print("-" * 70)

    response = await service.handle_message(
        user_message="我的系统出问题了",
        session_id=session_id,
        user_id=user_id,
        metadata={"channel": "web_chat"},
    )

    print("\n  📝 Turn 1 分析:")
    print(f"     意图: {response['intent']}")
    print("     置信度: 0.65 (较低，因为问题描述模糊)")
    print("     系统策略: 尝试引导用户提供更多细节")

    # Turn 2: 提供更多上下文
    print("\n" + "-" * 70)
    print("🗣️  Turn 2: 用户提供更多上下文")
    print("-" * 70)

    response = await service.handle_message(
        user_message="就是那个API的问题",
        session_id=session_id,
        user_id=user_id,
        metadata={"channel": "web_chat"},
    )

    print("\n  📝 Turn 2 分析:")
    print(f"     意图: {response['intent']}")
    print(f"     会话轮次: {response['turn_count']}")
    print("     系统策略: 继续尝试提供通用API问题解决方案")

    # Turn 3: 明确要求转人工
    print("\n" + "-" * 70)
    print("🗣️  Turn 3: 用户要求转人工")
    print("-" * 70)

    response = await service.handle_message(
        user_message="我要转人工客服",
        session_id=session_id,
        user_id=user_id,
        metadata={"channel": "web_chat"},
    )

    print("\n  📝 Turn 3 分析:")
    print(f"     意图: {response['intent']}")
    print(f"     是否升级: {response['escalated']}")
    print(f"     升级原因: {response.get('escalation_reason', 'N/A')}")
    print("     系统策略: 触发升级流程，提供友好的转接提示")

    print("\n" + "-" * 70)
    print("📊 场景3分析总结:")
    print("-" * 70)
    print(f"  总对话轮次: {response['turn_count']}")
    print("  最终状态: 已升级到人工客服")
    print("  升级原因: user_requested")
    print("\n  💡 关键点:")
    print("     - 系统维护了完整的会话上下文（3轮对话）")
    print("     - 在前两轮中尝试通过澄清和通用方案帮助用户")
    print("     - 当用户明确要求转人工时，立即触发升级流程")
    print("     - 提供了包含预计等待时间的友好提示")
    print("     - 整个过程在Langfuse中作为一个完整的session追踪")


async def run_all_scenarios():
    """运行所有技术支持场景演示"""
    print("\n" + "=" * 70)
    print("🚀 Langfuse 智能客服系统 - 技术支持场景演示")
    print("=" * 70)
    print(f"\n演示时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("演示版本: Tech Support Demo v1.0")
    print("\n本演示将展示3个典型的技术支持场景，每个场景都包含:")
    print("  • 完整的用户交互流程")
    print("  • 详细的Langfuse追踪信息")
    print("  • 多维度评分指标")
    print("  • 清晰的输出和分析总结")
    print("=" * 70)

    # 运行3个场景
    await scenario_1_api_error_troubleshooting()
    await scenario_2_ticket_status_query()
    await scenario_3_complex_multi_turn_with_escalation()

    # 总结
    print("\n" + "=" * 70)
    print("🎉 所有场景演示完成!")
    print("=" * 70)
    print("\n📚 演示回顾:")
    print("  场景1: API错误排查 - 展示RAG知识库检索能力")
    print("  场景2: 工单状态查询 - 展示工具调用集成能力")
    print("  场景3: 复杂多轮对话 - 展示上下文管理和升级机制")
    print("\n💡 核心价值:")
    print("  1. 完整的可观测性: 每个步骤都有Langfuse trace/span记录")
    print("  2. 多维度评估: 意图置信度、问题解决率、响应延迟等指标")
    print("  3. 智能决策: 基于多因素的自动升级机制")
    print("  4. 模块化设计: 意图识别、RAG、工具调用等模块解耦")
    print("\n🔗 查看Langfuse Dashboard:")
    print("  https://cloud.langfuse.com")
    print("  搜索session_id: session_tech_demo_*")
    print("=" * 70)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("⚙️  初始化演示环境...")
    print("=" * 70)

    # 加载环境变量（如果有的话）
    try:
        from dotenv import load_dotenv

        load_dotenv()
        print("✓ .env 文件加载成功")
    except ImportError:
        print("⚠ python-dotenv 未安装，跳过.env加载")
    except Exception as e:
        print(f"⚠ .env 加载警告: {e}")

    print("✓ 演示环境就绪\n")

    # 运行所有场景
    asyncio.run(run_all_scenarios())
