"""RAG 知识库 API 路由"""

from typing import Any

from core.exceptions import ErrorCode, RAGQueryFailed, ServiceUnavailableException
from fastapi import APIRouter
from pydantic import BaseModel, Field
from services.rag_service import rag_service

router = APIRouter(prefix="/rag", tags=["RAG 知识库"])


class RAGQueryRequest(BaseModel):
    """RAG 查询请求"""

    query: str = Field(..., description="用户查询", min_length=1, max_length=500)
    session_id: str = Field(..., description="会话 ID")
    filters: dict[str, Any] | None = Field(default=None, description="过滤条件")
    top_k: int = Field(default=3, description="返回文档数量", ge=1, le=10)


class RAGQueryResponse(BaseModel):
    """RAG 查询响应"""

    success: bool
    data: dict[str, Any] | None = None
    message: str | None = None


@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(request: RAGQueryRequest):
    """
    RAG 知识库查询接口

    基于向量检索和 LLM 生成答案

    Raises:
        RAGQueryFailed: RAG 查询失败
        ServiceUnavailableException: 服务不可用
    """
    try:
        result = await rag_service.query(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            session_id=request.session_id,
        )

        return RAGQueryResponse(
            success=True,
            data={
                "answer": result.answer,
                "documents": result.documents,
                "sources": result.sources,
                "confidence": result.confidence,
            },
            message=None,
        )

    except ServiceUnavailableException:
        # 服务不可用，继续向上抛出
        raise
    except Exception as e:
        # 转换为业务异常
        raise RAGQueryFailed(
            message=f"RAG 查询失败：{str(e)}",
            code=ErrorCode.RAG_QUERY_FAILED,
        ) from e


@router.get("/documents")
async def list_documents():
    """获取知识库文档列表"""
    # TODO: 实现文档列表查询
    return {
        "success": True,
        "data": {
            "total": 0,
            "documents": [],
        },
    }
