"""文档管理 API 路由"""

import hashlib
import logging
import os
import re
import tempfile

from core.exceptions import (
    DocumentNotFoundException,
    ErrorCode,
    RAGQueryFailed,
    ValidationException,
)
from core.langfuse_client import create_span
from fastapi import APIRouter, File, Form, UploadFile
from services.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["文档管理"])

# 允许的文件扩展名白名单
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt", ".html", ".htm"}

# 允许的文件 MIME 类型（用于额外验证）
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/markdown",
    "text/plain",
    "text/html",
}

# 最大文件大小 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def _validate_filename(filename: str) -> str:
    """
    验证并清理文件名，防止目录遍历攻击

    Args:
        filename: 原始文件名

    Returns:
        str: 清理后的文件名

    Raises:
        ValidationException: 文件名不合法
    """
    if not filename:
        raise ValidationException(message="文件名不能为空")

    # 移除路径分隔符和特殊字符
    filename = os.path.basename(filename)
    filename = re.sub(r"[^\w\-.]", "_", filename)

    # 检查文件名长度
    if len(filename) > 255:
        raise ValidationException(message="文件名过长")

    return filename


def _validate_file_extension(filename: str) -> None:
    """
    验证文件扩展名是否在白名单中

    Args:
        filename: 文件名

    Raises:
        ValidationException: 文件类型不允许
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationException(
            message=f"不支持的文件类型: {ext}。允许的类型: {', '.join(ALLOWED_EXTENSIONS)}",
            details={"allowed_types": list(ALLOWED_EXTENSIONS), "provided_type": ext},
        )


def _validate_file_size(content: bytes) -> None:
    """
    验证文件大小是否在限制范围内

    Args:
        content: 文件内容

    Raises:
        ValidationException: 文件过大
    """
    if len(content) > MAX_FILE_SIZE:
        raise ValidationException(
            message=f"文件过大，最大允许大小: {MAX_FILE_SIZE / 1024 / 1024:.1f}MB",
            details={"max_size_bytes": MAX_FILE_SIZE, "provided_size_bytes": len(content)},
        )


def _validate_file_content(filename: str, content: bytes) -> None:
    """
    验证文件内容（魔数检查）

    Args:
        filename: 文件名
        content: 文件内容

    Raises:
        ValidationException: 文件内容不合法
    """
    if not content:
        raise ValidationException(message="文件内容为空")

    ext = os.path.splitext(filename)[1].lower()

    # PDF 魔数检查
    if ext == ".pdf":
        if not content.startswith(b"%PDF"):
            raise ValidationException(message="无效的 PDF 文件")

    # DOCX 魔数检查 (ZIP 格式)
    elif ext == ".docx":
        if not content.startswith(b"PK\x03\x04"):
            raise ValidationException(message="无效的 DOCX 文件")

    # HTML 标签检查
    elif ext in (".html", ".htm"):
        content_str = content[:1024].decode("utf-8", errors="ignore").lower()
        if "<script" in content_str or "<iframe" in content_str:
            raise ValidationException(message="HTML 文件包含不安全的内容")


def _generate_safe_filename(original_filename: str) -> str:
    """
    生成安全的临时文件名

    Args:
        original_filename: 原始文件名

    Returns:
        str: 安全的文件名
    """
    ext = os.path.splitext(original_filename)[1].lower()
    # 使用时间戳 + 随机哈希作为文件名
    timestamp = str(int(os.path.getmtime(__file__) * 1000)) if os.path.exists(__file__) else "0"
    hash_digest = hashlib.sha256(f"{original_filename}{timestamp}".encode()).hexdigest()[:16]
    return f"doc_{hash_digest}{ext}"


@router.post("/upload")
async def upload_documents(
    files: list[UploadFile] = File(..., description="要上传的文件列表"),  # noqa: B008
    metadata: str | None = Form(None, description="文档元数据（JSON格式）"),
):
    """
    上传文档到知识库

    支持格式：PDF, DOCX, MD, TXT, HTML

    Args:
        files: 文件列表（最大10MB每个）
        metadata: 可选的文档元数据

    Returns:
        dict: 上传结果，包含成功和失败文件统计

    Raises:
        ValidationException: 参数验证失败
        RAGQueryFailed: 文档导入失败
    """
    with create_span("document_upload_api"):
        results = {
            "total_files": len(files),
            "successful_files": 0,
            "failed_files": 0,
            "errors": [],
        }
        uploaded_paths = []

        try:
            for file in files:
                try:
                    # 1. 验证文件名
                    safe_filename = _validate_filename(file.filename)

                    # 2. 验证文件扩展名
                    _validate_file_extension(safe_filename)

                    # 3. 读取并验证文件大小
                    content = await file.read()
                    _validate_file_size(content)

                    # 4. 验证文件内容
                    _validate_file_content(safe_filename, content)

                    # 5. 创建临时文件（使用安全文件名）
                    ext = os.path.splitext(safe_filename)[1]
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=ext, prefix="upload_"
                    ) as tmp:
                        tmp.write(content)
                        uploaded_paths.append(tmp.name)

                    results["successful_files"] += 1

                except ValidationException as e:
                    results["failed_files"] += 1
                    results["errors"].append(
                        {
                            "filename": file.filename,
                            "error": e.message,
                        }
                    )
                    logger.warning(f"文件上传失败 {file.filename}: {e.message}")

            # 导入文档到 RAG
            if uploaded_paths:
                try:
                    rag_result = await rag_service.import_documents(uploaded_paths)

                    return {
                        "success": True,
                        "data": {
                            "total_chunks": rag_result.total_chunks,
                            "successful_files": results["successful_files"],
                            "failed_files": results["failed_files"],
                            "errors": results["errors"] if results["errors"] else None,
                        },
                    }
                except Exception as e:
                    # 转换为业务异常
                    raise RAGQueryFailed(
                        message=f"文档导入失败：{str(e)}",
                        code=ErrorCode.RAG_QUERY_FAILED,
                    ) from e
            else:
                raise ValidationException(message="没有有效的文件可以导入")

        finally:
            # 清理临时文件
            for path in uploaded_paths:
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except Exception as e:
                    logger.error(f"清理临时文件失败 {path}: {e}")


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """
    删除文档

    Raises:
        ValidationException: 文档 ID 无效
        DocumentNotFoundException: 文档不存在
    """
    if not doc_id or not re.match(r"^[\w\-]+$", doc_id):
        raise ValidationException(message="无效的文档 ID")

    try:
        rag_service.delete_documents([doc_id])
        return {"success": True, "message": f"文档 {doc_id} 已删除"}
    except Exception as e:
        if "not found" in str(e).lower():
            raise DocumentNotFoundException(doc_id=doc_id) from e
        raise RAGQueryFailed(message=f"删除文档失败：{str(e)}") from e


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
            "allowed_types": list(ALLOWED_EXTENSIONS),
            "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024,
        },
    }
