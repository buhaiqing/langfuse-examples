"""
速率限制中间件

基于 Redis 实现令牌桶限流算法，防止 API 滥用
"""

import time
from typing import Optional, Dict, Tuple
from functools import lru_cache

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.config import settings
from core.langfuse_client import langfuse_client
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件 - 基于滑动窗口计数"""

    def __init__(self, app, excluded_paths: Optional[set] = None):
        """
        初始化限流中间件

        Args:
            app: FastAPI 应用
            excluded_paths: 不需要限流的路径集合
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or {"/health", "/docs", "/redoc"}
        # 内存中的限流计数器（生产环境应使用 Redis）
        self._request_counts: Dict[str, Tuple[int, float]] = {}

    async def dispatch(self, request: Request, call_next):
        """处理请求限流"""

        # 跳过不需要限流的路径
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # 开始 Langfuse 追踪
        start_time = time.time()

        with langfuse_client.trace().span(name="rate_limiting") as rate_limit_span:
            # 获取客户端标识（IP 地址或 API Key）
            client_id = self._get_client_id(request)

            # 检查限流
            is_allowed, retry_after = self._check_rate_limit(client_id)

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
        # 如果请求中有 API Key，使用 API Key 作为标识
        api_key = getattr(request.state, "api_key_raw", None)
        if api_key:
            return f"key:{api_key}"

        # 使用 IP 地址
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    def _check_rate_limit(self, client_id: str) -> Tuple[bool, int]:
        """
        检查是否超过速率限制

        使用滑动窗口计数算法

        Args:
            client_id: 客户端标识

        Returns:
            Tuple[bool, int]: (是否允许，重试等待秒数)
        """
        current_time = time.time()
        window_size = settings.rate_limit_seconds  # 时间窗口（秒）
        max_requests = settings.rate_limit_requests  # 最大请求数

        # 获取客户端的请求记录
        if client_id in self._request_counts:
            count, window_start = self._request_counts[client_id]

            # 检查是否在新的时间窗口
            if current_time - window_start > window_size:
                # 新窗口，重置计数器
                self._request_counts[client_id] = (1, current_time)
                return True, 0

            # 检查是否超过限制
            if count >= max_requests:
                # 计算需要等待的时间
                retry_after = int(window_start + window_size - current_time) + 1
                return False, retry_after

            # 更新计数器
            self._request_counts[client_id] = (count + 1, window_start)
        else:
            # 新客户端，创建记录
            self._request_counts[client_id] = (1, current_time)

        return True, 0

    def cleanup_old_entries(self):
        """清理过期的限流记录（定期调用）"""
        current_time = time.time()
        window_size = settings.rate_limit_seconds

        # 删除超过 2 个时间窗口的记录
        cutoff_time = current_time - (window_size * 2)
        self._request_counts = {
            client_id: (count, window_start)
            for client_id, (count, window_start) in self._request_counts.items()
            if window_start > cutoff_time
        }


# 限流装饰器（用于特定路由的限流）
def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """
    速率限制装饰器

    Args:
        max_requests: 最大请求数
        window_seconds: 时间窗口（秒）

    Returns:
        装饰器函数
    """
    # 这里可以扩展实现更细粒度的限流逻辑
    pass


@lru_cache
def get_rate_limit_config() -> Tuple[int, int]:
    """获取限流配置"""
    return settings.rate_limit_requests, settings.rate_limit_seconds
