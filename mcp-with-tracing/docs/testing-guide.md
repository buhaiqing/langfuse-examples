# Testing Guide

> **Purpose**: Testing standards and best practices  
> **Last Updated**: 2026-04-08

---

## Coverage Requirements

- **Overall**: Minimum 90%
- **Critical Paths**: Minimum 95%
- **New Code**: Minimum 95%

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

# Run specific tests
pytest tests/unit/observability/test_instrumentation.py -v
```

---

**See Full Documentation**: Test structure, mocking patterns, integration tests, E2E tests, CI/CD automation.
