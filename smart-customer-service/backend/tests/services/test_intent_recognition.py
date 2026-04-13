"""意图识别服务测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.services.intent_recognition import (
    IntentRecognitionService,
    IntentRecognitionResult,
    Entity,
    INTENT_DEFINITIONS,
    intent_service,
)


class TestIntentRecognitionService:
    """意图识别服务测试"""

    @pytest.fixture
    def intent_service_instance(self):
        """创建意图识别服务实例"""
        with patch('backend.services.intent_recognition.ChatOpenAI'):
            service = IntentRecognitionService()
            return service

    def test_init(self, intent_service_instance):
        """测试初始化"""
        service = intent_service_instance
        assert service.llm is not None
        assert service.intent_prompt is not None
        assert service.entity_prompt is not None
        assert service.intent_parser is not None
        assert service.entity_parser is not None

    def test_preprocess_text(self, intent_service_instance):
        """测试文本预处理"""
        service = intent_service_instance
        
        # 测试空格规范化
        assert service.preprocess_text("  多个   空格  ") == "多个 空格"
        
        # 测试长度截断
        long_text = "x" * 1000
        result = service.preprocess_text(long_text)
        assert len(result) == 500
        
        # 测试空白字符去除
        assert service.preprocess_text("  trim  ") == "trim"

    def test_format_intent_definitions(self, intent_service_instance):
        """测试意图定义格式化"""
        service = intent_service_instance
        
        result = service._format_intent_definitions()
        
        # 验证包含所有意图类型
        for intent_type in INTENT_DEFINITIONS.keys():
            assert intent_type in result
            
        # 验证包含描述和示例
        assert "API 错误排查" in result
        assert "示例" in result

    def test_format_context(self, intent_service_instance):
        """测试上下文格式化"""
        service = intent_service_instance
        
        # 测试空上下文
        assert service._format_context(None) == "无上下文信息"
        assert service._format_context({}) == "无额外上下文"
        
        # 测试有历史消息
        context = {"previous_messages": ["msg1", "msg2"]}
        result = service._format_context(context)
        assert "历史消息" in result
        assert "2 条" in result
        
        # 测试有已收集槽位
        context = {"collected_slots": {"error_code": "403"}}
        result = service._format_context(context)
        assert "已收集槽位" in result
        assert "error_code" in result

    @pytest.mark.asyncio
    async def test_recognize_intent(self, intent_service_instance):
        """测试意图识别"""
        service = intent_service_instance
        
        with patch.object(service, '_recognize_intent', new_callable=AsyncMock) as mock_recognize, \
             patch.object(service, '_recognize_entities', new_callable=AsyncMock) as mock_entities:
            
            mock_recognize.return_value = MagicMock(
                intent="api_error_troubleshooting",
                confidence=0.92,
                slots={"error_code": "403"},
                reasoning="用户提到 API 错误"
            )
            mock_entities.return_value = [
                {"entity_type": "error_code", "value": "403"}
            ]
            
            result = await service.recognize("我的 API 返回 403 错误")
            
            assert isinstance(result, IntentRecognitionResult)
            assert result.intent == "api_error_troubleshooting"
            assert result.confidence == 0.92
            assert result.slots["error_code"] == "403"
            assert len(result.entities) == 1
            assert result.entities[0]["type"] == "error_code"

    @pytest.mark.asyncio
    async def test_recognize_with_context(self, intent_service_instance):
        """测试带上下文的意图识别"""
        service = intent_service_instance
        
        context = {
            "previous_messages": ["你好", "有问题"],
            "collected_slots": {"account": "user123"}
        }
        
        with patch.object(service, '_recognize_intent', new_callable=AsyncMock) as mock_recognize, \
             patch.object(service, '_recognize_entities', new_callable=AsyncMock):
            
            mock_recognize.return_value = MagicMock(
                intent="account_login_issue",
                confidence=0.85,
                slots={},
                reasoning=""
            )
            
            await service.recognize("我登录不了", context=context)
            
            # 验证上下文被传递
            call_args = mock_recognize.call_args
            assert "无上下文信息" not in str(call_args)


class TestIntentDefinitions:
    """意图定义测试"""

    def test_all_intents_have_required_fields(self):
        """测试所有意图都有必需字段"""
        required_fields = ["description", "required_slots", "optional_slots", "example"]
        
        for intent_type, info in INTENT_DEFINITIONS.items():
            for field in required_fields:
                assert field in info, f"意图 {intent_type} 缺少字段 {field}"

    def test_intent_types(self):
        """测试意图类型完整性"""
        expected_intents = [
            "api_error_troubleshooting",
            "account_login_issue",
            "billing_payment_question",
            "feature_usage_guidance",
            "ticket_status_query",
            "product_information",
            "technical_documentation",
            "general_inquiry",
            "human_agent_request",
        ]
        
        for intent in expected_intents:
            assert intent in INTENT_DEFINITIONS, f"缺少意图 {intent}"


class TestEntityRecognition:
    """实体识别测试"""

    @pytest.fixture
    def intent_service_instance(self):
        with patch('backend.services.intent_recognition.ChatOpenAI'):
            return IntentRecognitionService()

    @pytest.mark.asyncio
    async def test_recognize_entities(self, intent_service_instance):
        """测试实体识别"""
        service = intent_service_instance
        
        with patch.object(service.llm, 'ainvoke', new_callable=AsyncMock) as mock_llm:
            mock_response = MagicMock()
            mock_response.content = '{"entities": [{"entity_type": "error_code", "value": "500"}]}'
            mock_llm.return_value = mock_response
            
            # Mock parser
            with patch.object(service.entity_parser, 'ainvoke', new_callable=AsyncMock) as mock_parser:
                mock_parser.return_value = {"entities": [{"entity_type": "error_code", "value": "500"}]}
                
                entities = await service._recognize_entities("服务器返回 500 错误")
                
                assert len(entities) == 1
                assert entities[0]["entity_type"] == "error_code"
                assert entities[0]["value"] == "500"

    @pytest.mark.asyncio
    async def test_recognize_entities_multiple(self, intent_service_instance):
        """测试多实体识别"""
        service = intent_service_instance
        
        with patch.object(service.entity_parser, 'ainvoke', new_callable=AsyncMock) as mock_parser:
            mock_parser.return_value = {
                "entities": [
                    {"entity_type": "email", "value": "user@example.com"},
                    {"entity_type": "ticket_id", "value": "TKT-12345"},
                ]
            }
            
            entities = await service._recognize_entities("user@example.com 的工单 TKT-12345")
            
            assert len(entities) == 2
            entity_types = [e["entity_type"] for e in entities]
            assert "email" in entity_types
            assert "ticket_id" in entity_types

    @pytest.mark.asyncio
    async def test_recognize_entities_empty(self, intent_service_instance):
        """测试无实体情况"""
        service = intent_service_instance
        
        with patch.object(service.entity_parser, 'ainvoke', new_callable=AsyncMock) as mock_parser:
            mock_parser.return_value = {"entities": []}
            
            entities = await service._recognize_entities("你好")
            
            assert entities == []


class TestSlotExtraction:
    """槽位提取测试"""

    @pytest.fixture
    def intent_service_instance(self):
        with patch('backend.services.intent_recognition.ChatOpenAI'):
            return IntentRecognitionService()

    @pytest.mark.asyncio
    async def test_extract_slots_api_error(self, intent_service_instance):
        """测试 API 错误场景的槽位提取"""
        service = intent_service_instance
        
        with patch.object(service, '_recognize_entities', new_callable=AsyncMock) as mock_entities:
            mock_entities.return_value = [
                {"entity_type": "error_code", "value": "403"},
                {"entity_type": "api_endpoint", "value": "/api/v1/users"},
            ]
            
            slots = await service.extract_slots(
                "访问 /api/v1/users 返回 403",
                "api_error_troubleshooting"
            )
            
            assert slots["error_code"] == "403"
            assert slots["api_endpoint"] == "/api/v1/users"

    @pytest.mark.asyncio
    async def test_extract_slots_ticket_query(self, intent_service_instance):
        """测试工单查询场景的槽位提取"""
        service = intent_service_instance
        
        with patch.object(service, '_recognize_entities', new_callable=AsyncMock) as mock_entities:
            mock_entities.return_value = [
                {"entity_type": "ticket_id", "value": "TKT-98765"},
            ]
            
            slots = await service.extract_slots(
                "查询 TKT-98765 的状态",
                "ticket_status_query"
            )
            
            assert slots["ticket_id"] == "TKT-98765"

    @pytest.mark.asyncio
    async def test_extract_slots_no_match(self, intent_service_instance):
        """测试不匹配的槽位提取"""
        service = intent_service_instance
        
        with patch.object(service, '_recognize_entities', new_callable=AsyncMock) as mock_entities:
            mock_entities.return_value = [
                {"entity_type": "error_code", "value": "500"},
            ]
            
            # 账户登录问题不应该提取 error_code
            slots = await service.extract_slots(
                "错误 500",
                "account_login_issue"
            )
            
            assert "error_code" not in slots


class TestConfidenceCalculation:
    """置信度计算测试"""

    @pytest.fixture
    def intent_service_instance(self):
        with patch('backend.services.intent_recognition.ChatOpenAI'):
            return IntentRecognitionService()

    def test_calculate_confidence_high(self, intent_service_instance):
        """测试高置信度计算"""
        service = intent_service_instance
        
        confidence = service.calculate_confidence(
            llm_confidence=0.95,
            slots_completeness=1.0,
            context_match=0.9
        )
        
        assert confidence > 0.9
        assert confidence <= 1.0

    def test_calculate_confidence_low(self, intent_service_instance):
        """测试低置信度计算"""
        service = intent_service_instance
        
        confidence = service.calculate_confidence(
            llm_confidence=0.3,
            slots_completeness=0.0,
            context_match=0.2
        )
        
        assert confidence < 0.5
        assert confidence >= 0.0

    def test_calculate_confidence_clamping(self, intent_service_instance):
        """测试置信度边界限制"""
        service = intent_service_instance
        
        # 测试上限
        high_conf = service.calculate_confidence(2.0, 2.0, 2.0)
        assert high_conf == 1.0
        
        # 测试下限
        low_conf = service.calculate_confidence(-1.0, -1.0, -1.0)
        assert low_conf == 0.0


class TestIntentRecognitionEdgeCases:
    """意图识别边界情况测试"""

    @pytest.fixture
    def intent_service_instance(self):
        with patch('backend.services.intent_recognition.ChatOpenAI'):
            return IntentRecognitionService()

    @pytest.mark.asyncio
    async def test_recognize_empty_message(self, intent_service_instance):
        """测试空消息识别"""
        service = intent_service_instance
        
        with patch.object(service, '_recognize_intent', new_callable=AsyncMock) as mock_recognize, \
             patch.object(service, '_recognize_entities', new_callable=AsyncMock):
            
            mock_recognize.return_value = MagicMock(
                intent="general_inquiry",
                confidence=0.5,
                slots={},
                reasoning=""
            )
            
            result = await service.recognize("")
            
            assert result.intent == "general_inquiry"

    @pytest.mark.asyncio
    async def test_recognize_very_long_message(self, intent_service_instance):
        """测试超长消息识别"""
        service = intent_service_instance
        
        long_message = "问题" * 1000
        
        with patch.object(service, '_recognize_intent', new_callable=AsyncMock) as mock_recognize, \
             patch.object(service, '_recognize_entities', new_callable=AsyncMock):
            
            mock_recognize.return_value = MagicMock(
                intent="general_inquiry",
                confidence=0.6,
                slots={},
                reasoning=""
            )
            
            result = await service.recognize(long_message)
            
            assert len(result.raw_response) <= 500  # 预处理应该截断

    @pytest.mark.asyncio
    async def test_recognize_special_characters(self, intent_service_instance):
        """测试特殊字符消息识别"""
        service = intent_service_instance
        
        special_message = "API <script>alert('xss')</script> 错误！"
        
        with patch.object(service, '_recognize_intent', new_callable=AsyncMock) as mock_recognize, \
             patch.object(service, '_recognize_entities', new_callable=AsyncMock):
            
            mock_recognize.return_value = MagicMock(
                intent="api_error_troubleshooting",
                confidence=0.8,
                slots={},
                reasoning=""
            )
            
            result = await service.recognize(special_message)
            
            assert result.intent == "api_error_troubleshooting"


class TestEntityModel:
    """实体模型测试"""

    def test_entity_creation(self):
        """测试实体创建"""
        entity = Entity(
            entity_type="email",
            value="test@example.com",
            original_text="请联系 test@example.com"
        )
        
        assert entity.entity_type == "email"
        assert entity.value == "test@example.com"
        assert entity.original_text == "请联系 test@example.com"


class TestIntentRecognitionIntegration:
    """意图识别集成测试"""

    @pytest.mark.asyncio
    async def test_full_intent_recognition_pipeline(self):
        """测试完整意图识别流程"""
        with patch('backend.services.intent_recognition.ChatOpenAI') as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock()
            mock_llm_class.return_value = mock_llm
            
            service = IntentRecognitionService()
            
            # Mock intent recognition
            with patch.object(service.intent_parser, 'ainvoke', new_callable=AsyncMock) as mock_intent_parser, \
                 patch.object(service.entity_parser, 'ainvoke', new_callable=AsyncMock) as mock_entity_parser:
                
                mock_intent_parser.return_value = {
                    "intent": "api_error_troubleshooting",
                    "confidence": 0.95,
                    "slots": {"error_code": "403"},
                    "reasoning": "用户明确提到 API 403 错误",
                }
                mock_entity_parser.return_value = {
                    "entities": [
                        {"entity_type": "error_code", "value": "403"}
                    ]
                }
                
                result = await service.recognize("我的 API 返回 403 错误，怎么办？")
                
                assert result.intent == "api_error_troubleshooting"
                assert result.confidence == 0.95
                assert result.slots["error_code"] == "403"
                assert len(result.entities) == 1
                assert result.entities[0]["type"] == "error_code"
                assert result.entities[0]["value"] == "403"
