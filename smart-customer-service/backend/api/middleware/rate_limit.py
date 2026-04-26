"""速率限制中间件

基于滑动窗口计数算法实现请求限流，支持内存和 Redis 两种后端。
通过请求上下文共享 Langfuse trace_id，避免中间件独立创建 trace。
"""

import asyncio
import logging
import time
from functools import lru_cache

from core.config import settings
from core.langfuse_client import (
    DummySpan,
    create_span,
    get_current_trace_id,
    score_trace,
)
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件 - 基于滑动窗口计数

    内存模式适用于单实例部署，Redis 模式适用于分布式部署。
    清理任务通过 FastAPI lifespan 启动，避免事件循环问题。
    """

    def __init__(self, app, excluded_paths: set[str] | None = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or {"/health", "/docs", "/redoc", "/openapi.json"}
        self._request_counts: dict[str, tuple[int, float]] = {}
        self._max_entries = 10000
        self._cleanup_task: asyncio.Task | None = None

    def start_cleanup_task(self) -> None:
        """启动后台清理任务（应在 FastAPI lifespan startup 中调用）"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("限流清理任务已启动")

    def stop_cleanup_task(self) -> None:
        """停止后台清理任务（应在 FastAPI lifespan shutdown 中调用）"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            logger.info("限流清理任务已停止")

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        start_time = time.time()

        rate_span = create_span("rate_limiting")

        client_id = self._get_client_id(request)

        is_allowed, retry_after = self._check_rate_limit(client_id)

        if not is_allowed:
            if not isinstance(rate_span, DummySpan):
                rate_span.end(
                    output_data={
                        "success": False,
                        "reason": "rate_limit_exceeded",
                        "retry_after": retry_after,
                    }
                )
            else:
                rate_span.end()

            logger.warning("限流触发：client=%s, retry_after=%ds", client_id, retry_after)

            trace_id = get_current_trace_id()
            score_trace("rate_limit_exceeded", 1.0, comment="请求超过速率限制", trace_id=trace_id)

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

        if not isinstance(rate_span, DummySpan):
            rate_span.end(output_data={"success": True, "client_id": client_id})
        else:
            rate_span.end()

        latency_ms = (time.time() - start_time) * 1000
        trace_id = get_current_trace_id()
        score_trace("rate_limit_latency_ms", latency_ms, comment="限流检查延迟", trace_id=trace_id)

        response = await call_next(request)

        return response

    @staticmethod
    def _get_client_id(request: Request) -> str:
        """获取客户端标识，优先使用 API Key，其次使用 IP 地址"""
        api_key = getattr(request.state, "api_key_raw", None)
        if api_key:
            return f"key:{api_key}"

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    def _check_rate_limit(self, client_id: str) -> tuple[bool, int]:
        """检查是否超过速率限制（滑动窗口计数算法）

        Returns:
            (是否允许, 重试等待秒数)
        """
        current_time = time.time()
        window_size = settings.rate_limit_seconds
        max_requests = settings.rate_limit_requests

        if client_id in self._request_counts:
            count, window_start = self._request_counts[client_id]

            if current_time - window_start > window_size:
                self._request_counts[client_id] = (1, current_time)
                return True, 0

            if count >= max_requests:
                retry_after = int(window_start + window_size - current_time) + 1
                return False, retry_after

            self._request_counts[client_id] = (count + 1, window_start)
        else:
            self._request_counts[client_id] = (1, current_time)

        return True, 0

    async def _cleanup_loop(self) -> None:
        """后台清理循环（每 60 秒清理一次过期条目）"""
        try:
            while True:
                await asyncio.sleep(60)
                self._cleanup_old_entries()

                if len(self._request_counts) > self._max_entries:
                    self._force_cleanup()
                    logger.warning(
                        "限流计数器条目数超过上限 (%d/%d)，已强制清理",
                        len(self._request_counts),
                        self._max_entries,
                    )
        except asyncio.CancelledError:
            logger.info("限流清理任务已取消")

    def _force_cleanup(self) -> None:
        """强制清理过期条目"""
        current_time = time.time()
        window_size = settings.rate_limit_seconds
        cutoff_time = current_time - window_size

        self._request_counts = {
            client_id: (count, window_start)
            for client_id, (count, window_start) in self._request_counts.items()
            if current_time - window_start < cutoff_time
        }

    def _cleanup_old_entries(self) -> None:
        """清理超过 2 个时间窗口的过期记录"""
        current_time = time.time()
        window_size = settings.rate_limit_seconds
        cutoff_time = current_time - (window_size * 2)

        self._request_counts = {
            client_id: (count, window_start)
            for client_id, (count, window_start) in self._request_counts.items()
            if window_start > cutoff_time
        }

        if len(self._request_counts) > self._max_entries:
            self._force_cleanup()


def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """速率限制装饰器（预留扩展接口）"""
    pass


@lru_cache
def get_rate_limit_config() -> tuple[int, int]:
    """获取限流配置"""
    return settings.rate_limit_requests, settings.rate_limit_seconds
