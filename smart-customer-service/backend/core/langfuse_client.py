"""Langfuse 可观测性客户端

提供 Langfuse SDK 封装、追踪上下文管理、Span 创建工具和评分体系。
支持自动检测测试环境并切换为 Mock 模式。
"""

import logging
import os
from contextvars import ContextVar
from typing import Any

from langfuse import Langfuse, observe
from utils.masking import mask_dict, mask_text

from core.config import settings

logger = logging.getLogger(__name__)


class LangfuseClient:
    """Langfuse 客户端封装

    自动检测运行环境：
    - 测试环境（PYTEST_CURRENT_TEST 或 ENVIRONMENT=testing）：使用 Mock 客户端
    - 生产/开发环境且配置完整：使用真实 Langfuse 客户端
    - 配置缺失或初始化失败：降级为 Mock 客户端
    """

    def __init__(self):
        self.client: Langfuse | None = None
        self._mock_enabled = False

        if self._is_testing_environment():
            self._mock_enabled = True
            self._setup_mock_client()
            return

        if self._can_initialize_real_client():
            try:
                self.client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host,
                )
                logger.info("Langfuse 客户端初始化成功")
            except Exception as exc:
                logger.warning("Langfuse 客户端初始化失败，降级为 Mock: %s", exc)
                self._setup_mock_client()
        else:
            logger.info("Langfuse 未启用或配置缺失，使用 Mock 客户端")
            self._setup_mock_client()

    @staticmethod
    def _is_testing_environment() -> bool:
        """检测是否为测试环境"""
        env = os.environ.get("ENVIRONMENT", "")
        return "testing" in env.lower() or "PYTEST_CURRENT_TEST" in os.environ

    @staticmethod
    def _can_initialize_real_client() -> bool:
        """检查是否具备初始化真实客户端的条件"""
        return bool(
            settings.langfuse_enabled
            and settings.langfuse_public_key
            and settings.langfuse_secret_key
        )

    def _setup_mock_client(self):
        """设置 mock Langfuse 客户端用于测试或降级场景"""
        from unittest.mock import MagicMock

        self._mock_enabled = True
        self.client = MagicMock()
        self.client.trace = MagicMock(return_value=MagicMock(id="mock-trace-id"))
        self.client.start_as_current_span = MagicMock()
        self.client.start_as_current_observation = MagicMock()
        self.client.score_current_span = MagicMock()
        self.client.score_current_trace = MagicMock()
        self.client.flush = MagicMock()
        self.client.shutdown = MagicMock()

    def is_enabled(self) -> bool:
        """检查客户端是否可用"""
        return self.client is not None

    def is_mock(self) -> bool:
        """检查是否为 Mock 模式"""
        return self._mock_enabled

    def trace(self, **kwargs):
        """委托到内部 Langfuse client 创建 trace"""
        if not self.client:
            return None
        return self.client.trace(**kwargs)

    def flush(self):
        """刷新追踪数据到 Langfuse 服务端"""
        if self.client:
            self.client.flush()

    def shutdown(self):
        """关闭客户端连接"""
        if self.client:
            self.client.shutdown()


langfuse_client = LangfuseClient()


_trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
_span_stack_var: ContextVar[list[Any] | None] = ContextVar("span_stack", default=None)


def _get_span_stack() -> list[Any]:
    """获取当前 span 栈（惰性初始化）"""
    stack = _span_stack_var.get()
    if stack is None:
        stack = []
        _span_stack_var.set(stack)
    return stack


def get_current_trace_id() -> str | None:
    """获取当前请求的 trace ID"""
    return _trace_id_var.get()


def set_current_trace_id(trace_id: str | None) -> None:
    """设置当前请求的 trace ID"""
    _trace_id_var.set(trace_id)


def get_current_span() -> Any | None:
    """获取当前 Span 栈顶元素"""
    stack = _get_span_stack()
    return stack[-1] if stack else None


def trace_customer_service(
    name: str,
    session_id: str | None = None,
    user_id: str | None = None,
    metadata: dict | None = None,
):
    """智能客服会话追踪装饰器

    Usage::

        @trace_customer_service(
            name="api_error_troubleshooting",
            session_id="sess_123",
            user_id="user_456"
        )
        async def handle_message(...):
            ...
    """
    return observe(name=name, session_id=session_id, user_id=user_id, metadata=metadata or {})


class SpanManager:
    """Span 管理器

    提供基于 ContextVar 的 Span 创建、结束和评分能力。
    """

    @staticmethod
    def create_span(name: str, **kwargs):
        """创建 Span 并压入上下文栈"""
        if not langfuse_client.is_enabled():
            return DummySpan()

        trace_id = get_current_trace_id()
        if not trace_id:
            return DummySpan()

        trace = langfuse_client.client.trace(id=trace_id)
        span = trace.span(name=name, **kwargs)

        stack = _get_span_stack()
        stack.append(span)

        return span

    @staticmethod
    def end_span(span):
        """结束 Span 并从上下文栈弹出"""
        if hasattr(span, "end") and callable(span.end):
            span.end()

        stack = _get_span_stack()
        if span in stack:
            stack.remove(span)

    @staticmethod
    def score_current_span(name: str, value: float, comment: str | None = None):
        """对当前 Span 评分"""
        span = get_current_span()
        if span and hasattr(span, "score"):
            span.score(name=name, value=value, comment=comment)


class DummySpan:
    """空 Span（用于 Langfuse 禁用或 trace_id 缺失时的降级）"""

    def end(self, **kwargs):
        pass

    def score(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class Scores:
    """预定义评分项常量"""

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
    score_name: str,
    value: float,
    comment: str | None = None,
    trace_id: str | None = None,
):
    """对指定 Trace 评分"""
    if not langfuse_client.is_enabled():
        return

    if not trace_id:
        trace_id = get_current_trace_id()

    if not trace_id:
        return

    trace = langfuse_client.client.trace(id=trace_id)
    trace.score(name=score_name, value=value, comment=comment)


def create_trace_with_masking(
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict | None = None,
    input_data: Any | None = None,
    **kwargs,
):
    """创建脱敏后的 Trace

    自动对 user_id、metadata 和 input_data 中的 PII 信息进行脱敏处理。
    """
    if not langfuse_client.is_enabled():
        return None

    masked_metadata = mask_dict(metadata or {})
    masked_input = input_data
    if input_data and isinstance(input_data, dict):
        masked_input = mask_dict(input_data)
    elif input_data and isinstance(input_data, str):
        masked_input = mask_text(input_data)

    masked_user_id = user_id.split("@")[0][:3] + "***" if user_id else None

    trace = langfuse_client.client.trace(
        user_id=masked_user_id,
        session_id=session_id,
        metadata=masked_metadata,
        input=masked_input,
        **kwargs,
    )

    _trace_id_var.set(trace.id)

    return trace


def log_event(name: str, metadata: dict | None = None, level: str = "INFO"):
    """记录事件到当前 Trace"""
    if not langfuse_client.is_enabled():
        return

    trace_id = get_current_trace_id()
    if not trace_id:
        return

    trace = langfuse_client.client.trace(id=trace_id)
    trace.event(name=name, metadata=mask_dict(metadata) if metadata else None, level=level)


def create_span(name: str, **kwargs):
    """创建 Span 便捷函数"""
    return SpanManager.create_span(name, **kwargs)
