"""认证授权组件 - API Key 和 JWT 认证"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from pydantic import BaseModel

from core.config import settings


# ==================== 安全配置 ====================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name=settings.api_key_header, auto_error=False)


# ==================== 数据模型 ====================
class TokenPayload(BaseModel):
    """JWT Token 负载"""

    sub: str  # 用户 ID
    exp: datetime  # 过期时间
    iat: datetime  # 签发时间
    type: str = "access"  # token 类型：access/refresh
    scopes: List[str] = []  # 权限范围


class TokenResponse(BaseModel):
    """Token 响应"""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # 过期时间 (秒)


class APIKey(BaseModel):
    """API Key 模型"""

    key: str
    name: str
    scopes: List[str] = []
    is_active: bool = True


# ==================== 密码处理 ====================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


# ==================== JWT Token 处理 ====================
def create_access_token(
    subject: str, expires_delta: Optional[timedelta] = None, scopes: Optional[List[str]] = None
) -> str:
    """
    创建 Access Token

    Args:
        subject: 用户 ID
        expires_delta: 过期时间增量
        scopes: 权限范围

    Returns:
        JWT Access Token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
        "scopes": scopes or [],
    }

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    return encoded_jwt


def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 Refresh Token

    Args:
        subject: 用户 ID
        expires_delta: 过期时间增量

    Returns:
        JWT Refresh Token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)

    to_encode = {"sub": subject, "exp": expire, "iat": datetime.utcnow(), "type": "refresh"}

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    return encoded_jwt


def decode_token(token: str) -> TokenPayload:
    """
    解码 Token

    Args:
        token: JWT Token

    Returns:
        Token 负载

    Raises:
        HTTPException: Token 无效或已过期
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"]),
            type=payload.get("type", "access"),
            scopes=payload.get("scopes", []),
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ==================== 认证依赖 ====================
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> str:
    """
    获取当前用户 ID

    Args:
        credentials: HTTP Bearer 凭证

    Returns:
        用户 ID

    Raises:
        HTTPException: 认证失败
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    return payload.sub


async def get_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    获取 API Key

    Args:
        api_key: API Key

    Returns:
        API Key

    Raises:
        HTTPException: 认证失败
    """
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
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Optional[str]:
    """
    获取当前用户 ID(可选)

    Args:
        credentials: HTTP Bearer 凭证

    Returns:
        用户 ID 或 None
    """
    if credentials is None:
        return None

    try:
        payload = decode_token(credentials.credentials)
        return payload.sub
    except HTTPException:
        return None


# ==================== 权限检查 ====================
def require_scope(required_scope: str):
    """
    需要特定权限的装饰器

    Args:
        required_scope: 所需权限

    Returns:
        依赖函数
    """

    async def scope_checker(
        user_id: str = Depends(get_current_user),
        token_payload: TokenPayload = Depends(decode_token_from_context),
    ) -> str:
        if required_scope not in token_payload.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}",
            )
        return user_id

    return scope_checker


def decode_token_from_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> TokenPayload:
    """从上下文中解码 Token"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return decode_token(credentials.credentials)


# ==================== 工具函数 ====================
def generate_api_key() -> str:
    """生成随机 API Key"""
    import secrets

    return f"sk-{secrets.token_urlsafe(32)}"


def verify_service_api_key(api_key: str) -> bool:
    """验证服务 API Key"""
    return api_key in settings.service_api_keys
