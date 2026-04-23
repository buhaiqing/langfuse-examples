"""
Langfuse Integration Client.

This module provides a wrapper around the Langfuse SDK for integrated
tracing with STOP Protocol.
"""

import os
from typing import Any, Dict, Optional
from contextvars import ContextVar

from langfuse import Langfuse


class LangfuseClient:
    """Singleton client for Langfuse integration with STOP Protocol."""
    
    _instance: Optional["LangfuseClient"] = None
    _langfuse: Optional[Langfuse] = None
    
    # Context variable for trace_id propagation
    _trace_id_context: ContextVar[Optional[str]] = ContextVar(
        "trace_id", default=None
    )
    
    # Context variable for parent_trace_id (cross-layer correlation)
    _parent_trace_id_context: ContextVar[Optional[str]] = ContextVar(
        "parent_trace_id", default=None
    )
    
    def __new__(cls) -> "LangfuseClient":
        """Create singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize Langfuse client."""
        if self._langfuse is not None:
            return
        
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        
        if not public_key or not secret_key:
            self._langfuse = None
            return
        
        self._langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            debug=False,
        )
    
    @classmethod
    def get_instance(cls) -> Optional[Langfuse]:
        """Get the Langfuse client instance."""
        instance = cls()
        return instance._langfuse
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Langfuse is configured and available."""
        return cls().get_instance() is not None
    
    @classmethod
    def start_trace(
        cls,
        trace_id: Optional[str] = None,
        name: str = "skill_execution",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Start a new trace.
        
        Args:
            trace_id: Optional trace ID (if None, auto-generated)
            name: Trace name
            session_id: Session identifier
            user_id: User identifier
            metadata: Additional metadata
            
        Returns:
            Trace ID if successful, None otherwise
        """
        client = cls.get_instance()
        if client is None:
            return None
        
        try:
            # Use provided trace_id or generate new one
            if not trace_id:
                import uuid
                trace_id = f"skill_trace_{uuid.uuid4().hex[:12]}"
            
            # Set context
            cls.set_trace_id(trace_id)
            
            # Optional: start trace in Langfuse
            # Note: Langfuse SDK 3.x handles this automatically
            
            return trace_id
            
        except Exception:
            return None
    
    @classmethod
    def end_trace(
        cls,
        status: str = "success",
        output: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        End current trace.
        
        Args:
            status: Trace status (success, error)
            output: Output data
            
        Returns:
            True if successful, False otherwise
        """
        client = cls.get_instance()
        if client is None:
            return False
        
        try:
            # Optional: explicit trace update
            # Langfuse SDK handles this automatically
            return True
            
        except Exception:
            return False
    
    @classmethod
    def score_trace(
        cls,
        name: str,
        value: Any,
        data_type: str = "NUMERIC",
        comment: Optional[str] = None,
    ) -> bool:
        """
        Add a score to the current trace.
        
        Args:
            name: Score name
            value: Score value
            data_type: Score data type (NUMERIC, BOOLEAN, CATEGORICAL)
            comment: Optional comment
            
        Returns:
            True if successful, False otherwise
        """
        client = cls.get_instance()
        if client is None:
            return False
        
        try:
            # Use context variable to get current trace
            from src.skill_observability_toolkit.stop.tracer import tracer_context
            
            trace_id = cls.get_trace_id()
            if not trace_id:
                return False
            
            # Get current span for scoring
            current_span = tracer_context.get_current_span()
            if current_span:
                # Apply score to span
                current_span.score(name, value, data_type, comment)
            
            return True
            
        except Exception:
            return False
    
    @classmethod
    def start_span(
        cls,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Start a new span.
        
        Args:
            name: Span name
            trace_id: Trace ID (if None, uses current context)
            parent_span_id: Parent span ID
            input_data: Input data
            metadata: Additional metadata
            
        Returns:
            Span context if successful, None otherwise
        """
        from src.skill_observability_toolkit.stop.tracer import tracer_context
        
        try:
            # Use current trace ID if not provided
            if not trace_id:
                trace_id = cls.get_trace_id()
            
            # Create span using tracer_context
            span = tracer_context.start_span(
                name=name,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                input_data=input_data,
                metadata=metadata,
            )
            
            return span
            
        except Exception:
            return None
    
    @classmethod
    def end_span(
        cls,
        span: Dict[str, Any],
        status: str = "success",
        output: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        End a span.
        
        Args:
            span: Span to end
            status: Span status
            output: Output data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from src.skill_observability_toolkit.stop.tracer import tracer_context
            tracer_context.end_span(span, status=status, output=output)
            return True
            
        except Exception:
            return False
    
    @classmethod
    def set_trace_id(cls, trace_id: str) -> None:
        """Set the current trace ID in context."""
        cls._trace_id_context.set(trace_id)
    
    @classmethod
    def get_trace_id(cls) -> Optional[str]:
        """Get the current trace ID from context."""
        return cls._trace_id_context.get()
    
    @classmethod
    def set_parent_trace_id(cls, parent_trace_id: str) -> None:
        """Set the parent trace ID for cross-layer correlation."""
        cls._parent_trace_id_context.set(parent_trace_id)
    
    @classmethod
    def get_parent_trace_id(cls) -> Optional[str]:
        """Get the parent trace ID."""
        return cls._parent_trace_id_context.get()
    
    @classmethod
    def clear_trace_context(cls) -> None:
        """Clear trace context."""
        cls._trace_id_context.set(None)
        cls._parent_trace_id_context.set(None)
