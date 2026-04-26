"""ChromaDB 客户端测试

测试:
- similarity_search 接口兼容性（P1-9 修复验证）
- DocumentChunk 数据类
- 混合检索 RRF 融合算法
"""

from unittest.mock import MagicMock

import pytest
from storage.chroma_client import (
    ChromaDBClient,
    DocumentChunk,
    HybridSearchResult,
)


class TestDocumentChunk:
    """DocumentChunk 数据类测试"""

    def test_create_with_defaults(self):
        """创建带默认值的 DocumentChunk"""
        chunk = DocumentChunk(id="doc1", content="hello world")
        assert chunk.id == "doc1"
        assert chunk.content == "hello world"
        assert chunk.embedding is None
        assert chunk.metadata is None
        assert chunk.score is None

    def test_create_with_all_fields(self):
        """创建带所有字段的 DocumentChunk"""
        chunk = DocumentChunk(
            id="doc2",
            content="test content",
            embedding=[0.1, 0.2, 0.3],
            metadata={"source": "test"},
            score=0.95,
        )
        assert chunk.embedding == [0.1, 0.2, 0.3]
        assert chunk.metadata == {"source": "test"}
        assert chunk.score == 0.95


class TestSimilaritySearchInterface:
    """similarity_search 接口兼容性测试（P1-9 修复验证）"""

    def test_accepts_query_text(self):
        """similarity_search 接受 query 文本参数"""
        import inspect

        sig = inspect.signature(ChromaDBClient.similarity_search)
        params = sig.parameters
        assert "query" in params, "similarity_search 应支持 query 参数"
        assert (
            params["query"].default is not inspect.Parameter.empty
            or params["query"].annotation == str | None
        )

    def test_accepts_query_embedding(self):
        """similarity_search 接受 query_embedding 参数"""
        import inspect

        sig = inspect.signature(ChromaDBClient.similarity_search)
        params = sig.parameters
        assert "query_embedding" in params, "similarity_search 应支持 query_embedding 参数"

    def test_query_and_embedding_are_optional(self):
        """query 和 query_embedding 都是可选参数"""
        import inspect

        sig = inspect.signature(ChromaDBClient.similarity_search)
        params = sig.parameters
        assert params["query"].default is not inspect.Parameter.empty
        assert params["query_embedding"].default is not inspect.Parameter.empty

    @pytest.mark.asyncio
    async def test_returns_empty_without_query_or_embedding(self):
        """无 query 和 query_embedding 时返回空列表"""
        client = ChromaDBClient()
        client._initialized = True
        client.collection = MagicMock()

        result = await client.similarity_search()
        assert result == []


class TestHybridSearchResult:
    """HybridSearchResult 数据类测试"""

    def test_create_result(self):
        """创建混合搜索结果"""
        chunks = [DocumentChunk(id="1", content="a", score=0.9)]
        result = HybridSearchResult(
            chunks=chunks,
            vector_results=chunks,
            keyword_results=[],
            fused_results=chunks,
        )
        assert len(result.chunks) == 1
        assert len(result.vector_results) == 1
        assert len(result.keyword_results) == 0

    def test_empty_result(self):
        """空搜索结果"""
        result = HybridSearchResult(
            chunks=[], vector_results=[], keyword_results=[], fused_results=[]
        )
        assert len(result.chunks) == 0


class TestRRFFusion:
    """RRF 融合算法测试"""

    def test_rrf_fusion_combines_results(self):
        """RRF 融合合并两种搜索结果"""
        client = ChromaDBClient()

        vector_results = [
            DocumentChunk(id="1", content="doc1", score=0.9),
            DocumentChunk(id="2", content="doc2", score=0.8),
        ]
        keyword_results = [
            DocumentChunk(id="2", content="doc2", score=0.7),
            DocumentChunk(id="3", content="doc3", score=0.6),
        ]

        fused = client._reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=0.7,
            keyword_weight=0.3,
            k=5,
        )

        assert len(fused) <= 5
        ids = [doc.id for doc in fused]
        assert "2" in ids, "同时出现在两个结果中的文档应排名更高"

    def test_rrf_fusion_empty_inputs(self):
        """空输入时 RRF 融合返回空列表"""
        client = ChromaDBClient()

        fused = client._reciprocal_rank_fusion(
            vector_results=[],
            keyword_results=[],
            vector_weight=0.7,
            keyword_weight=0.3,
            k=5,
        )
        assert len(fused) == 0

    def test_rrf_fusion_vector_only(self):
        """仅有向量结果时 RRF 融合"""
        client = ChromaDBClient()

        vector_results = [
            DocumentChunk(id="1", content="doc1", score=0.9),
        ]

        fused = client._reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=[],
            vector_weight=0.7,
            keyword_weight=0.3,
            k=5,
        )
        assert len(fused) == 1
        assert fused[0].id == "1"
