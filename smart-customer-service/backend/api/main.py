"""智能客服系统 API 主入口"""

from core.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.auth import APIKeyAuthMiddleware
from api.middleware.exception_handlers import register_exception_handlers
from api.middleware.logging import RequestLoggingMiddleware, setup_logging
from api.middleware.rate_limit import RateLimitMiddleware as CustomRateLimitMiddleware
from api.v1.routes import conversations, intent, rag, tools


# ==================== 应用初始化 ====================
def create_application() -> FastAPI:
    """创建 FastAPI 应用"""

    # 配置日志
    setup_logging()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="智能客服系统 API",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 注册异常处理器
    register_exception_handlers(app)

    # CORS 中间件（最先添加，最后执行）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # 请求日志中间件
    app.add_middleware(
        RequestLoggingMiddleware,
        excluded_paths={"/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"},
        log_request_body=settings.debug,
        log_response_body=settings.debug,
    )

    # API Key 认证中间件
    app.add_middleware(
        APIKeyAuthMiddleware,
        excluded_paths={"/health", "/docs", "/redoc", "/openapi.json"},
    )

    # 速率限制中间件
    app.add_middleware(
        CustomRateLimitMiddleware,
        excluded_paths={"/health", "/docs", "/redoc"},
    )

    # 注册路由
    app.include_router(intent.router, prefix=settings.api_v1_prefix, tags=["意图识别"])
    app.include_router(rag.router, prefix=settings.api_v1_prefix, tags=["RAG 知识库"])
    app.include_router(tools.router, prefix=settings.api_v1_prefix, tags=["工具调用"])
    app.include_router(conversations.router, prefix=settings.api_v1_prefix, tags=["会话管理"])

    @app.on_event("startup")
    async def startup_event():
        """应用启动事件"""
        from storage.redis_client import redis_client

        await redis_client.connect()

    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭事件"""
        from storage.redis_client import redis_client

        await redis_client.close()

    @app.get("/health")
    async def health_check():
        """健康检查"""
        from storage.redis_client import redis_client

        redis_health = await redis_client.ping()

        return {
            "status": "healthy" if redis_health else "unhealthy",
            "redis": "connected" if redis_health else "disconnected",
        }

    return app


app = create_application()
