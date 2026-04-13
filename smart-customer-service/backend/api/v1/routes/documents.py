"""文档管理 API 路由"""

from fastapi import APIRouter, UploadFile, File, Form
from typing import List, Optional
import tempfile
import os

from services.rag_service import rag_service
from core.langfuse_client import create_span

router = APIRouter(prefix="/documents", tags=["文档管理"])


@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    metadata: Optional[str] = Form(None),
):
    """
    上传文档到知识库

    支持格式：PDF, DOCX, MD, TXT, HTML
    """
    with create_span("document_upload_api"):
        uploaded_paths = []

        try:
            # 保存上传文件到临时目录
            for file in files:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=os.path.splitext(file.filename)[1]
                ) as tmp:
                    content = await file.read()
                    tmp.write(content)
                    uploaded_paths.append(tmp.name)

            # 导入文档
            result = await rag_service.import_documents(uploaded_paths)

            return {
                "success": True,
                "data": {
                    "total_chunks": result.total_chunks,
                    "successful_files": result.metadata.get("successful_files", 0),
                    "failed_files": result.failed_files,
                },
            }

        finally:
            # 清理临时文件
            for path in uploaded_paths:
                if os.path.exists(path):
                    os.unlink(path)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档"""
    rag_service.delete_documents([doc_id])
    return {"success": True, "message": f"文档 {doc_id} 已删除"}


@router.get("/stats")
async def get_document_stats():
    """获取知识库统计信息"""
    # TODO: 从 ChromaDB 获取统计
    return {
        "success": True,
        "data": {
            "total_documents": 0,
            "total_chunks": 0,
            "last_updated": None,
        },
    }
