"""
Intent recognition module with Langfuse tracing
Identifies user intent and extracts slots/entities from customer queries
"""

import time
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config.settings import OPENAI_API_KEY
from core.scoring import score_intent_confidence
from core.tracing import create_span, score_trace


class IntentResult(BaseModel):
    """Result of intent recognition"""

    intent: str = Field(description="Detected intent category")
    confidence: float = Field(description="Confidence score (0-1)")
    slots: dict[str, Any] = Field(default_factory=dict, description="Extracted slots")
    entities: list[dict[str, str]] = Field(default_factory=list, description="Recognized entities")


# Supported intents for technical support
SUPPORTED_INTENTS = {
    "api_error_troubleshooting": "API错误排查",
    "account_login_issue": "账户登录问题",
    "billing_payment_question": "账单支付咨询",
    "feature_usage_guidance": "功能使用指导",
    "ticket_status_query": "工单状态查询",
    "product_information": "产品信息查询",
    "technical_documentation": "技术文档查询",
    "general_inquiry": "一般咨询",
    "human_agent_request": "请求人工客服",
}


class IntentRecognitionSystem:
    """Intent recognition system with Langfuse tracing"""

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2, api_key=OPENAI_API_KEY)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是一个技术支持客服系统的意图识别模块。请分析用户的问题，识别其意图并提取关键信息。

支持的意图类型：
{intents}

请返回JSON格式：
{{
    "intent": "意图类型",
    "confidence": 0.0-1.0的置信度,
    "slots": {{提取的槽位信息}},
    "entities": [{{"type": "实体类型", "value": "实体值"}}]
}}

槽位提取规则：
- API相关问题：提取error_code, api_endpoint, http_method
- 工单查询：提取ticket_id
- 账户问题：提取account_type, issue_description
- 产品咨询：提取product_name, feature_name""",
                ),
                ("human", "{user_input}"),
            ]
        )

    async def recognize_intent(
        self, user_message: str, session_id: str | None = None
    ) -> IntentResult:
        """
        Recognize user intent with full Langfuse tracing

        Args:
            user_message: User's input message
            session_id: Session identifier for tracking

        Returns:
            IntentResult with intent, confidence, slots, and entities
        """
        start_time = time.time()

        # Create main span for intent recognition
        with create_span(
            name="intent_recognition",
            input_data={"user_message": user_message},
            metadata={"session_id": session_id},
        ) as main_span:

            # Step 1: Text preprocessing
            preprocess_span = create_span(
                name="text_preprocessing", input_data={"raw_text": user_message}
            )
            cleaned_text = self._preprocess_text(user_message)
            preprocess_span.end(
                output_data={"cleaned_text": cleaned_text, "length": len(cleaned_text)}
            )

            # Step 2: Intent classification with LLM
            classification_span = create_span(
                name="intent_classification",
                input_data={"text": cleaned_text},
                metadata={"model": "gpt-3.5-turbo", "temperature": 0.2},
            )

            intent_result = await self._classify_intent_llm(cleaned_text)

            classification_span.end(
                output_data={
                    "intent": intent_result.intent,
                    "confidence": intent_result.confidence,
                },
                metadata={"processing_time_ms": (time.time() - start_time) * 1000},
            )

            # Step 3: Slot extraction
            slot_span = create_span(
                name="slot_extraction",
                input_data={"text": cleaned_text, "intent": intent_result.intent},
            )
            slots = self._extract_slots(cleaned_text, intent_result.intent)
            slot_span.end(output_data={"slots": slots})
            intent_result.slots = slots

            # Step 4: Named entity recognition
            ner_span = create_span(
                name="named_entity_recognition", input_data={"text": cleaned_text}
            )
            entities = self._recognize_entities(cleaned_text)
            ner_span.end(output_data={"entities": entities})
            intent_result.entities = entities

            # Calculate overall quality score
            processing_time = (time.time() - start_time) * 1000
            quality_score = self._calculate_quality_score(
                intent_result.confidence, len(slots), len(entities), processing_time
            )

            # Add scores
            score_intent_confidence(
                intent_result.confidence, comment=f"Intent: {intent_result.intent}"
            )

            score_trace(
                name="recognition_quality",
                value=quality_score,
                data_type="NUMERIC",
                comment="Overall recognition quality score",
            )

            # Update main span
            main_span.end(
                output_data={
                    "intent": intent_result.intent,
                    "confidence": intent_result.confidence,
                    "slots_count": len(slots),
                    "entities_count": len(entities),
                    "processing_time_ms": processing_time,
                }
            )

            return intent_result

    def _preprocess_text(self, text: str) -> str:
        """Preprocess user input text"""
        # Remove extra whitespace
        text = " ".join(text.split())
        # Convert to lowercase for consistency
        text = text.lower()
        return text

    async def _classify_intent_llm(self, text: str) -> IntentResult:
        """Use LLM to classify intent"""
        intents_list = "\n".join([f"- {key}: {value}" for key, value in SUPPORTED_INTENTS.items()])

        prompt_with_intents = self.prompt.partial(intents=intents_list)
        chain = prompt_with_intents | self.llm

        response = await chain.ainvoke({"user_input": text})

        # Parse JSON response (in production, use structured output)
        try:
            import json

            result_dict = json.loads(response.content)
            return IntentResult(
                intent=result_dict.get("intent", "general_inquiry"),
                confidence=float(result_dict.get("confidence", 0.5)),
                slots=result_dict.get("slots", {}),
                entities=result_dict.get("entities", []),
            )
        except Exception:
            # Fallback to general inquiry if parsing fails
            return IntentResult(intent="general_inquiry", confidence=0.3, slots={}, entities=[])

    def _extract_slots(self, text: str, intent: str) -> dict[str, Any]:
        """Extract slots based on intent"""
        slots = {}

        # Extract error codes (e.g., 403, 500, 404)
        import re

        error_codes = re.findall(r"\b(4\d{2}|5\d{2})\b", text)
        if error_codes:
            slots["error_code"] = error_codes[0]

        # Extract ticket IDs (pattern: TKT-XXXXX or ticket number)
        ticket_ids = re.findall(r"(?:TKT-|ticket\s*#?)(\w+)", text, re.IGNORECASE)
        if ticket_ids:
            slots["ticket_id"] = ticket_ids[0]

        # Extract API endpoints
        endpoints = re.findall(r"(/[\w/-]+)", text)
        if endpoints:
            slots["api_endpoint"] = endpoints[0]

        # Extract HTTP methods
        methods = re.findall(r"\b(GET|POST|PUT|DELETE|PATCH)\b", text, re.IGNORECASE)
        if methods:
            slots["http_method"] = methods[0].upper()

        return slots

    def _recognize_entities(self, text: str) -> list[dict[str, str]]:
        """Recognize named entities"""
        entities = []

        # Simple pattern-based entity recognition
        import re

        # Email addresses
        emails = re.findall(r"\b[\w.-]+@[\w.-]+\.\w+\b", text)
        for email in emails:
            entities.append({"type": "email", "value": email})

        # Phone numbers
        phones = re.findall(r"\b1[3-9]\d{9}\b", text)
        for phone in phones:
            entities.append({"type": "phone", "value": phone})

        # Version numbers
        versions = re.findall(r"\bv?\d+\.\d+(\.\d+)?\b", text, re.IGNORECASE)
        for version in versions:
            entities.append({"type": "version", "value": version})

        return entities

    def _calculate_quality_score(
        self, confidence: float, slots_count: int, entities_count: int, processing_time_ms: float
    ) -> float:
        """Calculate overall recognition quality score (0-1)"""
        # Weight different factors
        confidence_weight = 0.5
        slots_weight = 0.2
        entities_weight = 0.15
        speed_weight = 0.15

        # Confidence component
        confidence_score = confidence

        # Slots component (more slots = better, up to 3)
        slots_score = min(slots_count / 3.0, 1.0)

        # Entities component
        entities_score = min(entities_count / 2.0, 1.0)

        # Speed component (< 500ms is ideal)
        speed_score = max(0, 1.0 - (processing_time_ms / 1000))

        # Weighted average
        quality = (
            confidence_weight * confidence_score
            + slots_weight * slots_score
            + entities_weight * entities_score
            + speed_weight * speed_score
        )

        return round(quality, 2)


# Singleton instance
intent_system = IntentRecognitionSystem()


async def recognize_user_intent(
    user_message: str, session_id: str | None = None
) -> IntentResult:
    """
    Convenience function to recognize user intent

    Args:
        user_message: User's input message
        session_id: Session identifier

    Returns:
        IntentResult with recognized intent and extracted information
    """
    return await intent_system.recognize_intent(user_message, session_id)


# Export
__all__ = ["IntentResult", "IntentRecognitionSystem", "recognize_user_intent", "SUPPORTED_INTENTS"]
