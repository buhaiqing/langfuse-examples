"""
全局异常处理器

统一处理应用中的各种异常，返回标准化的错误响应
"""

import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from pydantic import ValidationError

from core.config import settings
from core.exceptions import (
    BusinessException,
    ErrorCode,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    ResourceNotFoundException,
    RateLimitException,
    ServiceUnavailableException,
)

logger = logging.getLogger(__name__)


def get_request_id(request: Request) -> str:
    """获取请求 ID"""
    return getattr(request.state, "request_id", "unknown")


def create_error_response(
    code: ErrorCode,
    message: str,
    status_code: int,
    details: dict = None,
    request_id: str = None,
) -> JSONResponse:
    """创建标准错误响应"""
    content = {
        "success": False,
        "code": code,
        "message": message,
    }

    if details:
        content["details"] = details

    if request_id:
        content["request_id"] = request_id

    return JSONResponse(status_code=status_code, content=content)


async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
    """处理业务异常"""
    logger.warning(
        f"Business exception: {exc.code} - {exc.message}",
        extra={"request_id": get_request_id(request)},
    )

    return create_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request_id=get_request_id(request),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求验证异常（FastAPI）"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(
        f"Validation error: {errors}",
        extra={"request_id": get_request_id(request)},
    )

    return create_error_response(
        code=ErrorCode.INVALID_PARAMETER,
        message="请求参数验证失败",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"errors": errors},
        request_id=get_request_id(request),
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """处理 Pydantic 验证异常"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(
        f"Pydantic validation error: {errors}",
        extra={"request_id": get_request_id(request)},
    )

    return create_error_response(
        code=ErrorCode.INVALID_PARAMETER,
        message="数据验证失败",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"errors": errors},
        request_id=get_request_id(request),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理 HTTP 异常"""
    # 将 HTTPException 映射到业务错误码
    error_code_mapping = {
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.RESOURCE_NOT_FOUND,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
    }

    code = error_code_mapping.get(exc.status_code, ErrorCode.UNKNOWN_ERROR)

    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={"request_id": get_request_id(request)},
    )

    return create_error_response(
        code=code,
        message=exc.detail if isinstance(exc.detail, str) else "请求失败",
        status_code=exc.status_code,
        request_id=get_request_id(request),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的通用异常"""
    request_id = get_request_id(request)

    # 记录详细错误信息
    logger.error(
        f"Unhandled exception: {str(exc)}\n{traceback.format_exc()}",
        extra={"request_id": request_id},
    )

    # 生产环境不暴露详细错误信息
    if settings.is_production:
        message = "服务器内部错误，请稍后重试"
        details = {"request_id": request_id}
    else:
        message = str(exc)
        details = {
            "traceback": traceback.format_exc().split("\n"),
            "request_id": request_id,
        }

    return create_error_response(
        code=ErrorCode.UNKNOWN_ERROR,
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=details,
        request_id=request_id,
    )


def register_exception_handlers(app):
    """注册所有异常处理器"""
    # 业务异常
    app.add_exception_handler(BusinessException, business_exception_handler)

    # 验证异常
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)

    # HTTP 异常
    app.add_exception_handler(HTTPException, http_exception_handler)

    # 通用异常（必须最后注册）
    app.add_exception_handler(Exception, general_exception_handler)
