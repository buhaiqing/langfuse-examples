# Backend Development Standards

> **Purpose**: Python development standards for MCP Server backend  
> **Last Updated**: 2026-04-08

---

## 📋 Table of Contents

1. [Python Code Style](#1-python-code-style)
2. [Type Annotations](#2-type-annotations)
3. [Error Handling Standards](#3-error-handling-standards)
4. [Configuration Management](#4-configuration-management)
5. [Logging Standards](#5-logging-standards)
6. [Project Structure](#6-project-structure)

---

## 1. Python Code Style

### Mandatory Requirements

**Formatting Tools**:
- **Formatter**: `black` (line length: 100 characters)
- **Import Sorter**: `isort`
- **Linter**: `ruff`
- **Type Checker**: `mypy`

**Configuration**:
```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
```

### Rules

- ✅ ALWAYS use `black` for formatting
- ✅ ALWAYS use `isort` for import sorting
- ✅ ALWAYS pass `ruff` linter checks
- ❌ NEVER disable linter rules globally (only file-specific)
- ❌ NEVER commit code with formatting issues

---

## 2. Type Annotations

### Mandatory Pattern

```python
from typing import Dict, List, Optional, Any

def process_tool_call(
    tool_name: str,
    input_params: Dict[str, Any],
    session_id: str,
    user_id: str,
    prompt_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process an MCP tool call with full observability tracking.

    Args:
        tool_name: Name of the MCP tool to execute
        input_params: Input parameters for the tool
        session_id: Unique session identifier
        user_id: User identifier
        prompt_version: Optional prompt version for A/B testing

    Returns:
        Dictionary containing tool execution results

    Raises:
        ToolExecutionError: If tool execution fails
        ValidationError: If input parameters are invalid
    """
    # Implementation
    pass
```

### Rules

- ✅ ALL functions MUST have complete type annotations
- ✅ ALL public functions/classes MUST have docstrings (Google style)
- ✅ Use `Optional[T]` for optional parameters (not `T | None` in Python 3.9)
- ✅ Use `Dict[str, Any]` for flexible dictionaries
- ❌ NEVER use `Any` without justification
- ❌ NEVER skip return type annotations

---

## 3. Error Handling Standards

### Mandatory Pattern

```python
from observability.instrumentation import observe

class ObservabilityError(Exception):
    """Base exception for observability errors."""
    pass

class TraceSubmissionError(ObservabilityError):
    """Raised when trace submission to Langfuse fails."""
    pass

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass

@observe(name="process-request", as_type="span")
def process_request(request: dict) -> dict:
    """
    Process request with proper error handling and tracing.

    All exceptions are captured in traces automatically.
    """
    try:
        # Validate input
        if not request.get("session_id"):
            raise ValidationError("session_id is required")

        # Process request
        result = perform_operation(request)

        return {"success": True, "data": result}

    except ValidationError as e:
        # Validation errors are expected, log at INFO level
        logger.info(f"Validation failed: {e}")
        raise

    except TraceSubmissionError as e:
        # Observability errors should not fail the operation
        logger.error(f"Failed to submit trace: {e}")
        # Continue execution - graceful degradation
        return perform_operation_without_tracing(request)

    except Exception as e:
        # Unexpected errors must be captured and re-raised
        logger.exception(f"Unexpected error processing request: {e}")
        raise
```

### Rules

- ✅ ALWAYS catch specific exceptions before generic `Exception`
- ✅ ALWAYS log exceptions with context
- ✅ ALWAYS re-raise exceptions unless graceful degradation is intentional
- ❌ NEVER use bare `except:` clauses
- ❌ NEVER suppress exceptions silently
- ❌ NEVER catch `BaseException` (includes KeyboardInterrupt)

---

## 4. Configuration Management

### Mandatory Pattern

```python
from pydantic import BaseSettings, Field
from typing import Optional

class ObservabilityConfig(BaseSettings):
    """Configuration for Langfuse observability platform."""

    # Langfuse connection settings
    langfuse_public_key: str = Field(..., env="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(..., env="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        env="LANGFUSE_HOST"
    )

    # Observability settings
    enabled: bool = Field(default=True, env="OBSERVABILITY_ENABLED")
    sample_rate: float = Field(default=1.0, env="TRACE_SAMPLE_RATE")
    flush_interval: int = Field(default=10, env="LANGFUSE_FLUSH_INTERVAL")

    # Performance thresholds
    success_rate_threshold: float = Field(default=0.99)
    latency_p95_threshold_ms: int = Field(default=500)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Global config instance
_config: Optional[ObservabilityConfig] = None

def get_config() -> ObservabilityConfig:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = ObservabilityConfig()
    return _config
```

### Rules

- ✅ ALWAYS use environment variables for secrets
- ✅ ALWAYS provide sensible defaults
- ✅ ALWAYS validate configuration at startup
- ❌ NEVER hardcode secrets or credentials
- ❌ NEVER commit `.env` files to version control

---

## 5. Logging Standards

### Mandatory Pattern

```python
import structlog
from typing import Any, Dict

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

def log_tool_call(
    tool_name: str,
    session_id: str,
    user_id: str,
    duration_ms: float,
    success: bool,
    error: Optional[str] = None
) -> None:
    """
    Log tool call with structured logging.

    Args:
        tool_name: Name of the tool
        session_id: Session identifier
        user_id: User identifier
        duration_ms: Execution duration in milliseconds
        success: Whether the call succeeded
        error: Error message if failed
    """
    log_data: Dict[str, Any] = {
        "event": "tool_call",
        "tool_name": tool_name,
        "session_id": session_id,
        "user_id": user_id,
        "duration_ms": duration_ms,
        "success": success,
    }

    if error:
        log_data["error"] = error
        logger.error("Tool call failed", **log_data)
    else:
        logger.info("Tool call completed", **log_data)
```

### Rules

- ✅ ALWAYS use structured logging (JSON format)
- ✅ ALWAYS include context (session_id, user_id, tool_name)
- ✅ ALWAYS use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- ❌ NEVER log sensitive data (passwords, API keys, PII)
- ❌ NEVER use print() statements in production code
- ❌ NEVER log entire request/response payloads without size limits

---

## 6. Project Structure

### Mandatory Directory Layout

```
src/
├── observability/
│   ├── __init__.py
│   ├── instrumentation.py    # Core instrumentation decorators
│   ├── session.py             # Session context management
│   ├── prompt_versioning.py   # Prompt version tracking
│   ├── feedback.py            # Feedback collection
│   └── alerting.py            # Alerting configuration
├── tools/
│   ├── __init__.py
│   ├── base_tool.py           # Base tool class
│   └── implementations/       # Tool implementations
└── config/
    ├── __init__.py
    └── settings.py            # Configuration management
```

---

## Code Review Checklist

Before submitting code for review:

- [ ] Code formatted with `black` and `isort`
- [ ] All linter checks pass (`ruff`)
- [ ] Type checks pass (`mypy`)
- [ ] All functions have type annotations
- [ ] All public functions have docstrings
- [ ] Error handling follows patterns
- [ ] No hardcoded secrets
- [ ] Logging uses structured format

---

**Related Documentation**:
- [Integration Patterns](integration-patterns.md) - Langfuse integration examples
- [Testing Guide](testing-guide.md) - Testing standards
- [Security Guide](security-guide.md) - Security requirements