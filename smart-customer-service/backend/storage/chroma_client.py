"""ChromaDB 向量存储客户端"""

from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from core.config import settings


class ChromaDBClient:
    """ChromaDB 客户端封装"""

    def __init__(self):
        self.client = None
        self.collection = None

    def connect(self):
        """连接 ChromaDB"""
        self.client = chromadb.Client(
            Settings(
                chroma_db_impl="duckdb+parquet", persist_directory=settings.chroma_persist_directory
            )
        )

    def close(self):
        """关闭连接"""
        if self.client:
            self.client.persist()

    def add_documents(
        self,
        documents: List[str],
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
    ):
        """添加文档"""
        if not self.collection:
            self.collection = self.client.get_or_create_collection(name="knowledge_base")

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids or [f"doc_{i}" for i in range(len(documents))],
        )

    def query(self, query_texts: List[str], n_results: int = 5) -> List[Dict]:
        """查询相似文档"""
        if not self.collection:
            return []

        results = self.collection.query(query_texts=query_texts, n_results=n_results)
        return results


chroma_client = ChromaDBClient()
