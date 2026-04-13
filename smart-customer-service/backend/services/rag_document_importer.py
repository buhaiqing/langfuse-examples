"""文档导入与分块引擎"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import hashlib
from dataclasses import dataclass, field

from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredHTMLLoader,
    TextLoader,
)
from langchain_core.documents import Document
from core.config import settings


@dataclass
class ImportResult:
    """文档导入结果"""

    documents: List[Document]
    total_chunks: int
    failed_files: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentImportEngine:
    """文档导入引擎"""

    def __init__(self):
        # 分块配置
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""],
        )

        self.md_splitter = MarkdownTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )

        # 文件扩展名映射
        self.loader_map = {
            ".pdf": PyPDFLoader,
            ".docx": Docx2txtLoader,
            ".html": UnstructuredHTMLLoader,
            ".htm": UnstructuredHTMLLoader,
            ".txt": TextLoader,
            ".md": None,  # 特殊处理
        }

    async def import_files(
        self,
        file_paths: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ImportResult:
        """
        导入文件

        Args:
            file_paths: 文件路径列表
            metadata: 额外元数据

        Returns:
            ImportResult: 导入结果
        """
        documents = []
        failed_files = []

        for file_path in file_paths:
            try:
                loaded_docs = await self._load_file(file_path)

                # 添加自定义元数据
                if metadata:
                    for doc in loaded_docs:
                        doc.metadata.update(metadata)

                documents.extend(loaded_docs)

            except Exception as e:
                failed_files.append(f"{file_path}: {str(e)}")

        # 分块处理
        all_chunks = []
        for doc in documents:
            chunks = self._split_document(doc)
            all_chunks.extend(chunks)

        return ImportResult(
            documents=all_chunks,
            total_chunks=len(all_chunks),
            failed_files=failed_files,
            metadata={
                "total_files": len(file_paths),
                "successful_files": len(file_paths) - len(failed_files),
            },
        )

    async def _load_file(self, file_path: str) -> List[Document]:
        """加载单个文件"""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext not in self.loader_map:
            raise ValueError(f"不支持的文件类型：{ext}")

        loader_class = self.loader_map[ext]

        if ext == ".md":
            # Markdown 特殊处理（不分块）
            loader = TextLoader(file_path)
            docs = await loader.aload()
            # 使用 Markdown 分块器
            return self.md_splitter.split_documents(docs)

        # 其他格式使用对应加载器
        loader = loader_class(file_path)
        return await loader.aload()

    def _split_document(self, doc: Document) -> List[Document]:
        """
        分块文档

        Args:
            doc: 文档

        Returns:
            分块后的文档列表
        """
        # 检查是否已经分块
        if hasattr(doc, "metadata") and doc.metadata.get("already_chunked"):
            return [doc]

        # 使用文本分块器
        chunks = self.text_splitter.split_documents([doc])

        # 为每个 chunk 添加元数据
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)
            chunk.metadata["doc_hash"] = self._compute_hash(chunk.page_content)

        return chunks

    def _compute_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode()).hexdigest()


# 全局实例
document_import_engine = DocumentImportEngine()
