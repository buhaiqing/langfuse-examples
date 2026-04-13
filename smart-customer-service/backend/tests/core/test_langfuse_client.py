"""Langfuse 可观测性测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.core.langfuse_client import (
    LangfuseClient,
    langfuse_client,
    SpanManager,
    DummySpan,
    Scores,
    score_trace,
    create_trace_with_masking,
    log_event,
    get_current_trace_id,
    get_current_span,
)


class TestLangfuseClient:
    """Langfuse 客户端测试"""

    @pytest.fixture
    def client(self):
        """创建 Langfuse 客户端实例"""
        return LangfuseClient()

    def test_init_disabled(self, client):
        """测试未配置时禁用"""
        with patch('backend.core.langfuse_client.settings') as mock_settings:
            mock_settings.langfuse_enabled = False
            mock_settings.langfuse_public_key = ""
            mock_settings.langfuse_secret_key = ""
            
            client_test = LangfuseClient()
            
            assert client_test client is None
            assert client_test.is_enabled() is False

    def test_init_enabled(self, client):
        """测试配置后启用"""
        with patch('backend.core.langfuse_client.Langfuse') as mock_langfuse:
            with patch('backend.core.langfuse_client.settings') as mock_settings:
                mock_settings.langfuse_enabled = True
                mock_settings.langfuse_public_key = "pk-test"
                mock_settings.langfuse_secret_key = "sk-test"
                
                client_test = LangfuseClient()
                
                assert client_test.client is not None
                assert client_test.is_enabled() is True
                mock_langfuse.assert_called_once()

    def test_flush_when_disabled(self, client):
        """测试禁用时刷新"""
        client.client = None
        
        # 不应该抛出异常
        client.flush()

    def test_flush_when_enabled(self, client):
        """测试启用时刷新"""
        client.client = MagicMock()
        client.client.flush = MagicMock()
        
        client.flush()
        
        client.client.flush.assert_called_once()

    def test_shutdown_when_disabled(self, client):
        """测试禁用时关闭"""
        client.client = None
        
        # 不应该抛出异常
        client.shutdown()

    def test_shutdown_when_enabled(self, client):
        """测试启用时关闭"""
        client.client = MagicMock()
        client.client.shutdown = MagicMock()
        
        client.shutdown()
        
        client.client.shutdown.assert_called_once()


class TestSpanManager:
    """Span 管理器测试"""

    def test_create_span_when_disabled(self):
        """测试禁用时创建 Span"""
        with patch('backend.core.langfuse_client.langfuse_client') as mock_client:
            mock_client.is_enabled.return_value = False
            
            span = SpanManager.create_span("test_span")
            
            assert isinstance(span, DummySpan)

    def test_create_span_when_no_trace(self):
        """测试无 Trace 时创建 Span"""
        with patch('backend.core.langfuse_client.langfuse_client') as mock_client:
            mock_client.is_enabled.return_value = True
            mock_client.client = MagicMock()
            
            with patch('backend.core.langfuse_client.get_current_trace_id') as mock_trace_id:
                mock_trace_id.return_value = None
                
                span = SpanManager.create_span("test_span")
                
                assert isinstance(span, DummySpan)

    def test_create_span_success(self):
        """测试成功创建 Span"""
        mock_span = MagicMock()
        mock_trace = MagicMock()
        mock_trace.span = MagicMock(return_value=mock_span)
        
        with patch('backend.core.langfuse_client.langfuse_client') as mock_client:
            mock_client.is_enabled.return_value = True
            mock_client.client = MagicMock()
            mock_client.client.trace = MagicMock(return_value=mock_trace)
            
            with patch('backend.core.langfuse_client.get_current_trace_id') as mock_trace_id:
                mock_trace_id.return_value = "trace_123"
                
                span = SpanManager.create_span("test_span")
                
                assert span == mock_span
                mock_trace.span.assert_called_once_with(name="test_span")

    def test_end_span(self):
        """测试结束 Span"""
        mock_span = MagicMock()
        
        SpanManager.end_span(mock_span)
        
        mock_span.end.assert_called_once()

    def test_score_current_span(self):
        """测试 Span 评分"""
        mock_span = MagicMock()
        
        with patch('backend.core.langfuse_client.get_current_span') as mock_get_span:
            mock_get_span.return_value = mock_span
            
            SpanManager.score_current_span("test_score", 0.9, comment="Good")
            
            mock_span.score.assert_called_once_with(
                name="test_score",
                value=0.9,
                comment="Good"
            )


class TestDummySpan:
    """Dummy Span 测试"""

    def test_end_does_nothing(self):
        """测试 end 方法无操作"""
        span = DummySpan()
        
        # 不应该抛出异常
        span.end(key="value")

    def test_score_does_nothing(self):
        """测试 score 方法无操作"""
        span = DummySpan()
        
        # 不应该抛出异常
        span.score(name="test", value=1.0)


class TestScores:
    """评分常量测试"""

    def test_all_scores_defined(self):
        """测试所有评分项已定义"""
        assert hasattr(Scores, 'INTENT_CONFIDENCE')
        assert hasattr(Scores, 'RETRIEVAL_RELEVANCE')
        assert hasattr(Scores, 'TOOL_SUCCESS_RATE')
        assert hasattr(Scores, 'ISSUE_RESOLVED')
        assert hasattr(Scores, 'USER_SATISFACTION')
        assert hasattr(Scores, 'RESPONSE_LATENCY_MS')
        assert hasattr(Scores, 'DIALOGUE_COHERENCE')
        assert hasattr(Scores, 'SLOT_COMPLETION_RATE')
        assert hasattr(Scores, 'ESCALATION_REQUIRED')
        assert hasattr(Scores, 'FIRST_CONTACT_RESOLUTION')
        assert hasattr(Scores, 'FAILURE_TYPE')


class TestScoreTrace:
    """Trace 评分测试"""

    def test_score_trace_when_disabled(self):
        """测试禁用时评分"""
        with patch('backend.core.langfuse_client.langfuse_client') as mock_client:
            mock_client.is_enabled.return_value = False
            
            # 不应该抛出异常
            score_trace("test_score", 0.9)

    def test_score_trace_when_no_trace_id(self):
        """测试无 Trace ID 时评分"""
        with patch('backend.core.langfuse_client.langfuse_client') as mock_client:
            mock_client.is_enabled.return_value = True
            
            with patch('backend.core.langfuse_client.get_current_trace_id') as mock_trace_id:
                mock_trace_id.return_value = None
                
                # 不应该抛出异常
                score_trace("test_score", 0.9)

    def test_score_trace_success(self):
        """测试成功评分"""
        mock_trace = MagicMock()
        
        with patch('backend.core.langfuse_client.langfuse_client') as mock_client:
            mock_client.is_enabled.return_value = True
            mock_client.client = MagicMock()
            mock_client.client.trace = MagicMock(return_value=mock_trace)
            
            with patch('backend.core.langfuse_client.get_current_trace_id') as mock_trace_id:
                mock_trace_id.return_value = "trace_123"
                
                score_trace("test_score", 0.9, comment="Good")
                
                mock_trace.score.assert_called_once_with(
                    name="test_score",
                    value=0.9,
                    comment="Good"
                )


class TestCreateTraceWithMasking:
    """带脱敏的 Trace 创建测试"""

    def test_create_when_disabled(self):
        """测试禁用时创建"""
        with patch('backend.core.langfuse_client.langfuse_client') as mock_client:
            mock_client.is_enabled.return_value = False
            
            result = create_trace_with_masking(user_id="user_123")
            
            assert result is None

    def test_create_with_user_id_masking(self):
        """测试用户 ID 掩码"""
        mock_trace = MagicMock()
        
        with patch('backend.core.langfuse_client.langfuse_client') as mock_client:
            mock_client.is_enabled.return_value = True
            mock_client.client = MagicMock()
            mock_client.client.trace = MagicMock(return_value=mock_trace)
            
            with patch('backend.core.langfuse_client.mask_dict') as mock_mask_dict:
                mock_mask_dict.return_value = {}
                
                create_trace_with_masking(
                    user_id="user@example.com",
                    metadata={"key": "value"}
                )
                
                mock_client.client.trace.assert_called_once()
                # 验证 user_id 被掩码
                call_args = mock_client.client.trace.call_args
                assert "***" in call_args[1]["user_id"]


class TestLogEvent:
    """事件记录测试"""

    def test_log_event_when_disabled(self):
        """测试禁用时记录事件"""
        with patch('backend.core.langfuse_client.langfuse_client') as mock_client:
            mock_client.is_enabled.return_value = False
            
            # 不应该抛出异常
            log_event("test_event", {"key": "value"})

    def test_log_event_when_no_trace(self):
        """测试无 Trace 时记录事件"""
        with patch('backend.core.langfuse_client.langfuse_client') as mock_client:
            mock_client.is_enabled.return_value = True
            
            with patch('backend.core.langfuse_client.get_current_trace_id') as mock_trace_id:
                mock_trace_id.return_value = None
                
                # 不应该抛出异常
                log_event("test_event")

    def test_log_event_success(self):
        """测试成功记录事件"""
        mock_trace = MagicMock()
        
        with patch('backend.core.langfuse_client.langfuse_client') as mock_client:
            mock_client.is_enabled.return_value = True
            mock_client.client = MagicMock()
            mock_client.client.trace = MagicMock(return_value=mock_trace)
            
            with patch('backend.core.langfuse_client.get_current_trace_id') as mock_trace_id:
                mock_trace_id.return_value = "trace_123"
                with patch('backend.core.langfuse_client.mask_dict') as mock_mask_dict:
                    mock_mask_dict.return_value = {"key": "value"}
                    
                    log_event("test_event", {"key": "value"}, level="INFO")
                    
                    mock_trace.event.assert_called_once_with(
                        name="test_event",
                        metadata={"key": "value"},
                        level="INFO"
                    )


class TestContextFunctions:
    """上下文函数测试"""

    def test_get_current_trace_id(self):
        """测试获取当前 Trace ID"""
        from backend.core.langfuse_client import _trace_id_var
        
        _trace_id_var.set("test_trace_123")
        
        trace_id = get_current_trace_id()
        
        assert trace_id == "test_trace_123"

    def test_get_current_span_empty(self):
        """测试获取当前 Span（空栈）"""
        span = get_current_span()
        
        assert span is None

    def test_get_current_span_with_stack(self):
        """测试获取当前 Span（有栈）"""
        from backend.core.langfuse_client import _span_stack_var
        
        mock_span = MagicMock()
        _span_stack_var.set([mock_span])
        
        span = get_current_span()
        
        assert span == mock_span
