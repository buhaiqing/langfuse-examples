"""ChromaDB 向量存储客户端 - 增强版

支持混合检索（向量相似度 + 关键词 BM25）
提供集合管理、批量操作和健康检查
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import chromadb
import numpy as np
from chromadb.config import Settings
from core.config import settings
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """文档块数据类"""

    id: str
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] | None = None
    score: float | None = None


@dataclass
class HybridSearchResult:
    """混合搜索结果"""

    chunks: list[DocumentChunk]
    vector_results: list[DocumentChunk]
    keyword_results: list[DocumentChunk]
    fused_results: list[DocumentChunk]


class ChromaDBClient:
    """增强版 ChromaDB 客户端"""

    def __init__(self):
        self.client: chromadb.Client | None = None
        self.collection = None
        self.collection_name = "knowledge_base"
        self._in_memory_index: BM25Okapi | None = None
        self._doc_id_map: dict[int, str] = {}
        self._initialized = False

    async def connect(self) -> None:
        """连接 ChromaDB"""
        try:
            if settings.chroma_url:
                # 连接到远程 ChromaDB 服务器
                self.client = chromadb.HttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port,
                )
            else:
                # 本地持久化模式
                self.client = chromadb.PersistentClient(
                    path=settings.chroma_persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    ),
                )

            # 获取或创建集合
            await self._ensure_collection()

            self._initialized = True
            logger.info(f"ChromaDB 连接成功，集合: {self.collection_name}")

        except Exception as e:
            logger.error(f"ChromaDB 连接失败: {e}")
            raise

    async def _ensure_collection(self) -> None:
        """确保集合存在"""
        try:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            raise

    async def close(self) -> None:
        """关闭连接"""
        self._initialized = False
        self._in_memory_index = None
        self._doc_id_map = {}
        logger.info("ChromaDB 连接已关闭")

    async def ping(self) -> bool:
        """检查连接健康"""
        if not self._initialized or not self.client:
            return False
        try:
            # 尝试获取集合信息
            self.client.get_collection(self.collection_name)
            return True
        except Exception as e:
            logger.warning(f"ChromaDB 健康检查失败: {e}")
            return False

    # ==================== 文档操作 ====================

    async def add_documents(
        self,
        documents: list[DocumentChunk],
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """批量添加文档

        Args:
            documents: 文档块列表
            batch_size: 批处理大小

        Returns:
            操作结果统计
        """
        if not self._initialized:
            await self.connect()

        total_added = 0
        errors = []

        # 分批处理
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]

            try:
                ids = [doc.id for doc in batch]
                contents = [doc.content for doc in batch]
                embeddings = [doc.embedding for doc in batch if doc.embedding]
                metadatas = [doc.metadata or {} for doc in batch]

                # 添加文档
                self.collection.add(
                    ids=ids,
                    documents=contents,
                    embeddings=embeddings if embeddings else None,
                    metadatas=metadatas,
                )

                total_added += len(batch)
                logger.debug(f"已添加 {len(batch)} 个文档块")

            except Exception as e:
                logger.error(f"批量添加文档失败: {e}")
                errors.append(str(e))

        # 重建内存索引（用于关键词检索）
        await self._rebuild_keyword_index()

        return {
            "success": len(errors) == 0,
            "added": total_added,
            "failed": len(errors),
            "errors": errors,
        }

    async def update_document(self, doc_id: str, **updates) -> bool:
        """更新文档

        Args:
            doc_id: 文档 ID
            **updates: 更新字段（content, metadata, embedding）

        Returns:
            是否成功
        """
        if not self._initialized:
            await self.connect()

        try:
            update_data = {}
            if "content" in updates:
                update_data["documents"] = updates["content"]
            if "metadata" in updates:
                update_data["metadatas"] = updates["metadata"]
            if "embedding" in updates:
                update_data["embeddings"] = updates["embedding"]

            self.collection.update(ids=[doc_id], **update_data)

            # 重建索引
            await self._rebuild_keyword_index()
            return True

        except Exception as e:
            logger.error(f"更新文档失败: {e}")
            return False

    async def delete_documents(self, doc_ids: list[str]) -> int:
        """删除文档

        Args:
            doc_ids: 文档 ID 列表

        Returns:
            删除的文档数
        """
        if not self._initialized:
            await self.connect()

        try:
            self.collection.delete(ids=doc_ids)
            logger.info(f"已删除 {len(doc_ids)} 个文档")

            # 重建索引
            await self._rebuild_keyword_index()
            return len(doc_ids)

        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return 0

    async def get_document(self, doc_id: str) -> DocumentChunk | None:
        """获取单个文档

        Args:
            doc_id: 文档 ID

        Returns:
            文档块或 None
        """
        if not self._initialized:
            await self.connect()

        try:
            result = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"],
            )

            if not result["ids"]:
                return None

            return DocumentChunk(
                id=result["ids"][0],
                content=result["documents"][0],
                metadata=result["metadatas"][0] if result["metadatas"] else None,
            )

        except Exception as e:
            logger.error(f"获取文档失败: {e}")
            return None

    # ==================== 搜索功能 ====================

    async def similarity_search(
        self,
        query: str | None = None,
        query_embedding: list[float] | None = None,
        k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """向量相似度搜索

        支持两种调用方式：
        1. 传入 query 文本，内部自动生成 embedding
        2. 传入 query_embedding 向量，直接搜索

        Args:
            query: 查询文本（与 query_embedding 二选一）
            query_embedding: 查询向量（与 query 二选一）
            k: 返回结果数量
            filter_metadata: 元数据过滤条件

        Returns:
            文档块列表（按相似度排序）
        """
        if not self._initialized:
            await self.connect()

        if query_embedding is None and query is None:
            logger.error("similarity_search 必须提供 query 或 query_embedding")
            return []

        if query_embedding is None and query is not None:
            query_embedding = await self._embed_query(query)

        if query_embedding is None:
            logger.error("无法生成查询向量")
            return []

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"],
            )

            chunks = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    chunk = DocumentChunk(
                        id=doc_id,
                        content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i] if results["metadatas"] else None,
                        score=1 - (results["distances"][0][i] if results["distances"] else 0),
                    )
                    chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []

    async def keyword_search(
        self,
        query: str,
        k: int = 5,
    ) -> list[DocumentChunk]:
        """关键词 BM25 搜索

        Args:
            query: 查询文本
            k: 返回结果数量

        Returns:
            文档块列表（按 BM25 分数排序）
        """
        if not self._initialized:
            await self.connect()

        try:
            # 确保索引已建立
            if self._in_memory_index is None:
                await self._rebuild_keyword_index()

            if self._in_memory_index is None:
                logger.warning("关键词索引未建立")
                return []

            # 分词并搜索
            query_tokens = query.lower().split()
            scores = self._in_memory_index.get_scores(query_tokens)

            # 获取 top-k
            top_indices = np.argsort(scores)[::-1][:k]

            chunks = []
            for idx in top_indices:
                if scores[idx] > 0:
                    doc_id = self._doc_id_map.get(int(idx))
                    if doc_id:
                        doc = await self.get_document(doc_id)
                        if doc:
                            doc.score = float(scores[idx])
                            chunks.append(doc)

            return chunks

        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")
            return []

    async def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        k: int = 5,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        filter_metadata: dict[str, Any] | None = None,
    ) -> HybridSearchResult:
        """混合检索（向量 + 关键词）

        使用 RRF (Reciprocal Rank Fusion) 算法融合结果

        Args:
            query: 查询文本
            query_embedding: 查询向量
            k: 返回结果数量
            vector_weight: 向量检索权重
            keyword_weight: 关键词检索权重
            filter_metadata: 元数据过滤条件

        Returns:
            混合搜索结果
        """
        if not self._initialized:
            await self.connect()

        # 并行执行两种搜索
        vector_task = self.similarity_search(
            query_embedding=query_embedding,
            k=k * 2,
            filter_metadata=filter_metadata,
        )
        keyword_task = self.keyword_search(query=query, k=k * 2)

        vector_results, keyword_results = await asyncio.gather(vector_task, keyword_task)

        # RRF 融合
        fused_results = self._reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            k=k,
        )

        return HybridSearchResult(
            chunks=fused_results,
            vector_results=vector_results[:k],
            keyword_results=keyword_results[:k],
            fused_results=fused_results,
        )

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[DocumentChunk],
        keyword_results: list[DocumentChunk],
        vector_weight: float,
        keyword_weight: float,
        k: int = 5,
        k_constant: int = 60,
    ) -> list[DocumentChunk]:
        """RRF 融合算法

        Args:
            vector_results: 向量搜索结果
            keyword_results: 关键词搜索结果
            vector_weight: 向量权重
            keyword_weight: 关键词权重
            k: 返回数量
            k_constant: RRF 常数

        Returns:
            融合后的结果
        """
        scores: dict[str, float] = {}
        doc_map: dict[str, DocumentChunk] = {}

        # 处理向量搜索结果
        for rank, doc in enumerate(vector_results, start=1):
            doc_id = doc.id
            doc_map[doc_id] = doc
            rrf_score = vector_weight * (1 / (k_constant + rank))
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score

        # 处理关键词搜索结果
        for rank, doc in enumerate(keyword_results, start=1):
            doc_id = doc.id
            doc_map[doc_id] = doc
            rrf_score = keyword_weight * (1 / (k_constant + rank))
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score

        # 排序并返回
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:k]

        results = []
        for doc_id in sorted_ids:
            doc = doc_map[doc_id]
            doc.score = scores[doc_id]
            results.append(doc)

        return results

    # ==================== 集合管理 ====================

    async def list_collections(self) -> list[str]:
        """列出所有集合"""
        if not self._initialized:
            await self.connect()

        try:
            collections = self.client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"列出集合失败: {e}")
            return []

    async def create_collection(self, name: str, metadata: dict | None = None) -> bool:
        """创建新集合

        Args:
            name: 集合名称
            metadata: 集合元数据

        Returns:
            是否成功
        """
        if not self._initialized:
            await self.connect()

        try:
            self.client.create_collection(name=name, metadata=metadata)
            logger.info(f"创建集合: {name}")
            return True
        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            return False

    async def delete_collection(self, name: str) -> bool:
        """删除集合

        Args:
            name: 集合名称

        Returns:
            是否成功
        """
        if not self._initialized:
            await self.connect()

        try:
            self.client.delete_collection(name=name)
            logger.info(f"删除集合: {name}")
            return True
        except Exception as e:
            logger.error(f"删除集合失败: {e}")
            return False

    async def get_collection_stats(self) -> dict[str, Any]:
        """获取集合统计信息

        Returns:
            统计信息字典
        """
        if not self._initialized:
            await self.connect()

        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "initialized": self._initialized,
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    # ==================== 索引管理 ====================

    async def _embed_query(self, query: str) -> list[float] | None:
        """将查询文本转换为向量

        Args:
            query: 查询文本

        Returns:
            查询向量，失败时返回 None
        """
        try:
            from core.llm_client_pool import get_embedding_client

            embedding_client = get_embedding_client()
            embeddings = await embedding_client.aembed_query(query)
            return embeddings
        except Exception as e:
            logger.error("查询文本生成 embedding 失败: %s", e)
            return None

    async def _rebuild_keyword_index(self) -> None:
        """重建 BM25 关键词索引"""
        try:
            # 获取所有文档
            result = self.collection.get(
                include=["documents"],
            )

            if not result["ids"]:
                self._in_memory_index = None
                self._doc_id_map = {}
                return

            # 构建索引
            corpus = []
            self._doc_id_map = {}

            for i, (doc_id, content) in enumerate(
                zip(result["ids"], result["documents"], strict=False)
            ):
                if content:
                    tokens = content.lower().split()
                    corpus.append(tokens)
                    self._doc_id_map[i] = doc_id

            if corpus:
                self._in_memory_index = BM25Okapi(corpus)
                logger.debug(f"BM25 索引重建完成，包含 {len(corpus)} 个文档")
            else:
                self._in_memory_index = None

        except Exception as e:
            logger.error(f"重建关键词索引失败: {e}")
            self._in_memory_index = None

    async def reset_collection(self) -> bool:
        """清空集合（谨慎使用）

        Returns:
            是否成功
        """
        if not self._initialized:
            await self.connect()

        try:
            self.client.delete_collection(name=self.collection_name)
            await self._ensure_collection()
            self._in_memory_index = None
            self._doc_id_map = {}
            logger.warning(f"集合 {self.collection_name} 已清空")
            return True
        except Exception as e:
            logger.error(f"清空集合失败: {e}")
            return False


# 全局 ChromaDB 客户端实例
chroma_client = ChromaDBClient()

# 为测试兼容性提供别名
ChromaClient = ChromaDBClient


async def get_chroma_client() -> ChromaDBClient:
    """获取 ChromaDB 客户端实例"""
    return chroma_client
