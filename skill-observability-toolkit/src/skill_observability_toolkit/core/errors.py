"""
Structured Error Handling for Tracing Operations.

This module provides a comprehensive error handling system with:
- Error codes for programmatic handling
- Structured error context for debugging
- Error hierarchy for proper exception management
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TracingErrorCode(str, Enum):
    """
    Error codes for tracing operations.
    
    These codes enable programmatic error handling and monitoring.
    """
    
    # Langfuse Integration Errors
    LANGFUSE_UNAVAILABLE = "LANGFUSE_UNAVAILABLE"
    LANGFUSE_NOT_CONFIGURED = "LANGFUSE_NOT_CONFIGURED"
    LANGFUSE_API_ERROR = "LANGFUSE_API_ERROR"
    
    # Trace Context Errors
    TRACE_CONTEXT_NOT_INITIALIZED = "TRACE_CONTEXT_NOT_INITIALIZED"
    TRACE_ID_MISSING = "TRACE_ID_MISSING"
    SPAN_CONTEXT_CORRUPTED = "SPAN_CONTEXT_CORRUPTED"
    
    # Span Operation Errors
    SPAN_PROPAGATION_FAILED = "SPAN_PROPAGATION_FAILED"
    SPAN_ALREADY_ENDED = "SPAN_ALREADY_ENDED"
    INVALID_SPAN_OPERATION = "INVALID_SPAN_OPERATION"
    
    # Scoring Errors
    SCORE_VALIDATION_FAILED = "SCORE_VALIDATION_FAILED"
    INVALID_SCORE_TYPE = "INVALID_SCORE_TYPE"
    SCORE_VALUE_OUT_OF_RANGE = "SCORE_VALUE_OUT_OF_RANGE"
    
    # Manifest Errors
    MANIFEST_VALIDATION_FAILED = "MANIFEST_VALIDATION_FAILED"
    MANIFEST_PARSE_ERROR = "MANIFEST_PARSE_ERROR"
    MANIFEST_FILE_NOT_FOUND = "MANIFEST_FILE_NOT_FOUND"
    
    # Assertion Errors
    ASSERTION_EXECUTION_FAILED = "ASSERTION_EXECUTION_FAILED"
    ASSERTION_SYNTAX_ERROR = "ASSERTION_SYNTAX_ERROR"
    ASSERTION_CHECK_NOT_FOUND = "ASSERTION_CHECK_NOT_FOUND"
    
    # Configuration Errors
    CONFIG_VALIDATION_FAILED = "CONFIG_VALIDATION_FAILED"
    CONFIG_MISSING_FIELD = "CONFIG_MISSING_FIELD"
    
    # Export Errors
    EXPORT_FAILED = "EXPORT_FAILED"
    EXPORT_TIMEOUT = "EXPORT_TIMEOUT"
    
    # General Errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    FEATURE_NOT_IMPLEMENTED = "FEATURE_NOT_IMPLEMENTED"


@dataclass
class TracingError(Exception):
    """
    Structured error for tracing operations.
    
    Provides rich context for debugging and monitoring.
    
    Attributes:
        code: Error code for programmatic handling
        message: Human-readable error message
        context: Additional context (trace_id, span_id, operation, etc.)
        original_exception: Wrapped exception if any
        timestamp: Error occurrence timestamp (auto-generated)
        
    Example:
        >>> from skill_observability_toolkit.core.errors import TracingError, TracingErrorCode
        >>> try:
        ...     # Some operation
        ...     raise ValueError("Invalid input")
        ... except Exception as e:
        ...     raise TracingError(
        ...         code=TracingErrorCode.SCORE_VALIDATION_FAILED,
        ...         message="Failed to score trace 'execution_time'",
        ...         context={
        ...             "trace_id": "trace_123",
        ...             "span_id": "span_456",
        ...             "operation": "score_trace",
        ...             "score_name": "execution_time",
        ...             "score_value": 123.45
        ...         },
        ...         original_exception=e
        ...     )
    """
    
    code: TracingErrorCode
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    original_exception: Exception | None = None
    
    def __post_init__(self):
        """Validate error structure."""
        if not isinstance(self.code, TracingErrorCode):
            raise ValueError(
                f"Error code must be TracingErrorCode, got {type(self.code).__name__}"
            )
        
        if not self.message:
            raise ValueError("Error message cannot be empty")
    
    @classmethod
    def from_exception(
        cls,
        code: TracingErrorCode,
        exception: Exception,
        message: str = "",
        context: dict[str, Any] | None = None,
    ) -> "TracingError":
        """
        Create TracingError from an existing exception.
        
        Args:
            code: Error code
            exception: Original exception to wrap
            message: Optional custom message (uses exception message if not provided)
            context: Optional context dictionary
            
        Returns:
            TracingError instance
        """
        return cls(
            code=code,
            message=message or str(exception),
            context=context or {},
            original_exception=exception,
        )
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convert error to dictionary for logging/monitoring.
        
        Returns:
            Dictionary with error details
        """
        result = {
            "error_code": self.code.value,
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context.copy(),
        }
        
        # Include original exception details if present
        if self.original_exception:
            result["original_exception"] = {
                "type": type(self.original_exception).__name__,
                "message": str(self.original_exception),
            }
        
        return result
    
    def __str__(self) -> str:
        """String representation for logging."""
        context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
        
        if context_str:
            return f"[{self.code.value}] {self.message} ({context_str})"
        else:
            return f"[{self.code.value}] {self.message}"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"TracingError(code={self.code.value}, "
            f"message={self.message!r}, "
            f"original_exception={type(self.original_exception).__name__ if self.original_exception else None})"
        )


# Backward compatibility: Keep existing exception types
class ManifestError(Exception):
    """Base class for manifest-related errors (backward compatible)."""
    pass


class ManifestParseError(ManifestError):
    """Error parsing the manifest file (backward compatible)."""
    pass


class ManifestValidationError(ManifestError):
    """Error validating the manifest structure (backward compatible)."""
    pass


class AssertionError(Exception):
    """Base exception for assertion errors (backward compatible)."""
    pass


class AssertionExecutionError(AssertionError):
    """Error executing an assertion (backward compatible)."""
    pass


class AssertionSyntaxError(AssertionError):
    """Syntax error in assertion definition (backward compatible)."""
    pass


# Legacy exception mapping
# These can be used if code still imports old exceptions
LEGACY_EXCEPTION_MAP = {
    "ManifestError": ManifestError,
    "ManifestParseError": ManifestParseError,
    "ManifestValidationError": ManifestValidationError,
    "AssertionError": AssertionError,
    "AssertionExecutionError": AssertionExecutionError,
    "AssertionSyntaxError": AssertionSyntaxError,
}
