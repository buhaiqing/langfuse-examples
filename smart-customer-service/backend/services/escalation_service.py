"""升级管理服务模块"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from core.config import settings
from storage.redis_client import redis_client


@dataclass
class EscalationRequest:
    """升级请求"""

    session_id: str
    user_id: str
    priority_score: float
    priority_level: str  # critical/high/medium/low
    trigger_reasons: List[str]
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class EscalationService:
    """升级管理服务"""

    def __init__(self):
        self.llm = ChatOpenAI(model=settings.openai_model, temperature=0.1)

        # 情绪分析提示词
        self.sentiment_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """分析用户消息的情绪。

评分范围：-1.0 (非常负面) 到 1.0 (非常正面)
- < -0.7: 非常负面情绪
- -0.7 ~ -0.3: 负面情绪
- -0.3 ~ 0.3: 中性
- > 0.3: 正面

输出 JSON: {"score": -0.5, "reasoning": "分析理由"}""",
                ),
                ("user", "用户消息：{message}"),
            ]
        )

    async def check_escalation(
        self,
        session_id: str,
        user_id: str,
        intent_confidence: float,
        user_message: str,
        failure_count: int = 0,
        is_vip: bool = False,
    ) -> bool:
        """
        检查是否需要升级

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            intent_confidence: 意图置信度
            user_message: 用户消息
            failure_count: 连续失败次数
            is_vip: 是否 VIP 客户

        Returns:
            是否需要升级
        """
        trigger_reasons = []
        priority_score = 0.0

        # 1. 低置信度触发
        if intent_confidence < 0.5:
            trigger_reasons.append("low_confidence")
            priority_score += (0.5 - intent_confidence) / 0.5 * 10

        # 2. 负面情绪触发
        sentiment = await self.analyze_sentiment(user_message)
        if sentiment.score < -0.7:
            trigger_reasons.append("negative_sentiment")
            priority_score += abs(sentiment.score) * 15

        # 3. VIP 客户
        if is_vip:
            trigger_reasons.append("vip_customer")
            priority_score += 40

        # 4. 连续失败
        if failure_count >= 3:
            trigger_reasons.append("consecutive_failures")
            priority_score += failure_count * 10

        # 5. 敏感关键词
        sensitive_keywords = ["投诉", "起诉", "媒体", "曝光", "315", "工商局"]
        if any(keyword in user_message for keyword in sensitive_keywords):
            trigger_reasons.append("sensitive_keywords")
            priority_score += 50

        # 判定升级阈值：>= 40 分需要升级
        needs_escalation = priority_score >= 40

        if needs_escalation:
            escalation = EscalationRequest(
                session_id=session_id,
                user_id=user_id,
                priority_score=priority_score,
                priority_level=self._calculate_priority_level(priority_score),
                trigger_reasons=trigger_reasons,
                context={
                    "sentiment_score": sentiment.score,
                    "intent_confidence": intent_confidence,
                },
            )

            # 添加到升级队列
            await redis_client.add_to_escalation_queue(session_id, priority_score)

        return needs_escalation

    async def analyze_sentiment(self, message: str) -> object:
        """分析情绪"""
        response = await self.llm.ainvoke(await self.sentiment_prompt.ainvoke({"message": message}))

        content = response.content if hasattr(response, "content") else str(response)

        class SentimentResult:
            def __init__(self, score: float, reasoning: str):
                self.score = score
                self.reasoning = reasoning

        import json

        try:
            data = json.loads(content)
            return SentimentResult(
                score=float(data.get("score", 0)),
                reasoning=data.get("reasoning", ""),
            )
        except:
            return SentimentResult(score=0, reasoning="无法解析")

    def _calculate_priority_level(self, score: float) -> str:
        """计算优先级等级"""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"


# 全局服务实例
escalation_service = EscalationService()
