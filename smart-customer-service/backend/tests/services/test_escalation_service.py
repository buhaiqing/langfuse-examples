"""升级管理服务测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from backend.services.escalation_service import EscalationService, EscalationRequest


class TestEscalationService:
    """升级管理服务测试"""

    @pytest.fixture
    def escalation_service(self):
        """创建升级服务实例"""
        return EscalationService()

    def test_init(self, escalation_service):
        """测试初始化"""
        assert escalation_service.llm is not None
        assert escalation_service.sentiment_prompt is not None

    def test_calculate_priority_level_critical(self, escalation_service):
        """测试 critical 优先级计算"""
        level = escalation_service._calculate_priority_level(85)
        assert level == "critical"

        level = escalation_service._calculate_priority_level(80)
        assert level == "critical"

    def test_calculate_priority_level_high(self, escalation_service):
        """测试 high 优先级计算"""
        level = escalation_service._calculate_priority_level(70)
        assert level == "high"

        level = escalation_service._calculate_priority_level(60)
        assert level == "high"

    def test_calculate_priority_level_medium(self, escalation_service):
        """测试 medium 优先级计算"""
        level = escalation_service._calculate_priority_level(50)
        assert level == "medium"

        level = escalation_service._calculate_priority_level(40)
        assert level == "medium"

    def test_calculate_priority_level_low(self, escalation_service):
        """测试 low 优先级计算"""
        level = escalation_service._calculate_priority_level(30)
        assert level == "low"

        level = escalation_service._calculate_priority_level(0)
        assert level == "low"


class TestEscalationTriggers:
    """升级触发条件测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return EscalationService()

    @pytest.mark.asyncio
    async def test_escalation_low_confidence(self, service):
        """测试低置信度触发升级"""
        with patch.object(service, "analyze_sentiment", new_callable=AsyncMock) as mock_sentiment:
            mock_sentiment.return_value = MagicMock(score=0, reasoning="neutral")

            needs_escalation = await service.check_escalation(
                session_id="sess_123",
                user_id="user_456",
                intent_confidence=0.3,  # < 0.5
                user_message="问题",
                failure_count=0,
                is_vip=False,
            )

            assert needs_escalation is True

    @pytest.mark.asyncio
    async def test_escalation_negative_sentiment(self, service):
        """测试负面情绪触发升级"""
        with patch.object(service, "analyze_sentiment", new_callable=AsyncMock) as mock_sentiment:
            mock_sentiment.return_value = MagicMock(score=-0.8, reasoning="very negative")

            needs_escalation = await service.check_escalation(
                session_id="sess_123",
                user_id="user_456",
                intent_confidence=0.9,
                user_message="我要投诉你们！",
                failure_count=0,
                is_vip=False,
            )

            assert needs_escalation is True

    @pytest.mark.asyncio
    async def test_escalation_vip_customer(self, service):
        """测试 VIP 客户触发升级"""
        with patch.object(service, "analyze_sentiment", new_callable=AsyncMock) as mock_sentiment:
            mock_sentiment.return_value = MagicMock(score=0, reasoning="neutral")

            needs_escalation = await service.check_escalation(
                session_id="sess_123",
                user_id="vip_user",
                intent_confidence=0.6,
                user_message="问题",
                failure_count=0,
                is_vip=True,
            )

            assert needs_escalation is True

    @pytest.mark.asyncio
    async def test_escalation_consecutive_failures(self, service):
        """测试连续失败触发升级"""
        with patch.object(service, "analyze_sentiment", new_callable=AsyncMock) as mock_sentiment:
            mock_sentiment.return_value = MagicMock(score=0, reasoning="neutral")

            needs_escalation = await service.check_escalation(
                session_id="sess_123",
                user_id="user_456",
                intent_confidence=0.7,
                user_message="问题",
                failure_count=5,  # >= 3
                is_vip=False,
            )

            assert needs_escalation is True

    @pytest.mark.asyncio
    async def test_escalation_sensitive_keywords(self, service):
        """测试敏感关键词触发升级"""
        with patch.object(service, "analyze_sentiment", new_callable=AsyncMock) as mock_sentiment:
            mock_sentiment.return_value = MagicMock(score=0, reasoning="neutral")

            needs_escalation = await service.check_escalation(
                session_id="sess_123",
                user_id="user_456",
                intent_confidence=0.8,
                user_message="我要去 315 投诉你们！",
                failure_count=0,
                is_vip=False,
            )

            assert needs_escalation is True

    @pytest.mark.asyncio
    async def test_no_escalation_normal_case(self, service):
        """测试不需要升级的正常情况"""
        with patch.object(service, "analyze_sentiment", new_callable=AsyncMock) as mock_sentiment:
            mock_sentiment.return_value = MagicMock(score=0.5, reasoning="positive")

            needs_escalation = await service.check_escalation(
                session_id="sess_123",
                user_id="user_456",
                intent_confidence=0.9,
                user_message="谢谢帮助",
                failure_count=0,
                is_vip=False,
            )

            assert needs_escalation is False


class TestSentimentAnalysis:
    """情绪分析测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return EscalationService()

    @pytest.mark.asyncio
    async def test_analyze_sentiment_negative(self, service):
        """测试负面情绪分析"""
        with patch.object(service.llm, "ainvoke", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = MagicMock(content='{"score": -0.8, "reasoning": "用户很生气"}')

            result = await service.analyze_sentiment("我要投诉你们！")

            assert result.score < 0
            assert result.reasoning is not None

    @pytest.mark.asyncio
    async def test_analyze_sentiment_positive(self, service):
        """测试正面情绪分析"""
        with patch.object(service.llm, "ainvoke", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = MagicMock(content='{"score": 0.7, "reasoning": "用户很满意"}')

            result = await service.analyze_sentiment("非常感谢你的帮助！")

            assert result.score > 0

    @pytest.mark.asyncio
    async def test_analyze_sentiment_parse_error(self, service):
        """测试解析错误处理"""
        with patch.object(service.llm, "ainvoke", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = MagicMock(content="invalid json")

            result = await service.analyze_sentiment("测试")

            assert result.score == 0  # 默认值


class TestEscalationRequest:
    """升级请求模型测试"""

    def test_create_escalation_request(self):
        """测试创建升级请求"""
        request = EscalationRequest(
            session_id="sess_123",
            user_id="user_456",
            priority_score=85.5,
            priority_level="critical",
            trigger_reasons=["negative_sentiment", "vip_customer"],
            context={"sentiment_score": -0.8},
        )

        assert request.session_id == "sess_123"
        assert request.priority_score == 85.5
        assert request.priority_level == "critical"
        assert len(request.trigger_reasons) == 2
        assert "sentiment_score" in request.context

    def test_escalation_request_defaults(self):
        """测试升级请求默认值"""
        request = EscalationRequest(
            session_id="sess_123",
            user_id="user_456",
            priority_score=50,
            priority_level="medium",
            trigger_reasons=["low_confidence"],
        )

        assert request.context == {}
        assert request.created_at is not None
        assert isinstance(request.created_at, str)
