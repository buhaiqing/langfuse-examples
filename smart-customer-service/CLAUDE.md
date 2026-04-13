# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smart Customer Service System with Langfuse tracing and analytics - a production-grade LLM observability platform for customer service operations. Python backend (FastAPI) with React TypeScript frontend.

## Commands

### Backend (Python)
```bash
make setup          # Initial setup: create .env, install deps
make verify         # Verify API keys and configuration
make test           # Run pytest on backend/tests/
make test-cov       # Run tests with coverage report
make lint           # Run ruff linter
make format         # Format with black + ruff
make check-all      # lint + format + type-check + test

# Docker infrastructure
make docker-up      # Start Redis, PostgreSQL, ChromaDB, MinIO
make docker-down    # Stop containers
make db-migrate     # Run Alembic migrations

# Run from backend directory
uv run pytest backend/tests/test_file.py::TestClass::test_method -v
```

### Frontend (React/TypeScript)
```bash
cd frontend && npm run dev     # Start Vite dev server
cd frontend && npm run build   # TypeScript compile + Vite build
cd frontend && npm run lint    # ESLint
```

## Architecture

### Backend Structure (FastAPI)
- `backend/api/main.py` - Application entry point with middleware stack
- `backend/core/` - Infrastructure: config (Pydantic settings), Langfuse client, security (JWT, API key auth), exceptions
- `backend/services/` - Business logic: intent_recognition, rag_service, analytics, escalation_service
- `backend/storage/` - Data layer: Redis client (session cache), PostgreSQL, ChromaDB (vector search), MinIO (document storage)
- `backend/adapters/` - External system integrations

### Middleware Stack (order matters - first added executes last)
1. CORS (allow_origins from config)
2. RequestLoggingMiddleware (logs requests/responses)
3. APIKeyAuthMiddleware (X-API-Key header validation)
4. RateLimitMiddleware (sliding window rate limiting)

### Frontend Structure (React 19 + Vite)
- `frontend/src/App.tsx` - Root component with routing
- `frontend/src/components/` - Feature components (conversation-list, agent-status, quick-reply)
- `frontend/src/components/ui/` - 55 shadcn/ui base components
- `frontend/src/lib/api.ts` - REST API client
- `frontend/src/lib/websocket.ts` - WebSocket connection manager
- `frontend/src/hooks/use-agent-workstation.ts` - Agent state management

### Langfuse Tracing Pattern
```python
from core.langfuse_client import trace_customer_service, score_trace, Scores

@trace_customer_service(name="operation", session_id="sess_123", user_id="user_456")
async def handle_query(query: str):
    # Business logic automatically traced
    score_trace(Scores.INTENT_CONFIDENCE, 0.92)  # Attach metrics
    return result
```

### Predefined Scores (Scores class)
- `INTENT_CONFIDENCE`, `RETRIEVAL_RELEVANCE`, `TOOL_SUCCESS_RATE` (0-1 numeric)
- `ISSUE_RESOLVED`, `ESCALATION_REQUIRED` (boolean 0/1)
- `USER_SATISFACTION` (1-5 numeric)
- `FAILURE_TYPE` (categorical)

## Configuration

Environment variables via `.env` (copy from `.env.example`):
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` - Observability
- `OPENAI_API_KEY` - LLM provider
- `JWT_SECRET_KEY` (≥32 chars) - Auth
- `SERVICE_API_KEYS` (comma-separated) - Service-to-service auth
- `REDIS_URL`, `POSTGRES_URL`, `CHROMA_URL` - Data stores

Settings singleton: `from core.config import settings`

## Key Patterns

### PII Masking (automatic)
Langfuse client configured with global mask function. Sensitive fields (phone, email, id_card, password, api_key) are automatically redacted before tracing.

### Exception Handling
Use `core.exceptions` hierarchy with `ErrorCode` enum. Exceptions mapped to HTTP status codes via `api/middleware/exception_handlers.py`.

### WebSocket Handler
`api/websocket_handler.py` manages real-time chat with connection pooling, heartbeat (30s timeout), and message broadcasting.

### Testing
- Mock external dependencies (Langfuse, OpenAI, Redis) in all tests
- Use `conftest.py` fixtures for dependency injection
- Coverage: 90% overall, 95% critical paths