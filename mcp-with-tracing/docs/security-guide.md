# Security Guide

> **Purpose**: Security requirements and patterns  
> **Last Updated**: 2026-04-08

---

## Secrets Management

```python
import os

def get_secret_key() -> str:
    key = os.getenv("LANGFUSE_SECRET_KEY")
    if not key:
        raise ValueError("LANGFUSE_SECRET_KEY not set")
    return key
```

## PII Handling

```python
import re

PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
}

def redact_pii(text: str) -> str:
    redacted = text
    for pii_type, pattern in PII_PATTERNS.items():
        redacted = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", redacted)
    return redacted
```

## Rules

- ✅ ALWAYS use environment variables for secrets
- ✅ ALWAYS redact PII before logging
- ✅ ALWAYS validate inputs with Pydantic
- ❌ NEVER commit secrets to git
- ❌ NEVER log passwords or API keys

---

**See Full Documentation**: Input validation, authentication, authorization, security scanning.
