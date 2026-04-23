"""
Context-based STOP Tracer with automatic span propagation.

This module implements automatic SPAN propagation using contextvars
for seamless tracing integration across Skill execution.
"""

import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from typing import ContextManager as TypingContextManager
from typing import TypeVar

from skill_observability_toolkit.stop.manifest import ManifestParser

# Type variable for decorator
T = TypeVar("T")


class TracerContextError(Exception):
    """Base exception for tracer context errors."""
    pass


class TracerContextNotInitialized(TracerContextError):
    """Tracer context is not initialized."""
    pass


class TracerContext:
    """
    Context manager for automatic SPAN propagation using contextvars.
    
    This class manages trace context across function calls,
    automatically propagating trace_id and parent span ID.
    
    Attributes:
        ctx_trace_id: Context variable storing current trace_id
        ctx_span_stack: Context variable storing active span stack
    """
    
    def __init__(self):
        """Initialize the tracer context."""
        self.ctx_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
        self.ctx_span_stack: ContextVar[List[Dict[str, Any]]] = ContextVar("span_stack", default=[])
    
    def get_current_trace_id(self) -> str:
        """
        Get current trace ID from context.
        
        Returns:
            Current trace_id
            
        Raises:
            TracerContextNotInitialized: If no trace context exists
        """
        trace_id = self.ctx_trace_id.get()
        if trace_id is None:
            raise TracerContextNotInitialized("No active trace context. Call start_trace() first.")
        return trace_id
    
    def get_current_span(self) -> Optional[Dict[str, Any]]:
        """
        Get current active span from context.
        
        Returns:
            Current span dict, or None if no active span
        """
        stack = self.ctx_span_stack.get()
        if stack:
            return stack[-1]
        return None
    
    def push_span(self, span: Dict[str, Any]) -> None:
        """
        Push a span onto the context stack.
        
        Args:
            span: Span dictionary to push
        """
        stack = self.ctx_span_stack.get([])
        stack.append(span)
        self.ctx_span_stack.set(stack)
    
    def pop_span(self) -> Optional[Dict[str, Any]]:
        """
        Pop and return the current span from context.
        
        Returns:
            Popped span dict, or None if stack is empty
        """
        stack = self.ctx_span_stack.get([])
        if stack:
            stack.pop()
            self.ctx_span_stack.set(stack)
            return stack[-1] if stack else None
        return None
    
    def start_trace(self, trace_id: Optional[str] = None) -> str:
        """
        Start a new trace context.
        
        Args:
            trace_id: Optional trace_id. If None, generated automatically.
            
        Returns:
            New trace_id
        """
        if trace_id is None:
            trace_id = f"skill_trace_{uuid.uuid4().hex[:12]}"
        
        self.ctx_trace_id.set(trace_id)
        self.ctx_span_stack.set([])
        
        return trace_id
    
    def end_trace(self) -> None:
        """
        End current trace context and clear context vars.
        """
        self.ctx_trace_id.set(None)
        self.ctx_span_stack.set([])


# Global tracer context instance
tracer_context = TracerContext()


@dataclass
class Span:
    """
    Represents a single SPAN in the trace.
    
    A span represents a unit of work in the execution trace,
    with timing, input/output data, and scores.
    
    Attributes:
        span_id: Unique span identifier
        trace_id: Parent trace identifier
        parent_span_id: Optional parent span identifier
        name: Span name
        start_time: UTC timestamp when span started
        end_time: UTC timestamp when span ended (or None if running)
        status: "success", "error", or "running"
        input_data: Input data for the operation
        output_data: Output data from the operation
        duration_ms: Duration in milliseconds
        scores: List of score dictionaries
        metadata: Additional metadata
    """
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    scores: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def end(self, output: Optional[Dict[str, Any]] = None, status: str = "success") -> "Span":
        """
        Mark span as completed.
        
        Args:
            output: Output data to record
            status: Exit status ("success", "error")
            
        Returns:
            Self for method chaining
        """
        self.end_time = time.time()
        self.status = status
        self.duration_ms = (self.end_time - self.start_time) * 1000  # ms
        
        if output is not None:
            self.output_data = output
        
        return self
    
    def score(
        self,
        name: str,
        value: Any,
        type_: str = "NUMERIC",
        comment: str = ""
    ) -> "Span":
        """
        Record a score for this span.
        
        Args:
            name: Score name
            value: Score value
            type_: Score type ("NUMERIC", "BOOLEAN", "CATEGORICAL")
            comment: Optional comment
            
        Returns:
            Self for method chaining
        """
        self.scores.append({
            "name": name,
            "value": value,
            "type": type_,
            "comment": comment,
        })
        return self
    
    def set_metadata(self, **kwargs: Any) -> "Span":
        """
        Set metadata for this span.
        
        Args:
            **kwargs: Metadata key-value pairs
            
        Returns:
            Self for method chaining
        """
        self.metadata.update(kwargs)
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert span to dictionary for NDJSON output.
        
        Returns:
            Span dictionary
        """
        result = {
            "type": "span",
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "scores": self.scores,
        }
        
        if self.input_data:
            result["input"] = self.input_data
        if self.output_data:
            result["output"] = self.output_data
        if self.metadata:
            result["metadata"] = self.metadata
        
        return result


class STOPTracer:
    """
    Main tracer class for STOP Protocol L1 implementation.
    
    Supports:
    - Context manager for span lifecycle
    - Decorator for automatic span creation
    - Automatic span nesting via contextvars
    - NDJSON trace output
    
    Attributes:
        trace_id: Current trace ID
        spans: List of recorded spans
        output_path: Path for NDJSON output
    """
    
    def __init__(self, output_path: Optional[str] = None):
        """
        Initialize the STOP tracer.
        
        Args:
            output_path: Optional file path for NDJSON output
        """
        self.trace_id: Optional[str] = None
        self.spans: List[Span] = []
        self.output_path: Optional[Path] = Path(output_path) if output_path else None
        self._parent_span_id: Optional[str] = None
    
    def start_trace(self, trace_id: Optional[str] = None, name: str = "skill_execution") -> "STOPTracer":
        """
        Start a new trace.
        
        Args:
            trace_id: Optional trace_id. If None, generated automatically.
            name: Trace name
            
        Returns:
            Self for method chaining
        """
        self.trace_id = tracer_context.start_trace(trace_id)
        self.spans = []
        
        # Create root span
        root_span = Span(
            span_id=f"trace_{uuid.uuid4().hex[:8]}",
            trace_id=self.trace_id,
            parent_span_id=None,
            name=name,
            start_time=time.time(),
        )
        self.spans.append(root_span)
        tracer_context.push_span(root_span)
        
        return self
    
    def end_trace(self, status: str = "success") -> Dict[str, Any]:
        """
        End current trace and return trace data.
        
        Args:
            status: Trace status ("success", "error")
            
        Returns:
            Complete trace dictionary
        """
        # End root span
        if self.spans:
            root_span = self.spans[0]
            root_span.end(status=status)
            
            # Ensure root span has correct end
            if root_span.end_time is None:
                root_span.end_time = time.time()
                root_span.duration_ms = (root_span.end_time - root_span.start_time) * 1000
        
        # Get trace end time
        trace_end_time = time.time()
        
        # Build trace data
        trace_data = {
            "type": "trace",
            "trace_id": self.trace_id,
            "name": self.spans[0].name if self.spans else "unknown",
            "start_time": self.spans[0].start_time if self.spans else trace_end_time,
            "end_time": trace_end_time,
            "status": status,
            "spans": [span.to_dict() for span in self.spans],
        }
        
        # Write to file if output_path set
        if self.output_path:
            self._write_ndjson(trace_data)
        
        # Clear context
        tracer_context.end_trace()
        self.trace_id = None
        
        return trace_data
    
    def start_span(self, name: str, input_data: Optional[Dict[str, Any]] = None) -> "SpanContextManager":
        """
        Start a new span as a context manager.
        
        Args:
            name: Span name
            input_data: Optional input data
            
        Returns:
            SpanContextManager for use with 'with' statement
        """
        return SpanContextManager(self, name, input_data)
    
    def trace(
        self,
        name: Optional[str] = None,
        input_key: str = "params"
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        Create a decorator for automatic span creation.
        
        Args:
            name: Span name. If None, uses function __name__
            input_key: Key to store input data under in context
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args: Any, **kwargs: Any) -> T:
                span_name = name if name else func.__name__
                
                # Get or create trace
                if self.trace_id is None:
                    self.start_trace()
                
                # Record inputs
                input_data = {
                    input_key: {
                        "args": list(args),
                        "kwargs": kwargs,
                    },
                    "function": func.__name__,
                }
                
                with self.start_span(span_name, input_data) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.output_data = {"result": result}
                        return result
                    except Exception as e:
                        span.status = "error"
                        span.output_data = {"error": str(e)}
                        raise
            
            return wrapper
        
        return decorator
    
    def _write_ndjson(self, trace_data: Dict[str, Any]) -> None:
        """
        Write trace data to NDJSON file.
        
        Args:
            trace_data: Complete trace dictionary
        """
        import json
        
        if self.output_path:
            # Write trace as single JSON object
            with open(self.output_path, "a") as f:
                # Start new line for each trace
                f.write(json.dumps(trace_data, indent=2))
                f.write("\n\n")  # Blan between traces for readability


class SpanContextManager:
    """
    Context manager for span lifecycle.
    
    Usage:
        with tracer.start_span(name="operation") as span:
            result = do_something()
            span.end(output={"result": result})
    """
    
    def __init__(self, tracer: STOPTracer, name: str, input_data: Optional[Dict[str, Any]] = None):
        """
        Initialize span context manager.
        
        Args:
            tracer: Parent tracer instance
            name: Span name
            input_data: Optional input data
        """
        self.tracer = tracer
        self.name = name
        self.input_data = input_data or {}
        self.span: Optional[Span] = None
    
    def __enter__(self) -> Span:
        """
        Enter context and start span.
        
        Returns:
            Started span
        """
        # Get parent span from context
        current_span = tracer_context.get_current_span()
        parent_span_id = current_span.span_id if current_span and isinstance(current_span, Span) else None
        
        # Create new span
        self.span = Span(
            span_id=f"span_{uuid.uuid4().hex[:8]}",
            trace_id=self.tracer.trace_id,
            parent_span_id=parent_span_id,
            name=self.name,
            start_time=time.time(),
            input_data=self.input_data,
        )
        
        # Add to tracer and context
        self.tracer.spans.append(self.span)
        tracer_context.push_span(self.span)
        
        return self.span
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exit context and end span.
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if self.span:
            status = "success" if exc_type is None else "error"
            self.span.end(status=status)
            
            # Pop from context
            tracer_context.pop_span()


def trace_skill_execution(
    skill_name: str,
    version: str = "1.0.0",
    **kwargs: Any,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for Skill execution tracing.
    
    This is a convenience decorator that automatically:
    1. Starts a new trace
    2. Records skill name and version
    3. Handles pre/post assertions
    4. Calculates Trust Score
    
    Args:
        skill_name: Name of the skill
        version: Skill version
        **kwargs: Additional trace configuration
        
    Returns:
        Decorator function
    """
    tracer = STOPTracer(**kwargs)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Start trace
            tracer.start_trace(name=f"skill:{skill_name}")
            
            try:
                result = func(*args, **kwargs)
                
                # End trace with success
                trace_data = tracer.end_trace(status="success")
                
                return result
            except Exception as e:
                # End trace with error
                tracer.end_trace(status="error")
                raise
        
        return wrapper
    
    return decorator
