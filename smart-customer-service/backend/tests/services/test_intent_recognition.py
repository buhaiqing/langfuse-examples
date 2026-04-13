"""意图识别服务测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.services.intent_recognition import (
    IntentRecognitionService,
    IntentRecognitionResult,
    INTENT_DEFINITIONS,
)


class TestIntentRecognitionService:
    """意图识别服务测试"""

    @pytest.fixture
    def service(self):
        """创建意图识别服务实例"""
        return IntentRecognitionService()

    def test_preprocess_text(self, service):
        """测试文本预处理"""
        # 测试空白字符处理
        assert service.preprocess_text("  hello  world  ") == "hello world"

        # 测试长度截断
        long_text = "a" * 600
        assert len(service.preprocess_text(long_text)) == 500

        # 测试正常文本
        assert service.preprocess_text("你好") == "你好"

    def test_format_context_with_none(self, service):
        """测试上下文格式化为 None 时"""
        result = service._format_context(None)
        assert result == "无上下文信息"

    def test_format_context_with_data(self, service):
        """测试上下文格式化有数据时"""
        context = {
            "previous_messages": [{"role": "user", "content": "test"}],
            "collected_slots": {"error_code": "403"},
        }
        result = service._format_context(context)
        assert "历史消息" in result
        assert "已收集槽位" in result

    def test_format_intent_definitions(self, service):
        """测试意图定义格式化"""
        result = service._format_intent_definitions()
        assert "api_error_troubleshooting" in result
        assert "account_login_issue" in result

    @pytest.mark.asyncio
    async def test_recognize_api_error(self, service):
        """测试 API 错误排查意图识别"""
        # Mock LLM 响应
        with patch.object(service, "_recognize_intent", new_callable=AsyncMock) as mock_intent:
            with patch.object(
                service, "_recognize_entities", new_callable=AsyncMock
            ) as mock_entities:
                mock_intent.return_value = MagicMock(
                    intent="api_error_troubleshooting",
                    confidence=0.95,
                    slots={"error_code": "403"},
                    reasoning="用户提到 API 返回 403 错误",
                )
                mock_entities.return_value = [{"entity_type": "error_code", "value": "403"}]

                result = await service.recognize("我的 API 返回 403 错误", {})

                assert isinstance(result, IntentRecognitionResult)
                assert result.intent == "api_error_troubleshooting"
                assert result.confidence == 0.95
                assert result.slots == {"error_code": "403"}

    @pytest.mark.asyncio
    async def test_recognize_account_issue(self, service):
        """测试账户登录问题意图识别"""
        with patch.object(service, "_recognize_intent", new_callable=AsyncMock) as mock_intent:
            with patch.object(
                service, "_recognize_entities", new_callable=AsyncMock
            ) as mock_entities:
                mock_intent.return_value = MagicMock(
                    intent="account_login_issue",
                    confidence=0.88,
                    slots={"account": "user@example.com"},
                    reasoning="用户提到登录问题",
                )
                mock_entities.return_value = [{"entity_type": "email", "value": "user@example.com"}]

                result = await service.recognize("我登录不了账户", {})

                assert result.intent == "account_login_issue"
                assert any(e["type"] == "email" for e in result.entities)

    def test_calculate_confidence(self, service):
        """测试综合置信度计算"""
        # 测试高置信度
        confidence = service.calculate_confidence(0.9, 0.8, 0.7)
        assert 0.0 <= confidence <= 1.0

        # 测试低置信度
        confidence = service.calculate_confidence(0.3, 0.2, 0.1)
        assert confidence < 0.5

        # 测试边界值
        confidence = service.calculate_confidence(1.0, 1.0, 1.0)
        assert confidence == 1.0

        confidence = service.calculate_confidence(0.0, 0.0, 0.0)
        assert confidence == 0.0


class TestIntentDefinitions:
    """意图定义测试"""

    def test_all_intents_have_required_fields(self):
        """测试所有意图都有必需字段"""
        required_fields = ["description", "required_slots", "optional_slots", "example"]

        for intent_type, info in INTENT_DEFINITIONS.items():
            for field in required_fields:
                assert field in info, f"Intent {intent_type} missing {field}"

    def test_intent_types_are_valid(self):
        """测试意图类型命名规范"""
        for intent_type in INTENT_DEFINITIONS.keys():
            # 意图类型应该使用小写字母和下划线
            assert intent_type.islower() or "_" in intent_type
            assert len(intent_type) > 0
            assert not intent_type.startswith("_")
            assert not intent_type.endswith("_")

    def test_required_slots_are_lists(self):
        """测试必需槽位是列表"""
        for intent_type, info in INTENT_DEFINITIONS.items():
            assert isinstance(info["required_slots"], list)
            assert isinstance(info["optional_slots"], list)
