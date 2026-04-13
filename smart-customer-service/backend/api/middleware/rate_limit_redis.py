"""
速率限制中间件 - Redis 实现

使用 Redis Sorted Set 实现滑动窗口限流算法，支持分布式限流
"""

import time
from typing import Optional, Tuple

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.config import settings
from core.langfuse_client import langfuse_client
from storage.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """基于 Redis 的速率限制中间件"""

    def __init__(self, app, excluded_paths: Optional[set] = None):
        """
        初始化限流中间件

        Args:
            app: FastAPI 应用
            excluded_paths: 不需要限流的路径集合
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or {"/health", "/docs", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        """处理请求限流"""
        # 跳过不需要限流的路径
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # 开始 Langfuse 追踪
        start_time = time.time()

        with langfuse_client.trace().span(name="rate_limiting") as rate_limit_span:
            # 获取客户端标识
            client_id = self._get_client_id(request)

            # 检查限流
            is_allowed, retry_after = await self._check_rate_limit(client_id)

            if not is_allowed:
                rate_limit_span.end(
                    output_data={
                        "success": False,
                        "reason": "rate_limit_exceeded",
                        "retry_after": retry_after,
                    }
                )

                logger.warning(f"限流触发：client={client_id}, retry_after={retry_after}s")

                # 记录限流事件
                langfuse_client.trace().score(
                    name="rate_limit_exceeded", value=1.0, comment="请求超过速率限制"
                )

                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": "Too Many Requests",
                        "message": "Rate limit exceeded. Please try again later.",
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            # 限流检查通过
            rate_limit_span.end(output_data={"success": True, "client_id": client_id})

            # 记录限流检查延迟
            latency_ms = (time.time() - start_time) * 1000
            langfuse_client.trace().score(
                name="rate_limit_latency_ms", value=latency_ms, comment="限流检查延迟"
            )

            # 继续处理请求
            response = await call_next(request)

            return response

    def _get_client_id(self, request: Request) -> str:
        """
        获取客户端标识

        优先使用 API Key，其次使用 IP 地址
        """
        api_key = getattr(request.state, "api_key_raw", None)
        if api_key:
            return f"key:{api_key}"

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    async def _check_rate_limit(self, client_id: str) -> Tuple[bool, int]:
        """
        检查是否超过速率限制（使用 Redis）

        Args:
            client_id: 客户端标识

        Returns:
            Tuple[bool, int]: (是否允许，重试等待秒数)
        """
        try:
            return await redis_client.check_rate_limit(
                client_id,
                settings.rate_limit_requests,
                settings.rate_limit_seconds,
            )
        except Exception as e:
            logger.error(f"Redis 限流检查失败：{e}")
            # Redis 失败时放行，避免影响正常服务
            return True, 0


# 限流装饰器
def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """
    速率限制装饰器（用于特定路由）

    Args:
        max_requests: 最大请求数
        window_seconds: 时间窗口（秒）

    Returns:
        装饰器函数
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # TODO: 实现装饰器限流逻辑
            return await func(*args, **kwargs)

        return wrapper

    return decorator


@lru_cache
def get_rate_limit_config() -> Tuple[int, int]:
    """获取限流配置"""
    return settings.rate_limit_requests, settings.rate_limit_seconds
