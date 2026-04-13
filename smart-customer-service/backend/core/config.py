"""
配置管理模块

从环境变量加载配置，使用 Pydantic 进行验证
"""

from functools import lru_cache
from typing import Optional, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # ==================== 应用基础配置 ====================
    app_name: str = Field(default="Langfuse Smart Customer Service", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    environment: str = Field(default="development", description="运行环境")

    # API 配置
    api_prefix: str = Field(default="/api", description="API 前缀")
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 前缀")

    # ==================== Langfuse 配置 ====================
    langfuse_public_key: str = Field(default="", description="Langfuse Public Key")
    langfuse_secret_key: str = Field(default="", description="Langfuse Secret Key")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", description="Langfuse Host")
    langfuse_enabled: bool = Field(default=True, description="是否启用 Langfuse 追踪")

    # ==================== OpenAI 配置 ====================
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    openai_base_url: Optional[str] = Field(default=None, description="OpenAI Base URL")
    openai_model: str = Field(default="gpt-3.5-turbo", description="OpenAI 模型")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", description="OpenAI 嵌入模型"
    )

    # ==================== Redis 配置 ====================
    redis_host: str = Field(default="localhost", description="Redis 主机")
    redis_port: int = Field(default=6379, description="Redis 端口")
    redis_db: int = Field(default=0, description="Redis 数据库")
    redis_password: Optional[str] = Field(default=None, description="Redis 密码")
    redis_ttl_hours: int = Field(default=24, description="会话 TTL(小时)")
    redis_url: Optional[str] = Field(default=None, description="Redis URL(优先级高于单独配置)")

    @field_validator("redis_url", mode="before")
    @classmethod
    def build_redis_url(cls, v: Optional[str], info) -> Optional[str]:
        """如果未提供 redis_url，则从其他字段构建"""
        if v:
            return v
        data = info.data
        password = data.get("password")
        host = data.get("host", "localhost")
        port = data.get("port", 6379)
        db = data.get("db", 0)

        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        return f"redis://{host}:{port}/{db}"

    # ==================== PostgreSQL 配置 ====================
    postgres_host: str = Field(default="localhost", description="PostgreSQL 主机")
    postgres_port: int = Field(default=5432, description="PostgreSQL 端口")
    postgres_db: str = Field(default="smart_cs", description="PostgreSQL 数据库")
    postgres_user: str = Field(default="postgres", description="PostgreSQL 用户")
    postgres_password: str = Field(default="postgres", description="PostgreSQL 密码")
    postgres_url: Optional[str] = Field(
        default=None, description="PostgreSQL URL(优先级高于单独配置)"
    )

    @field_validator("postgres_url", mode="before")
    @classmethod
    def build_postgres_url(cls, v: Optional[str], info) -> str:
        """如果未提供 postgres_url，则从其他字段构建"""
        if v:
            return v
        data = info.data
        return (
            f"postgresql://{data.get('user', 'postgres')}:{data.get('password', 'postgres')}@"
            f"{data.get('host', 'localhost')}:{data.get('port', 5432)}/{data.get('db', 'smart_cs')}"
        )

    # ==================== ChromaDB 配置 ====================
    chroma_host: str = Field(default="localhost", description="ChromaDB 主机")
    chroma_port: int = Field(default=8000, description="ChromaDB 端口")
    chroma_persist_directory: str = Field(
        default="./data/chroma", description="ChromaDB 持久化目录"
    )
    chroma_url: Optional[str] = Field(default=None, description="ChromaDB URL(优先级高于单独配置)")

    # ==================== MinIO 配置 ====================
    minio_endpoint: str = Field(default="localhost:9000", description="MinIO 端点")
    minio_access_key: str = Field(default="minioadmin", description="MinIO Access Key")
    minio_secret_key: str = Field(default="minioadmin", description="MinIO Secret Key")
    minio_bucket: str = Field(default="smart-cs-archives", description="MinIO 存储桶")
    minio_secure: bool = Field(default=False, description="是否使用 HTTPS")

    # ==================== JWT 配置 ====================
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production", description="JWT 密钥"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT 算法")
    jwt_access_token_expire_minutes: int = Field(
        default=30, description="Access Token 过期时间 (分钟)"
    )
    jwt_refresh_token_expire_days: int = Field(default=7, description="Refresh Token 过期时间 (天)")

    # ==================== CORS 配置 ====================
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"], description="CORS 允许的来源"
    )
    cors_allow_credentials: bool = Field(default=True, description="CORS 是否允许凭证")
    cors_allow_methods: List[str] = Field(default=["*"], description="CORS 允许的方法")
    cors_allow_headers: List[str] = Field(default=["*"], description="CORS 允许的头部")

    # ==================== 限流配置 ====================
    rate_limit_requests: int = Field(default=100, description="限流请求数")
    rate_limit_seconds: int = Field(default=60, description="限流时间窗口 (秒)")

    # ==================== 日志配置 ====================
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="日志格式"
    )

    # ==================== 认证配置 ====================
    api_key_header: str = Field(default="X-API-Key", description="API Key 头部名称")
    service_api_keys: List[str] = Field(
        default=["default-service-key"], description="服务间调用的 API Keys"
    )

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """
    获取配置单例

    Returns:
        Settings: 配置对象
    """
    return Settings()


# 全局配置实例
settings = get_settings()
