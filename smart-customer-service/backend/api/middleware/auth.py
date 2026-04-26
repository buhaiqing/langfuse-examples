"""API Key 认证中间件

实现基于 API Key 的请求认证，支持多密钥轮换和密钥掩码日志。
通过请求上下文共享 Langfuse trace_id，避免中间件独立创建 trace。
"""

import logging
import time

from core.config import settings
from core.langfuse_client import (
    DummySpan,
    create_span,
    get_current_trace_id,
    langfuse_client,
)
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """API Key 认证中间件

    在请求入口创建 Langfuse trace 并将 trace_id 注入请求上下文，
    后续中间件和路由通过 get_current_trace_id() 共享同一 trace。
    """

    def __init__(self, app, excluded_paths: set[str] | None = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or {"/health", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        start_time = time.time()

        auth_span = create_span("authentication")

        api_key = request.headers.get(settings.api_key_header)

        if not api_key:
            if not isinstance(auth_span, DummySpan):
                auth_span.end(output_data={"success": False, "reason": "missing_api_key"})
            else:
                auth_span.end()
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": "Unauthorized",
                    "message": (
                        f"Missing API key. Please provide '{settings.api_key_header}' header."
                    ),
                },
            )

        is_valid = self._validate_api_key(api_key)

        if not is_valid:
            if not isinstance(auth_span, DummySpan):
                auth_span.end(output_data={"success": False, "reason": "invalid_api_key"})
            else:
                auth_span.end()
            logger.warning("无效的 API Key 尝试：%s", self._mask_api_key(api_key))
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": "Unauthorized",
                    "message": "Invalid API key.",
                },
            )

        request.state.api_key = self._mask_api_key(api_key)
        request.state.api_key_raw = api_key

        if not isinstance(auth_span, DummySpan):
            auth_span.end(output_data={"success": True, "api_key": self._mask_api_key(api_key)})
        else:
            auth_span.end()

        response = await call_next(request)

        latency_ms = (time.time() - start_time) * 1000
        trace_id = get_current_trace_id()
        if trace_id and langfuse_client.is_enabled():
            try:
                langfuse_client.client.trace(id=trace_id).score(
                    name="auth_latency_ms", value=latency_ms, comment="API Key 认证延迟"
                )
            except Exception:
                pass

        return response

    @staticmethod
    def _validate_api_key(api_key: str) -> bool:
        """验证 API Key 是否有效"""
        return api_key in settings.service_api_keys

    @staticmethod
    def _mask_api_key(api_key: str) -> str:
        """掩码 API Key 用于日志（sk-prod-abc123xyz789 → sk-prod***）"""
        if len(api_key) <= 8:
            return "***"
        return f"{api_key[:7]}***"


def verify_api_key(api_key: str | None) -> bool:
    """验证 API Key"""
    if not api_key:
        return False
    return api_key in set(settings.service_api_keys)


def mask_api_key(api_key: str) -> str:
    """掩码 API Key 用于日志"""
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:7]}***"
