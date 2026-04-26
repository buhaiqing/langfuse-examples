"""
请求日志中间件

功能：
- 记录所有 API 请求和响应
- 生成唯一请求 ID 用于追踪
- 敏感信息脱敏
- JSON 格式日志输出
- 记录请求耗时
"""

import json
import logging
import time
import uuid
from typing import Any

from core.config import settings
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("api.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件

    记录每个请求的详细信息，包括：
    - 请求 ID（用于链路追踪）
    - 请求方法、路径、查询参数
    - 请求头（脱敏后）
    - 响应状态码
    - 请求耗时
    - 客户端 IP
    """

    # 敏感字段，需要脱敏
    SENSITIVE_FIELDS: set[str] = {
        "authorization",
        "x-api-key",
        "api-key",
        "password",
        "token",
        "secret",
        "credential",
        "cookie",
    }

    # 敏感请求体字段
    SENSITIVE_BODY_FIELDS: set[str] = {
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "credential",
        "access_token",
        "refresh_token",
    }

    def __init__(
        self,
        app: ASGIApp,
        excluded_paths: set[str] | None = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
    ):
        super().__init__(app)
        self.excluded_paths = excluded_paths or {
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        }
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

    async def dispatch(self, request: Request, call_next) -> Response:
        """处理请求"""
        start_time = time.time()

        # 生成请求 ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 获取客户端信息
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # 记录请求开始
        request_log = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": client_ip,
            "user_agent": user_agent,
        }

        # 如果不是排除路径，添加详细请求信息
        if request.url.path not in self.excluded_paths:
            request_log["headers"] = self._sanitize_headers(dict(request.headers))

            # 记录请求体（如果启用）
            if self.log_request_body and request.method in ("POST", "PUT", "PATCH"):
                body = await self._get_request_body(request)
                if body:
                    request_log["body"] = self._sanitize_body(body)

        try:
            # 继续处理请求
            response = await call_next(request)

            # 计算处理时间
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # 添加响应信息
            request_log.update(
                {
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            )

            # 设置请求 ID 到响应头
            response.headers["X-Request-ID"] = request_id

            # 记录响应体（如果启用且不是排除路径）
            if self.log_response_body and request.url.path not in self.excluded_paths:
                response_body = await self._get_response_body(response)
                if response_body:
                    request_log["response_body"] = self._truncate_string(response_body, 1000)

            # 根据状态码确定日志级别
            if response.status_code >= 500:
                logger.error(json.dumps(request_log, ensure_ascii=False))
            elif response.status_code >= 400:
                logger.warning(json.dumps(request_log, ensure_ascii=False))
            else:
                logger.info(json.dumps(request_log, ensure_ascii=False))

            return response

        except Exception as e:
            # 记录异常
            duration_ms = round((time.time() - start_time) * 1000, 2)
            request_log.update(
                {
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "error": str(e),
                }
            )
            logger.error(json.dumps(request_log, ensure_ascii=False))
            raise

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        # 优先从 X-Forwarded-For 获取（支持反向代理）
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # 其次从 X-Real-IP 获取
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # 最后从直接连接获取
        if request.client:
            return request.client.host

        return "unknown"

    def _sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """脱敏请求头"""
        sanitized = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in self.SENSITIVE_FIELDS:
                sanitized[key] = self._mask_sensitive_value(value)
            else:
                sanitized[key] = value
        return sanitized

    def _sanitize_body(self, body: Any) -> Any:
        """脱敏请求体"""
        if isinstance(body, dict):
            sanitized = {}
            for key, value in body.items():
                if key.lower() in self.SENSITIVE_BODY_FIELDS:
                    sanitized[key] = self._mask_sensitive_value(str(value))
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_body(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(body, list):
            return [
                self._sanitize_body(item) if isinstance(item, (dict, list)) else item
                for item in body
            ]
        return body

    def _mask_sensitive_value(self, value: str, visible_chars: int = 4) -> str:
        """
        脱敏敏感值

        Args:
            value: 原始值
            visible_chars: 保留的可见字符数

        Returns:
            脱敏后的值，如：sk-***、Bearer ***
        """
        if not value or len(value) <= visible_chars:
            return "***"

        # 对于 Bearer token，保留前缀
        if value.lower().startswith("bearer "):
            return f"Bearer {value[7:7+visible_chars]}***"

        return f"{value[:visible_chars]}***"

    def _truncate_string(self, value: str, max_length: int = 1000) -> str:
        """截断长字符串"""
        if len(value) > max_length:
            return value[:max_length] + "... [truncated]"
        return value

    async def _get_request_body(self, request: Request) -> Any | None:
        """获取请求体"""
        try:
            body = await request.body()
            if body:
                try:
                    return json.loads(body.decode("utf-8"))
                except json.JSONDecodeError:
                    return body.decode("utf-8")[:500]
        except Exception:
            pass
        return None

    async def _get_response_body(self, response: Response) -> str | None:
        """获取响应体"""
        try:
            # 尝试读取响应体
            from starlette.responses import StreamingResponse

            if not isinstance(response, StreamingResponse):
                # 重新读取响应体
                original_body = response.body
                if original_body:
                    return original_body.decode("utf-8", errors="replace")
        except Exception:
            pass
        return None


class StructuredLoggingFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 添加额外字段
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging():
    """配置日志"""
    # 创建处理器
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredLoggingFormatter())

    # 配置 API 访问日志
    access_logger = logging.getLogger("api.access")
    access_logger.setLevel(logging.INFO)
    access_logger.addHandler(handler)
    access_logger.propagate = False

    # 配置根日志
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # 如果根日志没有处理器，添加一个
    if not root_logger.handlers:
        root_handler = logging.StreamHandler()
        root_handler.setFormatter(logging.Formatter(settings.log_format))
        root_logger.addHandler(root_handler)
