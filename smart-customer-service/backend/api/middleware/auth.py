"""
API Key 认证中间件

实现基于 API Key 的请求认证，支持多密钥轮换和密钥掩码日志
"""

import time
from typing import Optional, Set
from functools import lru_cache

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.config import settings
from core.langfuse_client import langfuse_client
import logging

logger = logging.getLogger(__name__)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """API Key 认证中间件"""

    def __init__(self, app, excluded_paths: Optional[Set[str]] = None):
        """
        初始化认证中间件

        Args:
            app: FastAPI 应用
            excluded_paths: 不需要认证的路径集合，如 {'/health', '/docs'}
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or {"/health", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next):
        """处理请求认证"""

        # 跳过不需要认证的路径
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # 开始 Langfuse 追踪
        start_time = time.time()

        with langfuse_client.trace().span(name="authentication") as auth_span:
            # 获取 API Key
            api_key = request.headers.get(settings.api_key_header)

            if not api_key:
                auth_span.end(output_data={"success": False, "reason": "missing_api_key"})
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "success": False,
                        "error": "Unauthorized",
                        "message": f"Missing API key. Please provide '{settings.api_key_header}' header.",
                    },
                )

            # 验证 API Key
            is_valid = self._validate_api_key(api_key)

            if not is_valid:
                auth_span.end(output_data={"success": False, "reason": "invalid_api_key"})
                logger.warning(f"无效的 API Key 尝试：{self._mask_api_key(api_key)}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "success": False,
                        "error": "Unauthorized",
                        "message": "Invalid API key.",
                    },
                )

            # 认证通过，将 API Key 信息存入请求状态
            request.state.api_key = self._mask_api_key(api_key)
            request.state.api_key_raw = api_key  # 供内部服务使用

            auth_span.end(
                output_data={
                    "success": True,
                    "api_key": self._mask_api_key(api_key),
                }
            )

            # 继续处理请求
            response = await call_next(request)

            # 记录认证延迟
            latency_ms = (time.time() - start_time) * 1000
            langfuse_client.trace().score(
                name="auth_latency_ms", value=latency_ms, comment="API Key 认证延迟"
            )

            return response

    def _validate_api_key(self, api_key: str) -> bool:
        """验证 API Key 是否有效"""
        return api_key in settings.service_api_keys

    def _mask_api_key(self, api_key: str) -> str:
        """
        掩码 API Key 用于日志

        示例：sk-prod-abc123xyz789 → sk-prod***
        """
        if len(api_key) <= 8:
            return "***"
        return f"{api_key[:7]}***"


# 辅助函数
@lru_cache
def get_valid_api_keys() -> Set[str]:
    """获取有效的 API Keys 集合"""
    return set(settings.service_api_keys)


def verify_api_key(api_key: Optional[str]) -> bool:
    """
    验证 API Key

    Args:
        api_key: 待验证的 API Key

    Returns:
        bool: 是否有效
    """
    if not api_key:
        return False
    return api_key in get_valid_api_keys()


def mask_api_key(api_key: str) -> str:
    """掩码 API Key 用于日志"""
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:7]}***"
