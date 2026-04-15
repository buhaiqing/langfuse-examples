"""Langfuse 可观测性客户端"""

from langfuse import Langfuse, observe

# langfuse_context 在 Langfuse 4.x 中已不再需要
from typing import Optional, Dict, Any, List
from contextvars import ContextVar
import uuid
from utils.masking import mask_dict

from core.config import settings


# ==================== Langfuse 客户端初始化 ====================
class LangfuseClient:
    """Langfuse 客户端封装"""

    def __init__(self):
        self.client: Optional[Langfuse] = None
        self._mock_enabled = False

        # 始终先检查测试环境或测试运行标志
        import os

        env = os.environ.get("ENVIRONMENT", "")
        is_testing = "testing" in env.lower() or "PYTEST_CURRENT_TEST" in os.environ

        if is_testing:
            self._mock_enabled = True
            self._setup_mock_client()
            return

        # 生产环境才初始化真实的 Langfuse 客户端
        if (
            settings.langfuse_enabled
            and settings.langfuse_public_key
            and settings.langfuse_secret_key
        ):
            try:
                self.client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host,
                )
            except Exception:
                self._setup_mock_client()
        elif (
            settings.langfuse_enabled
            and settings.langfuse_public_key
            and settings.langfuse_secret_key
        ):
            try:
                self.client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host,
                )
            except Exception:
                # 如果初始化失败，使用 mock
                self._setup_mock_client()

    def _setup_mock_client(self):
        """设置 mock Langfuse 客户端用于测试"""
        from unittest.mock import MagicMock

        self.client = MagicMock()
        self.client.trace = MagicMock(return_value=MagicMock(id="mock-trace-id"))
        self.client.start_as_current_span = MagicMock()
        self.client.start_as_current_observation = MagicMock()
        self.client.score_current_span = MagicMock()
        self.client.score_current_trace = MagicMock()
        self.client.flush = MagicMock()
        self.client.shutdown = MagicMock()

    def is_enabled(self) -> bool:
        return self.client is not None

    def trace(self, **kwargs):
        """委托到内部 Langfuse client"""
        if not self.client:
            return None
        return self.client.trace(**kwargs)

    def flush(self):
        """刷新追踪数据"""
        if self.client:
            self.client.flush()

    def shutdown(self):
        """关闭客户端"""
        if self.client:
            self.client.shutdown()


langfuse_client = LangfuseClient()


# ==================== 追踪上下文 ====================
_trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_span_stack_var: ContextVar[List[Any]] = ContextVar("span_stack", default=[])


def get_current_trace_id() -> Optional[str]:
    return _trace_id_var.get()


def get_current_span() -> Optional[Any]:
    stack = _span_stack_var.get()
    return stack[-1] if stack else None


# ==================== 追踪装饰器 ====================
def trace_customer_service(
    name: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
):
    """
    智能客服会话追踪装饰器

    usage:
        @trace_customer_service(
            name="api_error_troubleshooting",
            session_id="sess_123",
            user_id="user_456"
        )
        async def handle_message(...):
            ...
    """
    return observe(name=name, session_id=session_id, user_id=user_id, metadata=metadata or {})


# ==================== Span 创建工具 ====================
class SpanManager:
    """Span 管理器"""

    @staticmethod
    def create_span(name: str, **kwargs):
        """创建 Span"""
        if not langfuse_client.is_enabled():
            return DummySpan()

        trace_id = get_current_trace_id()
        if not trace_id:
            return DummySpan()

        trace = langfuse_client.client.trace(id=trace_id)
        span = trace.span(name=name, **kwargs)

        stack = _span_stack_var.get()
        stack.append(span)
        _span_stack_var.set(stack)

        return span

    @staticmethod
    def end_span(span):
        """结束 Span"""
        if hasattr(span, "end") and callable(span.end):
            span.end()

        stack = _span_stack_var.get()
        if span in stack:
            stack.remove(span)
            _span_stack_var.set(stack)

    @staticmethod
    def score_current_span(name: str, value: float, comment: Optional[str] = None):
        """对当前 Span 评分"""
        span = get_current_span()
        if span and hasattr(span, "score"):
            span.score(name=name, value=value, comment=comment)


class DummySpan:
    """空 Span(用于 Langfuse 禁用时)"""

    def end(self, **kwargs):
        pass

    def score(self, **kwargs):
        pass


# ==================== 评分体系 ====================
class Scores:
    """预定义评分项"""

    INTENT_CONFIDENCE = "intent_confidence"
    RETRIEVAL_RELEVANCE = "retrieval_relevance"
    TOOL_SUCCESS_RATE = "tool_success_rate"
    ISSUE_RESOLVED = "issue_resolved"
    USER_SATISFACTION = "user_satisfaction"
    RESPONSE_LATENCY_MS = "response_latency_ms"
    DIALOGUE_COHERENCE = "dialogue_coherence"
    SLOT_COMPLETION_RATE = "slot_completion_rate"
    ESCALATION_REQUIRED = "escalation_required"
    FIRST_CONTACT_RESOLUTION = "first_contact_resolution"
    FAILURE_TYPE = "failure_type"


def score_trace(
    score_name: str, value: float, comment: Optional[str] = None, trace_id: Optional[str] = None
):
    """
    对 Trace 评分
    """
    if not langfuse_client.is_enabled():
        return

    if not trace_id:
        trace_id = get_current_trace_id()

    if not trace_id:
        return

    trace = langfuse_client.client.trace(id=trace_id)
    trace.score(name=score_name, value=value, comment=comment)


# ==================== 数据脱敏集成 ====================
def create_trace_with_masking(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
    input_data: Optional[Any] = None,
    **kwargs,
):
    """
    创建脱敏后的 Trace
    """
    if not langfuse_client.is_enabled():
        return None

    masked_metadata = mask_dict(metadata or {})
    masked_input = input_data
    if input_data and isinstance(input_data, dict):
        masked_input = mask_dict(input_data)
    if input_data and isinstance(input_data, str):
        from utils.masking import mask_text

        masked_input = mask_text(input_data)

    trace = langfuse_client.client.trace(
        user_id=user_id.split("@")[0][:3] + "***" if user_id else None,
        session_id=session_id,
        metadata=masked_metadata,
        input=masked_input,
        **kwargs,
    )

    _trace_id_var.set(trace.id)

    return trace


# ==================== 事件标记 ====================
def log_event(name: str, metadata: Optional[Dict] = None, level: str = "INFO"):
    """
    记录事件
    """
    if not langfuse_client.is_enabled():
        return

    trace_id = get_current_trace_id()
    if not trace_id:
        return

    trace = langfuse_client.client.trace(id=trace_id)
    trace.event(name=name, metadata=mask_dict(metadata) if metadata else None, level=level)


# ==================== 便捷函数 ====================
def create_span(name: str, **kwargs):
    """创建 Span 便捷函数"""
    return SpanManager.create_span(name, **kwargs)
