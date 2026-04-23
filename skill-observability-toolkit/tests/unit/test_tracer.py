"""
Unit tests for STOP Tracer.
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from skill_observability_toolkit.stop.tracer import (
    Span,
    STOPTracer,
    TracerContext,
    TracerContextNotInitialized,
    trace_skill_execution,
)


class TestTracerContext:
    """Tests for TracerContext class."""

    def test_init(self):
        """Test context initialization."""
        ctx = TracerContext()
        assert ctx.ctx_trace_id.get() is None
        assert ctx.ctx_span_stack.get() == []

    def test_start_trace_generates_id(self):
        """Test trace ID generation."""
        ctx = TracerContext()
        trace_id = ctx.start_trace()

        assert trace_id is not None
        assert trace_id.startswith("skill_trace_")
        assert len(trace_id) > len("skill_trace_")

    def test_start_trace_with_custom_id(self):
        """Test trace with custom ID."""
        ctx = TracerContext()
        trace_id = ctx.start_trace("custom_trace_id")

        assert trace_id == "custom_trace_id"

    def test_get_current_trace_id(self):
        """Test getting current trace ID."""
        ctx = TracerContext()
        ctx.start_trace("test_trace")

        assert ctx.get_current_trace_id() == "test_trace"

    def test_get_current_trace_id_not_initialized(self):
        """Test getting trace ID without initialization raises error."""
        ctx = TracerContext()

        with pytest.raises(TracerContextNotInitialized):
            ctx.get_current_trace_id()

    def test_push_pop_span(self):
        """Test push and pop spans."""
        ctx = TracerContext()
        ctx.start_trace()

        span1 = {"span_id": "span1", "name": "operation1"}
        span2 = {"span_id": "span2", "name": "operation2"}

        ctx.push_span(span1)
        ctx.push_span(span2)

        assert len(ctx.ctx_span_stack.get()) == 2
        assert ctx.get_current_span() == span2

        # pop_span returns the new current span or None
        current = ctx.pop_span()
        assert current == span1  # After removing span2, span1 is current
        assert ctx.get_current_span() == span1

        ctx.pop_span()
        assert ctx.get_current_span() is None

    def test_end_trace(self):
        """Test ending trace."""
        ctx = TracerContext()
        ctx.start_trace("test_trace")

        ctx.end_trace()

        assert ctx.ctx_trace_id.get() is None
        assert ctx.ctx_span_stack.get() == []


class TestSpan:
    """Tests for Span class."""

    def test_init(self):
        """Test span initialization."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            parent_span_id=None,
            name="test_operation",
            start_time=time.time(),
        )

        assert span.span_id == "span123"
        assert span.trace_id == "trace456"
        assert span.parent_span_id is None
        assert span.name == "test_operation"
        assert span.status == "running"
        assert span.end_time is None
        assert span.duration_ms == 0

    def test_end(self):
        """Test ending span."""
        start_time = time.time()
        time.sleep(0.01)  # Small delay for measurable time

        span = Span(
            span_id="span123",
            trace_id="trace456",
            parent_span_id=None,
            name="test_operation",
            start_time=start_time,
        )

        span.end(output={"result": "success"}, status="success")

        assert span.end_time is not None
        assert span.status == "success"
        assert span.duration_ms >= 10  # Should be at least 10ms
        assert span.output_data == {"result": "success"}

    def test_score(self):
        """Test recording scores."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            parent_span_id=None,
            name="test_operation",
            start_time=time.time(),
        )

        span.score("accuracy", 0.95, "NUMERIC", "Model accuracy score")
        span.score("passed", True, "BOOLEAN")
        span.score("status", "approved", "CATEGORICAL", "Approval status")

        assert len(span.scores) == 3
        assert span.scores[0] == {
            "name": "accuracy",
            "value": 0.95,
            "type": "NUMERIC",
            "comment": "Model accuracy score",
        }

    def test_set_metadata(self):
        """Test setting metadata."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            parent_span_id=None,
            name="test_operation",
            start_time=time.time(),
        )

        span.set_metadata(
            key1="value1",
            key2=123,
            key3={"nested": "object"},
        )

        assert span.metadata == {
            "key1": "value1",
            "key2": 123,
            "key3": {"nested": "object"},
        }

    def test_to_dict(self):
        """Test span to_dict conversion."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            parent_span_id="parent789",
            name="test_operation",
            start_time=time.time(),
        )
        span.end(output={"result": "success"}, status="success")
        span.score("accuracy", 0.95, "NUMERIC", "Model accuracy score")
        span.set_metadata(metadata1="value1")

        result = span.to_dict()

        assert result["type"] == "span"
        assert result["span_id"] == "span123"
        assert result["trace_id"] == "trace456"
        assert result["parent_span_id"] == "parent789"
        assert result["name"] == "test_operation"
        assert result["status"] == "success"
        assert result["duration_ms"] >= 0
        # Comment field is optional, so it should be included
        assert result["scores"][0]["comment"] == "Model accuracy score"
        assert result["output"] == {"result": "success"}
        assert result["metadata"] == {"metadata1": "value1"}

    def test_to_dict_without_optional_fields(self):
        """Test to_dict without optional fields."""
        span = Span(
            span_id="span123",
            trace_id="trace456",
            parent_span_id=None,
            name="test_operation",
            start_time=time.time(),
        )

        result = span.to_dict()

        assert "input" not in result
        assert "output" not in result
        assert "metadata" not in result
        assert result["scores"] == []


class TestSpanContextManager:
    """Tests for SpanContextManager."""

    def test_context_manager(self):
        """Test context manager usage."""
        tracer = STOPTracer()
        tracer.start_trace("trace123")

        with tracer.start_span(name="test_operation") as span:
            assert span.name == "test_operation"
            assert span.status == "running"
            assert span.trace_id == "trace123"

            span.end(output={"result": "success"}, status="success")

        assert span.status == "success"
        assert len(tracer.spans) == 2  # Root + nested span


class TestSTOPTracer:
    """Tests for STOPTracer class."""

    def test_init(self):
        """Test tracer initialization."""
        tracer = STOPTracer()
        assert tracer.trace_id is None
        assert tracer.spans == []
        assert tracer.output_path is None

    def test_start_trace(self):
        """Test starting a trace."""
        tracer = STOPTracer()
        tracer.start_trace(name="test_trace")

        assert tracer.trace_id is not None
        assert len(tracer.spans) == 1
        assert tracer.spans[0].name == "test_trace"

    def test_start_trace_with_custom_id(self):
        """Test starting trace with custom ID."""
        tracer = STOPTracer()
        tracer.start_trace(trace_id="custom_trace_123")

        assert tracer.trace_id == "custom_trace_123"

    def test_end_trace(self):
        """Test ending a trace."""
        tracer = STOPTracer()
        tracer.start_trace(name="test_trace")

        with tracer.start_span(name="operation1"):
            pass

        trace_data = tracer.end_trace(status="success")

        assert tracer.trace_id is None
        assert trace_data["type"] == "trace"
        assert trace_data["trace_id"] is not None
        assert trace_data["status"] == "success"
        assert len(trace_data["spans"]) == 2  # Root + operation1

        # Check span structure using index access
        spans_list = trace_data["spans"]
        assert spans_list[0]["type"] == "span"
        assert spans_list[0]["name"] == "test_trace"

    def test_start_span(self):
        """Test starting a span."""
        tracer = STOPTracer()
        tracer.start_trace("trace123")

        # Store span reference before context exits
        with tracer.start_span(name="test_operation", input_data={"input": "data"}) as span:
            assert span.name == "test_operation"
            assert span.input_data == {"input": "data"}
            assert span.trace_id == "trace123"

        # Check tracer.spans using list instead of direct access
        spans_list = tracer.spans
        assert len(spans_list) == 2  # Root + 1 nested span
        assert spans_list[1].name == "test_operation"

    def test_trace_decorator(self):
        """Test trace decorator."""
        tracer = STOPTracer()

        @tracer.trace(name="test_operation")
        def test_function(x: int, y: int) -> int:
            return x + y

        result = test_function(3, 4)

        assert result == 7
        assert len(tracer.spans) == 2  # Root + decorated function

        # Access spans via list
        spans_list = tracer.spans
        assert spans_list[1].name == "test_operation"
        assert spans_list[1].output_data.get("result") == 7

    def test_trace_decorator_with_function_name(self):
        """Test trace decorator uses function name."""
        tracer = STOPTracer()

        @tracer.trace()
        def my_function() -> str:
            return "test"

        my_function()

        # Access spans via list
        spans_list = tracer.spans
        assert spans_list[1].name == "my_function"

    def test_trace_decorator_exception(self):
        """Test trace decorator with exception."""
        tracer = STOPTracer()

        @tracer.trace(name="test_function")
        def failing_function() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        # Access spans via list
        spans_list = tracer.spans
        assert spans_list[1].status == "error"
        error_msg = str(spans_list[1].output_data.get("error", ""))
        assert "Test error" in error_msg

    def test_write_ndjson(self):
        """Test NDJSON file output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "trace.ndjson"

            tracer = STOPTracer(output_path=str(output_file))
            tracer.start_trace("trace123")

            with tracer.start_span(name="test_operation"):
                pass

            tracer.end_trace()

            # Check file exists
            assert output_file.exists()

            # Check content
            content = output_file.read_text()
            trace_data = json.loads(content.strip())

            assert trace_data["type"] == "trace"
            assert trace_data["trace_id"] == "trace123"


class TestTraceSkillExecutionDecorator:
    """Tests for trace_skill_execution decorator."""

    def test_decorator(self):
        """Test basic decorator usage."""
        @trace_skill_execution(skill_name="test-skill")
        def execute_skill(x: int) -> int:
            return x * 2

        result = execute_skill(5)
        assert result == 10

    def test_decorator_with_version(self):
        """Test decorator with version."""
        @trace_skill_execution(skill_name="test-skill", version="1.0.0")
        def execute_skill() -> dict:
            return {"result": "success"}

        result = execute_skill()
        assert result["result"] == "success"


class TestSpanNesting:
    """Tests for nested span functionality."""

    def test_nested_spans(self):
        """Test nested span creation."""
        tracer = STOPTracer()
        tracer.start_trace("trace123")

        with tracer.start_span(name="parent") as parent:
            with tracer.start_span(name="child1") as child1:
                child1.end(output={"result": "child1"})

            with tracer.start_span(name="child2") as child2:
                child2.end(output={"result": "child2"})

            parent.end(output={"result": "parent"})

        assert len(tracer.spans) == 4  # Root + parent + 2 children

        # Check span names using list access
        spans_list = tracer.spans
        span_names = [span.name for span in spans_list]
        assert "parent" in span_names
        assert "child1" in span_names
        assert "child2" in span_names

    def test_span_hierarchy(self):
        """Test span parent-child relationships."""
        tracer = STOPTracer()
        tracer.start_trace(trace_id="trace123", name="my_trace")

        with tracer.start_span(name="parent") as parent:
            with tracer.start_span(name="child") as child:
                child.end()

            parent.end()

        # Access via list
        spans_list = tracer.spans

        # Root span is at index 0
        assert spans_list[0].name == "my_trace"
        assert spans_list[0].parent_span_id is None

        # Parent is at index 1
        assert spans_list[1].name == "parent"

        # Child is at index 2
        assert spans_list[2].name == "child"
        assert spans_list[2].parent_span_id == spans_list[1].span_id

    def test_multiple_nesting_levels(self):
        """Test multiple levels of nesting."""
        tracer = STOPTracer()
        tracer.start_trace(trace_id="trace123", name="my_trace")

        with tracer.start_span(name="level1") as level1:
            with tracer.start_span(name="level2") as level2:
                with tracer.start_span(name="level3") as level3:
                    level3.end()
                level2.end()
            level1.end()

        assert len(tracer.spans) == 4  # Root + 3 levels

        # Access via list
        spans_list = tracer.spans

        # Root at index 0
        assert spans_list[0].name == "my_trace"
        assert spans_list[0].parent_span_id is None

        # level1 nested directly under root
        assert spans_list[1].name == "level1"

        # level2 nested under level1
        assert spans_list[2].name == "level2"
        assert spans_list[2].parent_span_id == spans_list[1].span_id

        # level3 nested under level2
        assert spans_list[3].name == "level3"
        assert spans_list[3].parent_span_id == spans_list[2].span_id


class TestIntegrationWithManifestParser:
    """Tests for integration with ManifestParser."""

    def test_manual_integration(self, valid_skill_yaml_path: str):
        """Test manual integration with ManifestParser."""
        from skill_observability_toolkit.stop.manifest import ManifestParser

        parser = ManifestParser(valid_skill_yaml_path)
        manifest = parser.parse()

        tracer = STOPTracer()
        tracer.start_trace(trace_id=manifest.name, name=manifest.name)

        # Run pre-assertions
        with tracer.start_span(name="pre_assertions") as span:
            span.score("pre_assertions_passed", 1.0, "NUMERIC")
            span.end()

        # Execute skill
        with tracer.start_span(name="execute_skill") as span:
            result = {"success": True, "word_count": 100}
            span.end(output=result)

        # Calculate trust score
        parser.add_trust_score([
            {"passed": True},
            {"passed": True},
        ])

        # End trace
        trace_data = tracer.end_trace(status="success")

        assert trace_data["trace_id"] == manifest.name
        assert len(trace_data["spans"]) == 3  # Root + 2 operations (pre_assertions + execute_skill)


# Fixtures

@pytest.fixture
def valid_skill_yaml_path() -> str:
    """Path to valid skill YAML fixture."""
    return "tests/fixtures/valid_skill.yaml"


@pytest.fixture
def valid_skill_yaml_path_nonexistent() -> str:
    """Path to nonexistent skill YAML."""
    return "tests/fixtures/nonexistent.yaml"
