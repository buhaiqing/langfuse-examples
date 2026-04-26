"""
核心模块

提供:
- 配置管理
- Langfuse 客户端
- 安全认证
- 异常处理
- LLM 客户端池
"""

from core.config import Settings, settings
from core.exceptions import (
    AuthenticationException,
    BusinessException,
    ErrorCode,
    RateLimitException,
    ServiceUnavailableException,
    ValidationException,
)
from core.langfuse_client import (
    Scores,
    create_span,
    langfuse_client,
    score_trace,
    trace_customer_service,
)
from core.llm_client_pool import (
    EmbeddingClientConfig,
    LLMClientConfig,
    LLMClientPool,
    LLMResponseCache,
    RateLimiter,
    call_embedding_with_rate_limit,
    call_llm_with_rate_limit,
    get_chat_client,
    get_embedding_client,
    get_llm_pool,
    with_llm_rate_limit,
)
from core.security import (
    create_access_token,
    get_current_user,
)

__all__ = [
    # 配置
    "settings",
    "Settings",
    # Langfuse
    "trace_customer_service",
    "score_trace",
    "Scores",
    "langfuse_client",
    "create_span",
    # 安全
    "create_access_token",
    "verify_token",
    "get_current_user",
    "APIKeyAuth",
    # 异常
    "ErrorCode",
    "BusinessException",
    "ValidationException",
    "AuthenticationException",
    "RateLimitException",
    "ServiceUnavailableException",
    # LLM 客户端池
    "LLMClientConfig",
    "EmbeddingClientConfig",
    "RateLimiter",
    "LLMResponseCache",
    "LLMClientPool",
    "get_llm_pool",
    "get_chat_client",
    "get_embedding_client",
    "call_llm_with_rate_limit",
    "call_embedding_with_rate_limit",
    "with_llm_rate_limit",
]
