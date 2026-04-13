"""
统一异常处理模块

定义业务异常体系和全局异常处理器
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(str, Enum):
    """错误码枚举"""

    # 通用错误 (1xxxx)
    UNKNOWN_ERROR = "10000"
    INVALID_PARAMETER = "10001"
    MISSING_PARAMETER = "10002"
    INVALID_REQUEST = "10003"
    RESOURCE_NOT_FOUND = "10004"
    RESOURCE_EXISTS = "10005"
    OPERATION_FAILED = "10006"

    # 认证授权错误 (2xxxx)
    UNAUTHORIZED = "20001"
    FORBIDDEN = "20002"
    INVALID_TOKEN = "20003"
    TOKEN_EXPIRED = "20004"
    INVALID_API_KEY = "20005"

    # 业务错误 (3xxxx)
    INTENT_RECOGNITION_FAILED = "30001"
    RAG_QUERY_FAILED = "30002"
    TOOL_EXECUTION_FAILED = "30003"
    ESCALATION_FAILED = "30004"
    CONVERSATION_NOT_FOUND = "30005"
    DOCUMENT_NOT_FOUND = "30006"

    # 外部服务错误 (4xxxx)
    REDIS_ERROR = "40001"
    DATABASE_ERROR = "40002"
    VECTOR_DB_ERROR = "40003"
    LLM_SERVICE_ERROR = "40004"
    EXTERNAL_API_ERROR = "40005"

    # 限流熔断错误 (5xxxx)
    RATE_LIMIT_EXCEEDED = "50001"
    CIRCUIT_BREAKER_OPEN = "50002"


class BusinessException(Exception):
    """
    业务异常基类

    Attributes:
        code: 错误码
        message: 错误消息
        status_code: HTTP 状态码
        details: 额外详情
    """

    def __init__(
        self,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        message: str = "操作失败",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": False,
            "code": self.code,
            "message": self.message,
            "details": self.details if self.details else None,
        }


class ValidationException(BusinessException):
    """参数验证异常"""

    def __init__(self, message: str = "参数验证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=ErrorCode.INVALID_PARAMETER,
            message=message,
            status_code=422,
            details=details,
        )


class AuthenticationException(BusinessException):
    """认证异常"""

    def __init__(self, message: str = "认证失败", code: ErrorCode = ErrorCode.UNAUTHORIZED):
        super().__init__(
            code=code,
            message=message,
            status_code=401,
        )


class AuthorizationException(BusinessException):
    """授权异常"""

    def __init__(self, message: str = "权限不足"):
        super().__init__(
            code=ErrorCode.FORBIDDEN,
            message=message,
            status_code=403,
        )


class ResourceNotFoundException(BusinessException):
    """资源不存在异常"""

    def __init__(self, resource: str = "资源", resource_id: Optional[str] = None):
        message = f"{resource}不存在"
        if resource_id:
            message = f"{resource} [{resource_id}] 不存在"
        super().__init__(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message=message,
            status_code=404,
        )


class ServiceUnavailableException(BusinessException):
    """服务不可用异常"""

    def __init__(self, message: str = "服务暂时不可用", code: ErrorCode = ErrorCode.UNKNOWN_ERROR):
        super().__init__(
            code=code,
            message=message,
            status_code=503,
        )


class RateLimitException(BusinessException):
    """限流异常"""

    def __init__(self, message: str = "请求过于频繁，请稍后重试", retry_after: int = 60):
        super().__init__(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            status_code=429,
            details={"retry_after": retry_after},
        )
