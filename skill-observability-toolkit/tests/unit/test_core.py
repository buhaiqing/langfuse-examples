"""核心单元测试 - 只保留核心功能测试."""

import pytest

from skill_observability_toolkit.core.errors import TracingError, TracingErrorCode
from skill_observability_toolkit.stop.assertions import (
    AssertionEngine,
    AssertionResult,
)
from skill_observability_toolkit.stop.tracer import Span


class TestSpan:
    """Span 核心测试."""

    def test_span_end(self):
        """Test ending span."""
        span = Span(
            span_id="span_123",
            trace_id="trace_123",
            parent_span_id=None,
            name="test",
            start_time=1000.0,
        )
        span.end(output={"result": "success"}, status="success")
        assert span.status == "success"

    def test_span_score(self):
        """Test span scoring."""
        span = Span(
            span_id="span_123",
            trace_id="trace_123",
            parent_span_id=None,
            name="test",
            start_time=1000.0,
        )
        span.score(name="test_score", value=0.9, type_="NUMERIC")
        assert len(span.scores) == 1


class TestTracingError:
    """TracingError 核心测试."""

    def test_tracing_error_basic(self):
        """Test basic error."""
        error = TracingError(
            code=TracingErrorCode.LANGFUSE_UNAVAILABLE,
            message="Langfuse unavailable"
        )
        assert error.code == TracingErrorCode.LANGFUSE_UNAVAILABLE
        assert error.message == "Langfuse unavailable"

    def test_tracing_error_with_context(self):
        """Test error with context."""
        error = TracingError(
            code=TracingErrorCode.SCORE_VALIDATION_FAILED,
            message="Failed to score",
            context={"trace_id": "123"}
        )
        assert error.context["trace_id"] == "123"


class TestAssertionEngine:
    """AssertionEngine 核心测试."""

    def test_validate_pass(self):
        """Test valid assertion passes."""
        engine = AssertionEngine()
        assertions = [{"check": "string_not_empty", "value": "valid"}]
        assert engine.validate(assertions) is True

    def test_validate_fail(self):
        """Test invalid assertion fails."""
        engine = AssertionEngine()
        assertions = [{"check": "string_not_empty", "value": ""}]
        assert engine.validate(assertions) is False

    def test_calculate_trust_score(self):
        """Test trust score calculation."""
        engine = AssertionEngine()
        results = [
            AssertionResult(passed=True, assertion="check1"),
            AssertionResult(passed=False, assertion="check2"),
            AssertionResult(passed=True, assertion="check3"),
        ]
        score = engine.calculate_trust_score(results)
        assert score == pytest.approx(2/3)
