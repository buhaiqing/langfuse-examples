"""
Tracing Decorators.

This module provides decorators for automatic tracing of skills and tools
with integration to both STOP Protocol and Langfuse.
"""

import functools
import time
from typing import Any, Callable, Dict, Optional

from skill_observability_toolkit.langfuse_integration.client import (
    LangfuseClient,
)
from skill_observability_toolkit.langfuse_integration.context import (
    get_trace_id,
    set_trace_id,
)
from skill_observability_toolkit.stop.tracer import STOPTracer


def trace_skill_execution(
    skill_name: str,
    version: str,
    trace_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """
    Decorator for tracing skill execution.
    
    Args:
        skill_name: Name of the skill
        version: Version of the skill
        trace_id: Optional trace ID
        session_id: Session identifier
        user_id: User identifier
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            client = LangfuseClient.get_instance()
            tracer = STOPTracer()
            
            # Use provided trace_id or get from context
            current_trace_id = trace_id or get_trace_id()
            
            # Start trace if not exists
            if not current_trace_id:
                current_trace_id = tracer.start_trace(
                    name=f"skill:{skill_name}:{version}",
                )
                set_trace_id(current_trace_id)
            
            start_time = time.time()
            
            try:
                # Create span for skill execution
                span = tracer.start_span(
                    name=f"skill.execute:{skill_name}",
                    input_data={"args": str(args), "kwargs": str(kwargs)},
                )
                
                # Execute skill
                result = func(*args, **kwargs)
                
                duration_ms = (time.time() - start_time) * 1000
                
                # End span
                span.end(
                    output={"result": str(result)[:500]},
                    status="success",
                )
                
                # Score trace if Langfuse available
                if client:
                    client.score_trace(
                        name="execution_time_ms",
                        value=duration_ms,
                        comment=f"Skill {skill_name} v{version} execution time",
                    )
                    client.score_trace(
                        name="success",
                        value=1,
                        data_type="BOOLEAN",
                    )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # End span with error
                span.end(
                    output={"error": str(e)},
                    status="error",
                )
                
                # Score trace with error
                if client:
                    client.score_trace(
                        name="success",
                        value=0,
                        data_type="BOOLEAN",
                    )
                    client.score_trace(
                        name="error",
                        value=str(e),
                        data_type="CATEGORICAL",
                    )
                
                raise
                
            finally:
                # End trace
                tracer.end_trace(status="success")
        
        return wrapper
    return decorator


def trace_tool_call(
    tool_name: str,
    tool_input: Optional[Dict] = None,
    trace_id: Optional[str] = None,
):
    """
    Decorator for tracing tool calls.
    
    Args:
        tool_name: Name of the tool
        tool_input: Optional tool input data
        trace_id: Optional trace ID
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            client = LangfuseClient.get_instance()
            tracer = STOPTracer()
            
            # Use current trace_id
            current_trace_id = trace_id or get_trace_id()
            
            start_time = time.time()
            
            try:
                # Create span for tool call
                span = tracer.start_span(
                    name=f"tool:{tool_name}",
                    input_data=tool_input or {"args": str(args), "kwargs": str(kwargs)},
                )
                
                # Execute tool
                result = func(*args, **kwargs)
                
                duration_ms = (time.time() - start_time) * 1000
                
                # End span
                span.end(
                    output={"result": str(result)[:500]},
                    status="success",
                )
                
                # Score trace if Langfuse available
                if client:
                    client.score_trace(
                        name=f"{tool_name}_duration_ms",
                        value=duration_ms,
                        comment=f"Tool {tool_name} execution time",
                    )
                    client.score_trace(
                        name=f"{tool_name}_success",
                        value=1,
                        data_type="BOOLEAN",
                    )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # End span with error
                span.end(
                    output={"error": str(e)},
                    status="error",
                )
                
                # Score trace with error
                if client:
                    client.score_trace(
                        name=f"{tool_name}_success",
                        value=0,
                        data_type="BOOLEAN",
                    )
                    client.score_trace(
                        name=f"{tool_name}_error",
                        value=str(e),
                        data_type="CATEGORICAL",
                    )
                
                raise
                
            finally:
                # End trace
                tracer.end_trace(status="success")
        
        return wrapper
    return decorator


def trace_function(
    name: str,
    input_data: Optional[Dict] = None,
    trace_id: Optional[str] = None,
):
    """
    Generic decorator for tracing any function.
    
    Args:
        name: Function name for tracing
        input_data: Optional input data
        trace_id: Optional trace ID
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = STOPTracer()
            current_trace_id = trace_id or get_trace_id()
            
            start_time = time.time()
            
            try:
                # Create span
                span = tracer.start_span(
                    name=name,
                    input_data=input_data or {"args": str(args), "kwargs": str(kwargs)},
                )
                
                # Execute function
                result = func(*args, **kwargs)
                
                duration_ms = (time.time() - start_time) * 1000
                
                # End span
                span.end(
                    output={"result": str(result)[:500]},
                    status="success",
                )
                
                return result
                
            except Exception as e:
                span.end(
                    output={"error": str(e)},
                    status="error",
                )
                raise
                
            finally:
                tracer.end_trace(status="success")
        
        return wrapper
    return decorator
