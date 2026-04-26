"""认证授权组件 - API Key 和 JWT 认证

提供 JWT Token 的创建/解码、API Key 验证和权限检查功能。
所有 datetime 操作使用 timezone-aware UTC 时间。
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel

from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name=settings.api_key_header, auto_error=False)


class TokenPayload(BaseModel):
    """JWT Token 负载"""

    sub: str
    exp: datetime
    iat: datetime
    type: str = "access"
    scopes: list[str] = []


class TokenResponse(BaseModel):
    """Token 响应"""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class APIKey(BaseModel):
    """API Key 模型"""

    key: str
    name: str
    scopes: list[str] = []
    is_active: bool = True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def _utcnow() -> datetime:
    """获取当前 UTC 时间（timezone-aware）"""
    return datetime.now(timezone.utc)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    scopes: list[str] | None = None,
) -> str:
    """创建 Access Token"""
    now = _utcnow()
    expire = now + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "type": "access",
        "scopes": scopes or [],
    }

    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """创建 Refresh Token"""
    now = _utcnow()
    expire = now + (expires_delta or timedelta(days=settings.jwt_refresh_token_expire_days))

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }

    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    """解码 JWT Token

    Raises:
        HTTPException: Token 无效或已过期
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            type=payload.get("type", "access"),
            scopes=payload.get("scopes", []),
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security),  # noqa: B008
) -> str:
    """获取当前用户 ID"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    return payload.sub


async def get_api_key(api_key: str | None = Security(api_key_header)) -> str:  # noqa: B008
    """获取并验证 API Key"""
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key header missing",
        )

    if api_key not in settings.service_api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )

    return api_key


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Security(security),  # noqa: B008
) -> str | None:
    """获取当前用户 ID（可选，认证失败返回 None）"""
    if credentials is None:
        return None

    try:
        payload = decode_token(credentials.credentials)
        return payload.sub
    except HTTPException:
        return None


def require_scope(required_scope: str):
    """需要特定权限的依赖注入"""

    async def scope_checker(
        user_id: str = Security(get_current_user),  # noqa: B008
        token_payload: TokenPayload = Security(decode_token_from_context),  # noqa: B008
    ) -> str:
        if required_scope not in token_payload.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}",
            )
        return user_id

    return scope_checker


def decode_token_from_context(
    credentials: HTTPAuthorizationCredentials | None = Security(security),  # noqa: B008
) -> TokenPayload:
    """从请求上下文中解码 Token"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return decode_token(credentials.credentials)


def generate_api_key() -> str:
    """生成随机 API Key"""
    import secrets as _secrets

    return f"sk-{_secrets.token_urlsafe(32)}"


def verify_service_api_key(api_key: str) -> bool:
    """验证服务 API Key"""
    return api_key in settings.service_api_keys
