# Testing Guide

> **Purpose**: Testing standards and best practices  
> **Last Updated**: 2026-04-13

---

## Coverage Requirements

- **Overall**: Minimum 90%
- **Critical Paths**: Minimum 95%
- **New Code**: Minimum 95%

## Test Structure

### Unit Tests (`tests/`)

Test individual components in isolation:

- `test_feedback.py` - Feedback collection logic
- `test_instrumentation.py` - Observability instrumentation
- `test_prompt_versioning.py` - Prompt version management
- `test_session.py` - Session management
- `test_feedback_tools_integration.py` - MCP feedback tools integration ✨

### Integration Tests (`scripts/`)

End-to-end integration tests:

- `test_feedback_integration.py` - Complete feedback tools integration ✨
- `test_session_tracing.py` - Session tracing end-to-end
- `test_prompt_versioning.py` - Prompt versioning queries
- `test_success_failure_tracking.py` - Success/failure metrics

## Unit Test Pattern

```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_langfuse_client():
    with patch('observability.instrumentation.get_client') as mock:
        client = Mock()
        mock.return_value = client
        yield client

class TestInstrumentation:
    def test_observe_decorator_creates_span(self, mock_langfuse_client):
        @observe(name="test-tool")
        def test_function(x: int) -> int:
            return x * 2
        
        result = test_function(5)
        assert result == 10
```

## Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_feedback_tools_integration.py -v

# Run integration test script
python scripts/test_feedback_integration.py

# Run all tests with verbose output
pytest -v

# Run only unit tests (exclude example2)
pytest tests/ -v --ignore=tests/test_instrumentation.py
```

---

**See Full Documentation**: Test structure, mocking patterns, integration tests, E2E tests, CI/CD automation.
