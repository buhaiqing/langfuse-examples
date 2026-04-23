"""
Trace Correlation Logic.

This module provides trace correlation functionality,
enabling end-to-end correlation of spans across CI → Skill → MCP layers.
"""

import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Span:
    """A span representing a piece of work."""
    span_id: str
    name: str
    trace_id: str
    parent_span_id: str | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: str = "running"
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    def end(self, status: str = "success", attributes: dict[str, Any] | None = None):
        """End the span."""
        self.end_time = time.time()
        self.status = status

        if attributes:
            self.attributes.update(attributes)

    def duration_ms(self) -> float | None:
        """Get span duration in milliseconds."""
        if not self.end_time:
            return None
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "span_id": self.span_id,
            "name": self.name,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms(),
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events,
        }


@dataclass
class Trace:
    """A trace representing a request flow."""
    trace_id: str
    name: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    spans: list[Span] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)

    def add_span(self, span: Span):
        """Add a span to the trace."""
        self.spans.append(span)

    def end(self):
        """End the trace."""
        self.end_time = time.time()

    def top_level_spans(self) -> list[Span]:
        """Get top-level spans (no parent)."""
        return [s for s in self.spans if s.parent_span_id is None]

    def children_spans(self, parent_span_id: str) -> list[Span]:
        """Get child spans for a parent."""
        return [s for s in self.spans if s.parent_span_id == parent_span_id]

    def span_tree(self) -> dict[str, Any]:
        """Build span tree structure."""
        roots = self.top_level_spans()
        tree = {}

        for root in roots:
            tree[root.span_id] = self._build_span_tree(root)

        return tree

    def _build_span_tree(self, span: Span) -> dict[str, Any]:
        """Build span tree recursively."""
        children = self.children_spans(span.span_id)

        return {
            "span": span.to_dict(),
            "children": [
                self._build_span_tree(child)
                for child in children
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": (
                (self.end_time or time.time()) - self.start_time
            ) * 1000,
            "spans": [s.to_dict() for s in self.spans],
            "span_count": len(self.spans),
            "top_level_spans": len(self.top_level_spans()),
        }


@dataclass
class CorrelationContext:
    """Context for trace correlation."""
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    trace_state: dict[str, str] = field(default_factory=dict)
    layer: str = "unknown"  # "ci", "skill", "mcp"
    tags: dict[str, str] = field(default_factory=dict)


# Context var for current correlation context
_correlation_context: ContextVar[CorrelationContext] = ContextVar(
    "correlation_context", default=None
)


class TraceCorrelator:
    """
    Correlate traces across layers.

    Provides functionality to:
    - Create and manage spans
    - Build trace trees
    - Correlate traces across layers
    - Generate correlation IDs
    """

    def __init__(self):
        """Initialize the correlator."""
        self._traces: dict[str, Trace] = {}
        self._current_trace_id: str | None = None
        self._current_span_id: str | None = None

    def start_trace(
        self,
        trace_id: str | None = None,
        name: str = "trace",
        layer: str = "unknown",
        tags: dict[str, str] | None = None,
    ) -> str:
        """
        Start a new trace.

        Args:
            trace_id: Trace ID (generated if None)
            name: Trace name
            layer: Layer name (ci, skill, mcp)
            tags: Trace tags

        Returns:
            Trace ID
        """
        if not trace_id:
            import uuid
            trace_id = f"trace_{uuid.uuid4().hex[:12]}"

        self._traces[trace_id] = Trace(
            trace_id=trace_id,
            name=name,
        )

        self._current_trace_id = trace_id

        # Set correlation context
        context = CorrelationContext(
            trace_id=trace_id,
            layer=layer,
            tags=tags or {},
        )
        _correlation_context.set(context)

        return trace_id

    def start_span(
        self,
        name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """
        Start a new span.

        Args:
            name: Span name
            trace_id: Trace ID (uses current if None)
            parent_span_id: Parent span ID
            attributes: Span attributes

        Returns:
            Span instance
        """
        if not trace_id:
            trace_id = self._current_trace_id or _correlation_context.get().trace_id

        if not trace_id:
            raise ValueError("No trace_id available. Call start_trace() first.")

        import uuid
        span_id = f"span_{uuid.uuid4().hex[:12]}"

        span = Span(
            span_id=span_id,
            name=name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            attributes=attributes or {},
        )

        # Add span to trace
        if trace_id in self._traces:
            self._traces[trace_id].add_span(span)

        # Set as current span
        self._current_span_id = span_id

        # Update correlation context
        context = _correlation_context.get()
        context.span_id = span_id
        context.parent_span_id = parent_span_id
        context.trace_state[span_id] = "active"
        _correlation_context.set(context)

        return span

    def end_span(self, status: str = "success", attributes: dict[str, Any] | None = None):
        """End the current span."""
        context = _correlation_context.get()
        span_id = context.span_id

        if not span_id:
            return None

        # Find span
        for trace in self._traces.values():
            for span in trace.spans:
                if span.span_id == span_id:
                    span.end(status=status, attributes=attributes)
                    break

        # Update context
        context.span_id = context.parent_span_id
        _correlation_context.set(context)

        self._current_span_id = context.span_id

        return span

    def get_current_trace(self) -> Trace | None:
        """Get current trace."""
        if self._current_trace_id and self._current_trace_id in self._traces:
            return self._traces[self._current_trace_id]
        return None

    def get_trace(self, trace_id: str) -> Trace | None:
        """Get a trace by ID."""
        return self._traces.get(trace_id)

    def list_traces(self) -> list[str]:
        """List all trace IDs."""
        return list(self._traces.keys())

    def correlate_traces(
        self,
        ci_trace_id: str | None = None,
        skill_trace_id: str | None = None,
        mcp_trace_id: str | None = None,
    ) -> dict[str, str | None]:
        """
        Correlate traces across layers.

        Args:
            ci_trace_id: CI trace ID
            skill_trace_id: Skill trace ID
            mcp_trace_id: MCP trace ID

        Returns:
            Dictionary with correlated trace IDs
        """
        correlation = {
            "ci_trace_id": ci_trace_id,
            "skill_trace_id": skill_trace_id,
            "mcp_trace_id": mcp_trace_id,
        }

        # Set up parent-child relationships
        if ci_trace_id and skill_trace_id:
            # Skill trace is child of CI trace
            correlation["parent_of_skill"] = ci_trace_id

        if skill_trace_id and mcp_trace_id:
            # MCP trace is child of Skill trace
            correlation["parent_of_mcp"] = skill_trace_id

        return correlation

    def get_correlation_tree(self) -> dict[str, Any]:
        """
        Build a correlation tree across all layers.

        Returns:
            Correlation tree
        """
        tree = {
            "traces": {},
        }

        for trace_id, trace in self._traces.items():
            tree["traces"][trace_id] = {
                "trace": trace.to_dict(),
                "span_tree": trace.span_tree(),
            }

        return tree

    def clear(self):
        """Clear all traces and contexts."""
        self._traces = {}
        self._current_trace_id = None
        self._current_span_id = None

        # Clear correlation context
        _correlation_context.set(CorrelationContext())


# Global correlator instance
_correlator = TraceCorrelator()


def start_trace(
    trace_id: str | None = None,
    name: str = "trace",
    layer: str = "unknown",
    tags: dict[str, str] | None = None,
) -> str:
    """Start a new trace (convenience function)."""
    return _correlator.start_trace(trace_id, name, layer, tags)


def start_span(
    name: str,
    trace_id: str | None = None,
    parent_span_id: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Span:
    """Start a new span (convenience function)."""
    return _correlator.start_span(name, trace_id, parent_span_id, attributes)


def end_span(status: str = "success", attributes: dict[str, Any] | None = None):
    """End the current span (convenience function)."""
    return _correlator.end_span(status, attributes)


def get_current_trace() -> Trace | None:
    """Get current trace (convenience function)."""
    return _correlator.get_current_trace()


def correlate_traces(
    ci_trace_id: str | None = None,
    skill_trace_id: str | None = None,
    mcp_trace_id: str | None = None,
) -> dict[str, str | None]:
    """Correlate traces (convenience function)."""
    return _correlator.correlate_traces(
        ci_trace_id, skill_trace_id, mcp_trace_id
    )


def get_correlation_tree() -> dict[str, Any]:
    """Get correlation tree (convenience function)."""
    return _correlator.get_correlation_tree()


def clear_correlation():
    """Clear correlation state (convenience function)."""
    _correlator.clear()


def get_correlation_context() -> CorrelationContext:
    """Get current correlation context."""
    return _correlation_context.get()
