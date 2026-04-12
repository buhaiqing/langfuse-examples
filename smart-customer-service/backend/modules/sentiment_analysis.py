"""
Sentiment analysis module with multiple backend support
Provides accurate sentiment detection for customer messages
"""

import time
from abc import ABC, abstractmethod
from typing import Any

import httpx
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from config.settings import OPENAI_API_KEY, SENTIMENT_API_KEY, SENTIMENT_API_URL, SENTIMENT_USE_OPENAI
from core.logging_config import LogCategory, get_logger
from core.tracing import create_span

logger = get_logger(LogCategory.CUSTOMER_SERVICE)


class SentimentResult:
    """Result of sentiment analysis"""

    def __init__(
        self,
        score: float,
        label: str,
        confidence: float,
        provider: str,
    ):
        self.score = score
        self.label = label
        self.confidence = confidence
        self.provider = provider

    def __repr__(self) -> str:
        return f"SentimentResult(score={self.score:.2f}, label={self.label}, confidence={self.confidence:.2f})"


class SentimentAnalyzer(ABC):
    """Abstract base class for sentiment analysis providers"""

    @abstractmethod
    async def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment of the given text"""
        pass


class OpenAISentimentAnalyzer(SentimentAnalyzer):
    """Sentiment analyzer using OpenAI"""

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1, api_key=OPENAI_API_KEY)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a sentiment analysis expert. Analyze the sentiment of the user message.

Output a JSON object with:
- score: float from -1 (very negative) to 1 (very positive)
- label: "positive", "neutral", or "negative"
- confidence: float from 0 to 1 indicating confidence in the analysis

Be accurate and consider context, especially customer service scenarios.""",
                ),
                ("human", "{text}"),
            ]
        )
        self.chain = self.prompt | self.llm

    async def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment using OpenAI"""
        start_time = time.time()
        logger.debug(f"Analyzing sentiment with OpenAI: '{text[:50]}...'")

        with create_span(
            name="sentiment_analysis_openai",
            input_data={"text": text},
            metadata={"provider": "openai"},
        ) as span:
            try:
                response = await self.chain.ainvoke({"text": text})
                import json

                result = json.loads(response.content)

                score = float(result.get("score", 0.0))
                label = result.get("label", "neutral")
                confidence = float(result.get("confidence", 0.5))

                span.end(
                    output_data={"score": score, "label": label, "confidence": confidence},
                    metadata={"latency_ms": (time.time() - start_time) * 1000},
                )

                return SentimentResult(
                    score=score, label=label, confidence=confidence, provider="openai"
                )
            except Exception as e:
                logger.error(f"OpenAI sentiment analysis failed: {e}")
                span.end(output_data={"error": str(e)})
                return SentimentResult(score=0.0, label="neutral", confidence=0.0, provider="openai")


class ExternalAPISentimentAnalyzer(SentimentAnalyzer):
    """Sentiment analyzer using external API"""

    def __init__(self):
        self.api_url = SENTIMENT_API_URL
        self.api_key = SENTIMENT_API_KEY
        self.http_client = httpx.AsyncClient(timeout=30.0) if SENTIMENT_API_URL else None

    async def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment using external API"""
        start_time = time.time()
        logger.debug(f"Analyzing sentiment with external API: '{text[:50]}...'")

        with create_span(
            name="sentiment_analysis_external",
            input_data={"text": text, "api_url": self.api_url},
            metadata={"provider": "external_api"},
        ) as span:
            try:
                if not self.http_client or not self.api_url:
                    raise ValueError("External sentiment API not configured")

                response = await self.http_client.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"text": text, "language": "auto"},
                )
                response.raise_for_status()
                data = response.json()

                score = float(data.get("score", 0.0))
                label = data.get("label", "neutral")
                confidence = float(data.get("confidence", 0.5))

                span.end(
                    output_data={"score": score, "label": label, "confidence": confidence},
                    metadata={"latency_ms": (time.time() - start_time) * 1000},
                )

                return SentimentResult(
                    score=score, label=label, confidence=confidence, provider="external_api"
                )
            except Exception as e:
                logger.error(f"External API sentiment analysis failed: {e}")
                span.end(output_data={"error": str(e)})
                return SentimentResult(score=0.0, label="neutral", confidence=0.0, provider="external_api")


class KeywordBasedSentimentAnalyzer(SentimentAnalyzer):
    """Fallback keyword-based sentiment analyzer"""

    def __init__(self):
        self.negative_keywords = [
            "糟糕", "失望", "愤怒", "不满", "差劲", "垃圾", "无用", "无用",
            "讨厌", "恨", "投诉", "非常不满", "terrible", "awful", "horrible",
            "angry", "frustrated", "disappointed", "unacceptable", "worst", "hate",
            "furious", "outraged", "pathetic", "useless", "broken",
        ]
        self.positive_keywords = [
            "很好", "满意", "感谢", "棒", "优秀", "完美", "出色", "赞",
            "太好了", "非常好", "excellent", "great", "wonderful", "amazing",
            "fantastic", "perfect", "outstanding", "brilliant", "superb", "thanks",
            "grateful", "appreciate", "love", "helpful",
        ]
        self.intensity_modifiers = {
            "非常": 1.5, "极其": 1.8, "特别": 1.4, "十分": 1.4,
            "very": 1.5, "extremely": 1.8, "really": 1.3, "absolutely": 1.6,
            "有点": 0.5, "稍微": 0.5, "有点": 0.5,
            "slightly": 0.5, "a bit": 0.5, "kind of": 0.5,
        }

    async def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment using keyword matching"""
        logger.debug(f"Analyzing sentiment with keywords: '{text[:50]}...'")

        with create_span(
            name="sentiment_analysis_keyword",
            input_data={"text": text},
            metadata={"provider": "keyword"},
        ) as span:
            text_lower = text.lower()

            negative_score = 0.0
            positive_score = 0.0

            for keyword in self.negative_keywords:
                if keyword.lower() in text_lower:
                    intensity = self._get_intensity(text_lower, keyword)
                    negative_score += intensity

            for keyword in self.positive_keywords:
                if keyword.lower() in text_lower:
                    intensity = self._get_intensity(text_lower, keyword)
                    positive_score += intensity

            if negative_score > positive_score:
                score = -min(negative_score / 3.0, 1.0)
                label = "negative"
            elif positive_score > negative_score:
                score = min(positive_score / 3.0, 1.0)
                label = "positive"
            else:
                score = 0.0
                label = "neutral"

            confidence = min(abs(negative_score - positive_score) / 2.0 + 0.5, 1.0)

            span.end(output_data={"score": score, "label": label, "confidence": confidence})

            return SentimentResult(score=score, label=label, confidence=confidence, provider="keyword")

    def _get_intensity(self, text: str, keyword: str) -> float:
        """Get intensity modifier for a keyword"""
        intensity = 1.0
        for modifier, multiplier in self.intensity_modifiers.items():
            if modifier in text:
                intensity = max(intensity, multiplier)
        return intensity


class SentimentAnalysisService:
    """Unified sentiment analysis service with provider fallback"""

    def __init__(self):
        logger.info("Initializing Sentiment Analysis Service")

        self.analyzers: list[SentimentAnalyzer] = []

        if SENTIMENT_USE_OPENAI and OPENAI_API_KEY:
            self.analyzers.append(OpenAISentimentAnalyzer())
            logger.info("OpenAI sentiment analyzer added")
        elif SENTIMENT_API_URL and SENTIMENT_API_KEY:
            self.analyzers.append(ExternalAPISentimentAnalyzer())
            logger.info("External API sentiment analyzer added")
        else:
            logger.info("No external sentiment API configured, using keyword-based fallback")

        self.analyzers.append(KeywordBasedSentimentAnalyzer())
        logger.info(f"Sentiment Analysis Service initialized with {len(self.analyzers)} providers")

    async def analyze(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of the given text

        Args:
            text: Input text to analyze

        Returns:
            SentimentResult with score, label, and confidence
        """
        if not self.analyzers:
            return SentimentResult(score=0.0, label="neutral", confidence=0.0, provider="none")

        for analyzer in self.analyzers:
            try:
                result = await analyzer.analyze(text)
                if result.confidence > 0:
                    logger.debug(f"Sentiment analysis completed: {result}")
                    return result
            except Exception as e:
                logger.warning(f"Sentiment analyzer {type(analyzer).__name__} failed: {e}")
                continue

        logger.warning("All sentiment analyzers failed, returning neutral")
        return SentimentResult(score=0.0, label="neutral", confidence=0.0, provider="fallback")

    async def close(self):
        """Close any HTTP clients"""
        for analyzer in self.analyzers:
            if isinstance(analyzer, ExternalAPISentimentAnalyzer) and analyzer.http_client:
                await analyzer.http_client.aclose()


sentiment_service = SentimentAnalysisService()


async def analyze_sentiment(text: str) -> SentimentResult:
    """
    Convenience function to analyze sentiment

    Args:
        text: Input text to analyze

    Returns:
        SentimentResult with score (-1 to 1), label, and confidence
    """
    return await sentiment_service.analyze(text)


__all__ = [
    "SentimentResult",
    "SentimentAnalyzer",
    "SentimentAnalysisService",
    "analyze_sentiment",
]