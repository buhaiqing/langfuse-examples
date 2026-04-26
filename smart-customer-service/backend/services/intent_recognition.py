"""意图识别服务"""

import re
from dataclasses import dataclass
from typing import Any

from core.llm_client_pool import get_chat_client
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


# ==================== 数据模型 ====================
@dataclass
class IntentRecognitionResult:
    """意图识别结果"""

    intent: str
    confidence: float
    slots: dict[str, Any]
    entities: list[dict[str, Any]]
    raw_response: str | None = None


@dataclass
class Entity:
    """实体"""

    entity_type: str
    value: str
    original_text: str


# ==================== 意图定义 ====================
INTENT_DEFINITIONS = {
    "api_error_troubleshooting": {
        "description": "API 错误排查",
        "required_slots": ["error_code"],
        "optional_slots": ["api_endpoint", "http_method"],
        "example": "我的 API 返回 403 错误",
    },
    "account_login_issue": {
        "description": "账户登录问题",
        "required_slots": ["account"],
        "optional_slots": ["error_message"],
        "example": "我登录不了账户",
    },
    "billing_payment_question": {
        "description": "账单支付问题",
        "required_slots": [],
        "optional_slots": ["billing_type", "amount"],
        "example": "我的账单有问题",
    },
    "feature_usage_guidance": {
        "description": "功能使用指导",
        "required_slots": [],
        "optional_slots": ["feature_name"],
        "example": "这个功能怎么用",
    },
    "ticket_status_query": {
        "description": "工单状态查询",
        "required_slots": ["ticket_id"],
        "optional_slots": [],
        "example": "查询工单 TKT-12345 的状态",
    },
    "product_information": {
        "description": "产品信息",
        "required_slots": [],
        "optional_slots": ["product_name", "category"],
        "example": "你们有什么产品",
    },
    "technical_documentation": {
        "description": "技术文档",
        "required_slots": [],
        "optional_slots": ["doc_type", "api_name"],
        "example": "API 文档在哪里",
    },
    "general_inquiry": {
        "description": "一般咨询",
        "required_slots": [],
        "optional_slots": [],
        "example": "你好",
    },
    "human_agent_request": {
        "description": "转人工请求",
        "required_slots": [],
        "optional_slots": ["reason"],
        "example": "转人工客服",
    },
}


# ==================== LLM 输出模型 ====================
class IntentOutput(BaseModel):
    """LLM 意图识别输出"""

    intent: str = Field(
        description=(
            "意图类型，必须是以下之一：api_error_troubleshooting, "
            "account_login_issue, billing_payment_question, "
            "feature_usage_guidance, ticket_status_query, "
            "product_information, technical_documentation, "
            "general_inquiry, human_agent_request"
        )
    )
    confidence: float = Field(description="置信度，0.0 到 1.0 之间")
    slots: dict[str, Any] = Field(description="提取的槽位信息")
    reasoning: str = Field(description="判断理由")


class EntityOutput(BaseModel):
    """LLM 实体识别输出"""

    entities: list[dict[str, str]] = Field(
        description="识别的实体列表，每个实体包含 entity_type 和 value"
    )


# ==================== 意图识别服务 ====================
class IntentRecognitionService:
    """意图识别服务"""

    def __init__(self):
        self.llm = get_chat_client(temperature=0)

        self.intent_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是一个智能客服意图识别助手。根据用户消息，识别其意图。

可用的意图类型：
{intent_definitions}

输出要求：
1. intent 必须是上述意图类型之一
2. confidence 是 0.0 到 1.0 的数值，表示置信度
3. slots 是提取的关键信息
4. reasoning 说明判断理由""",
                ),
                (
                    "user",
                    """用户消息：{user_message}

{context}""",
                ),
            ]
        )

        self.entity_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """识别用户消息中的实体。

支持的实体类型：
- email: 邮箱地址
- phone: 手机号
- error_code: 错误代码 (如 403, 500)
- api_endpoint: API 端点
- ticket_id: 工单号
- version: 版本号
- account: 账户名""",
                ),
                ("user", """用户消息：{user_message}"""),
            ]
        )

        self.intent_parser = JsonOutputParser(pydantic_object=IntentOutput)
        self.entity_parser = JsonOutputParser(pydantic_object=EntityOutput)

    def preprocess_text(self, text: str) -> str:
        """
        文本预处理
        """
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        text = text[:500]
        return text

    async def recognize(
        self, user_message: str, context: dict | None = None
    ) -> IntentRecognitionResult:
        """
        意图识别主方法
        """
        preprocessed = self.preprocess_text(user_message)
        context_str = self._format_context(context)
        intent_definitions_str = self._format_intent_definitions()

        intent_result = await self._recognize_intent(
            preprocessed, context_str, intent_definitions_str
        )

        entities = await self._recognize_entities(preprocessed)

        return IntentRecognitionResult(
            intent=intent_result.intent,
            confidence=intent_result.confidence,
            slots=intent_result.slots,
            entities=[{"type": e["entity_type"], "value": e["value"]} for e in entities],
            raw_response=str(intent_result),
        )

    def _format_context(self, context: dict | None) -> str:
        if not context:
            return "无上下文信息"

        parts = []
        if context.get("previous_messages"):
            parts.append(f"历史消息：{len(context['previous_messages'])} 条")
        if context.get("collected_slots"):
            slots = context["collected_slots"]
            parts.append(f"已收集槽位：{slots}")

        return "\n".join(parts) if parts else "无额外上下文"

    def _format_intent_definitions(self) -> str:
        lines = []
        for intent_type, info in INTENT_DEFINITIONS.items():
            lines.append(f"- {intent_type}: {info['description']} (示例：{info['example']})")
        return "\n".join(lines)

    async def _recognize_intent(self, message: str, context: str, definitions: str) -> IntentOutput:
        prompt = await self.intent_prompt.ainvoke(
            {"user_message": message, "context": context, "intent_definitions": definitions}
        )

        response = await self.llm.ainvoke(prompt)
        result = await self.intent_parser.ainvoke(response)

        return IntentOutput(
            intent=result["intent"],
            confidence=result.get("confidence", 0.5),
            slots=result.get("slots", {}),
            reasoning=result.get("reasoning", ""),
        )

    async def _recognize_entities(self, message: str) -> list[dict[str, str]]:
        prompt = await self.entity_prompt.ainvoke({"user_message": message})

        response = await self.llm.ainvoke(prompt)
        result = await self.entity_parser.ainvoke(response)

        return result.get("entities", [])

    async def extract_slots(self, user_message: str, intent: str) -> dict[str, Any]:
        """
        提取槽位
        """
        entities = await self._recognize_entities(user_message)

        slots = {}
        for entity in entities:
            entity_type = entity["entity_type"]
            value = entity["value"]

            if entity_type == "email" and intent in ["account_login_issue"]:
                slots["email"] = value
            elif entity_type == "error_code" and intent in ["api_error_troubleshooting"]:
                slots["error_code"] = value
            elif entity_type == "ticket_id" and intent in ["ticket_status_query"]:
                slots["ticket_id"] = value
            elif entity_type == "api_endpoint" and intent in ["api_error_troubleshooting"]:
                slots["api_endpoint"] = value

        return slots

    async def recognize_entities(self, user_message: str) -> list[Entity]:
        """
        实体识别
        """
        entities = await self._recognize_entities(user_message)

        return [
            Entity(entity_type=e["entity_type"], value=e["value"], original_text=user_message)
            for e in entities
        ]

    def calculate_confidence(
        self, llm_confidence: float, slots_completeness: float, context_match: float
    ) -> float:
        """
        计算综合置信度
        """
        weights = {"llm": 0.5, "slots": 0.3, "context": 0.2}

        confidence = (
            llm_confidence * weights["llm"]
            + slots_completeness * weights["slots"]
            + context_match * weights["context"]
        )

        return min(1.0, max(0.0, confidence))


intent_service = IntentRecognitionService()
