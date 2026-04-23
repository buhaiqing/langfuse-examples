"""
Tests for Trace ID Context Management.

This module tests the context-based trace ID propagation.
"""


import pytest

from skill_observability_toolkit.langfuse_integration.context import (
    TraceContextManager,
    clear_trace_context,
    create_trace_context,
    generate_trace_id,
    get_current_span,
    get_parent_trace_id,
    get_trace_id,
    pop_span,
    push_span,
    set_parent_trace_id,
    set_trace_id,
)


class TestTraceIdContext:
    """Tests for trace_id context management."""

    def test_set_get_trace_id(self):
        """Test setting and getting trace ID."""
        set_trace_id("trace_abc123")
        assert get_trace_id() == "trace_abc123"

    def test_trace_id_isolation(self):
        """Test that trace IDs are isolated per context."""
        set_trace_id("trace_1")
        assert get_trace_id() == "trace_1"

        # In same context, should get same ID
        assert get_trace_id() == "trace_1"

    def test_clear_trace_id(self):
        """Test clearing trace ID."""
        set_trace_id("trace_123")
        clear_trace_context()
        assert get_trace_id() is None


class TestTraceIdGeneration:
    """Tests for trace ID generation."""

    def test_generate_trace_id(self):
        """Test generating a new trace ID."""
        trace_id = generate_trace_id(prefix="test")

        assert trace_id is not None
        assert trace_id.startswith("test_")
        assert len(trace_id) > len("test_")

    def test_generate_trace_id_default_prefix(self):
        """Test generation with default prefix."""
        trace_id = generate_trace_id()

        assert trace_id is not None
        assert trace_id.startswith("skill_")


class TestParentTraceId:
    """Tests for parent trace ID (cross-layer correlation)."""

    def test_set_get_parent_trace_id(self):
        """Test setting and getting parent trace ID."""
        set_parent_trace_id("parent_trace_xyz")
        assert get_parent_trace_id() == "parent_trace_xyz"

    def test_parent_trace_id_isolation(self):
        """Test parent trace ID isolation."""
        set_parent_trace_id("parent_1")
        set_trace_id("child_1")

        assert get_parent_trace_id() == "parent_1"
        assert get_trace_id() == "child_1"

    def test_clear_parent_trace_id(self):
        """Test clearing parent trace ID."""
        set_parent_trace_id("parent_123")
        clear_trace_context()
        assert get_parent_trace_id() is None


class TestSpanContext:
    """Tests for span context stack."""

    def test_push_pop_span(self):
        """Test pushing and popping span."""
        span1 = {"span_id": "span1", "name": "operation1"}
        push_span(span1)

        current = get_current_span()
        assert current == span1

        popped = pop_span()
        assert popped == span1

        assert get_current_span() is None

    def test_push_multiple_spans(self):
        """Test multiple span nesting."""
        span1 = {"span_id": "span1", "name": "outer"}
        span2 = {"span_id": "span2", "name": "inner"}

        push_span(span1)
        push_span(span2)

        assert get_current_span() == span2

        popped = pop_span()
        assert popped == span2
        assert get_current_span() == span1

    def test_pop_empty_stack(self):
        """Test popping from empty stack."""
        # Ensure clean state
        clear_trace_context()

        result = pop_span()
        assert result is None


class TestTraceContextManager:
    """Tests for TraceContextManager context manager."""

    def test_context_manager_sets_trace_id(self):
        """Test context manager sets trace ID."""
        ctx = TraceContextManager(trace_id="trace_abc123")

        with ctx:
            assert get_trace_id() == "trace_abc123"

        # After exiting, should be cleared
        assert get_trace_id() is None

    def test_context_manager_sets_parent_trace_id(self):
        """Test context manager sets parent trace ID."""
        ctx = TraceContextManager(parent_trace_id="parent_xyz")

        with ctx:
            assert get_parent_trace_id() == "parent_xyz"

        # After exiting, should be cleared
        assert get_parent_trace_id() is None

    def test_context_manager_creates_nested(self):
        """Test nested context managers."""
        with TraceContextManager(trace_id="outer_trace"):
            assert get_trace_id() == "outer_trace"

            with TraceContextManager(trace_id="inner_trace"):
                assert get_trace_id() == "inner_trace"

            # Should restore to outer
            assert get_trace_id() == "outer_trace"

    def test_context_manager_handles_exception(self):
        """Test context manager handles exceptions."""
        ctx = TraceContextManager(trace_id="trace_abc")

        with pytest.raises(ValueError):
            with ctx:
                raise ValueError("Test error")

        # Should still clean up
        assert get_trace_id() is None


class TestCreateTraceContext:
    """Tests for create_trace_context factory function."""

    def test_create_trace_context(self):
        """Test creating trace context."""
        ctx = create_trace_context(trace_id="trace_123")

        assert isinstance(ctx, TraceContextManager)
        assert ctx.trace_id == "trace_123"

    def test_create_trace_context_without_trace_id(self):
        """Test creating context without trace ID."""
        ctx = create_trace_context()

        assert isinstance(ctx, TraceContextManager)
        assert ctx.trace_id is None


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self):
        """Test complete trace workflow."""
        # 1. Generate trace ID
        trace_id = generate_trace_id(prefix="skill")
        assert trace_id is not None

        # 2. Set parent (cross-layer)
        set_parent_trace_id("ci_build_123")

        # 3. Create some spans
        span1 = {"span_id": "span1", "name": "step1"}
        push_span(span1)

        span2 = {"span_id": "span2", "name": "step2"}
        push_span(span2)

        assert get_current_span() == span2

        # 4. Clear context
        clear_trace_context()

        assert get_trace_id() is None
        assert get_parent_trace_id() is None
        assert get_current_span() is None

    def test_context_manager_with_parent(self):
        """Test context manager with both trace and parent."""
        with create_trace_context(
            trace_id="trace_abc",
            parent_trace_id="parent_xyz",
        ):
            assert get_trace_id() == "trace_abc"
            assert get_parent_trace_id() == "parent_xyz"

        # Should be cleaned up
        assert get_trace_id() is None
        assert get_parent_trace_id() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
