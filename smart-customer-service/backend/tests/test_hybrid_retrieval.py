"""
Tests for hybrid retrieval strategy (BM25, MMR, HybridRetriever)
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock

from modules.rag_knowledge.retrieval_strategy import (
    BM25Retriever,
    MMRReranker,
    HybridRetriever,
)


class TestBM25Retriever:
    """Test suite for BM25 keyword retriever"""

    def test_tokenization(self):
        """Test text tokenization removes stop words and short tokens"""
        text = "The API authentication error is very common"
        tokens = BM25Retriever._tokenize(text)

        assert "the" not in tokens
        assert "is" not in tokens
        assert "api" in tokens
        assert "authentication" in tokens
        assert "error" in tokens
        assert "common" in tokens

    def test_add_documents_builds_index(self):
        """Test that adding documents builds the index correctly"""
        retriever = BM25Retriever()

        documents = [
            {"doc_id": "doc1", "text": "API authentication guide"},
            {"doc_id": "doc2", "text": "How to reset password"},
            {"doc_id": "doc3", "text": "API rate limiting best practices"},
        ]

        retriever.add_documents(documents)

        assert retriever.num_docs == 3
        assert "api" in retriever.doc_freqs
        assert retriever.doc_freqs["api"] == 2  # appears in doc1 and doc3

    def test_bm25_search_returns_ranked_results(self):
        """Test BM25 search returns results ranked by relevance"""
        retriever = BM25Retriever()

        documents = [
            {"doc_id": "doc1", "text": "API authentication with OAuth tokens"},
            {"doc_id": "doc2", "text": "Database connection troubleshooting"},
            {"doc_id": "doc3", "text": "API rate limiting and throttling"},
        ]

        retriever.add_documents(documents)
        results = retriever.search("API authentication", top_k=2)

        assert len(results) == 2
        assert results[0]["relevance_score"] > results[1]["relevance_score"]
        assert results[0]["doc_id"] == "doc1"  # Most relevant

    def test_empty_index_returns_empty_results(self):
        """Test searching empty index returns empty list"""
        retriever = BM25Retriever()
        results = retriever.search("test query")

        assert results == []

    def test_idf_calculation(self):
        """Test IDF calculation with smoothing"""
        retriever = BM25Retriever()
        retriever.num_docs = 100

        # Rare term (appears in 1 doc)
        idf_rare = retriever._calculate_idf(1)
        # Common term (appears in 50 docs)
        idf_common = retriever._calculate_idf(50)

        assert idf_rare > idf_common  # Rare terms should have higher IDF
        assert idf_rare > 0
        assert idf_common >= 0


class TestMMRReranker:
    """Test suite for MMR reranker"""

    def test_mmr_selects_diverse_results(self):
        """Test MMR balances relevance and diversity"""
        reranker = MMRReranker(lambda_param=0.7)

        documents = [
            {
                "doc_id": "doc1",
                "content_preview": "API authentication using OAuth tokens",
                "relevance_score": 0.9,
            },
            {
                "doc_id": "doc2",
                "content_preview": "API authentication with JWT tokens",
                "relevance_score": 0.85,
            },
            {
                "doc_id": "doc3",
                "content_preview": "Database connection pooling setup",
                "relevance_score": 0.7,
            },
        ]

        results = reranker.rerank("API auth", documents, top_k=2)

        assert len(results) == 2
        # Should prefer diverse results over similar high-scoring ones
        doc_ids = [r["doc_id"] for r in results]
        assert "doc1" in doc_ids  # Highest relevance
        assert "doc3" in doc_ids  # More diverse than doc2

    def test_mmr_with_pure_relevance(self):
        """Test MMR with lambda=1.0 returns pure relevance ranking"""
        reranker = MMRReranker(lambda_param=1.0)

        documents = [
            {"doc_id": "doc1", "content_preview": "text1", "relevance_score": 0.6},
            {"doc_id": "doc2", "content_preview": "text2", "relevance_score": 0.9},
            {"doc_id": "doc3", "content_preview": "text3", "relevance_score": 0.7},
        ]

        results = reranker.rerank("query", documents, top_k=2)

        assert results[0]["doc_id"] == "doc2"  # Highest score
        assert results[1]["doc_id"] == "doc3"  # Second highest

    def test_mmr_with_pure_diversity(self):
        """Test MMR with lambda=0.0 returns pure diversity"""
        reranker = MMRReranker(lambda_param=0.0)

        documents = [
            {"doc_id": "doc1", "content_preview": "same text here", "relevance_score": 0.9},
            {"doc_id": "doc2", "content_preview": "same text here", "relevance_score": 0.8},
            {"doc_id": "doc3", "content_preview": "completely different content", "relevance_score": 0.5},
        ]

        results = reranker.rerank("query", documents, top_k=2)

        # Should select diverse documents even if lower relevance
        doc_ids = [r["doc_id"] for r in results]
        assert "doc3" in doc_ids  # Different content

    def test_jaccard_similarity(self):
        """Test Jaccard similarity calculation"""
        doc1 = {"content_preview": "hello world foo bar"}
        doc2 = {"content_preview": "hello world baz qux"}
        doc3 = {"content_preview": "completely different text"}

        sim_12 = MMRReranker._calculate_similarity(doc1, doc2)
        sim_13 = MMRReranker._calculate_similarity(doc1, doc3)

        assert 0 < sim_12 < 1  # Partial overlap
        assert sim_12 > sim_13  # doc1 and doc2 more similar

    def test_diversity_calculation(self):
        """Test diversity metric calculation"""
        documents = [
            {"content_preview": "text one two"},
            {"content_preview": "text three four"},
            {"content_preview": "completely different stuff"},
        ]

        diversity = MMRReranker._calculate_diversity(documents)
        assert 0 <= diversity <= 1


class TestHybridRetriever:
    """Test suite for hybrid retriever"""

    @pytest.mark.asyncio
    async def test_hybrid_search_combines_results(self):
        """Test hybrid search combines vector and BM25 results"""
        # Mock vector retriever
        mock_vector = AsyncMock()
        mock_vector.query_knowledge = AsyncMock(return_value={
            "retrieved_documents": [
                {"doc_id": "v1", "relevance_score": 0.9, "metadata": {}},
                {"doc_id": "v2", "relevance_score": 0.7, "metadata": {}},
            ]
        })

        # BM25 retriever
        bm25 = BM25Retriever()
        bm25.add_documents([
            {"doc_id": "b1", "text": "API authentication guide"},
            {"doc_id": "b2", "text": "Database troubleshooting"},
        ])

        hybrid = HybridRetriever(
            vector_retriever=mock_vector,
            bm25_retriever=bm25,
            alpha=0.7,
            beta=0.3,
        )

        results = await hybrid.search("API auth", top_k=3, mode="hybrid")

        assert len(results) > 0
        # Check that fusion method is recorded
        assert any(r["metadata"].get("fusion_method") == "rrf" for r in results)

    @pytest.mark.asyncio
    async def test_vector_only_mode(self):
        """Test vector-only search mode"""
        mock_vector = AsyncMock()
        mock_vector.query_knowledge = AsyncMock(return_value={
            "retrieved_documents": [
                {"doc_id": "v1", "relevance_score": 0.9, "metadata": {}},
            ]
        })

        bm25 = BM25Retriever()
        hybrid = HybridRetriever(mock_vector, bm25)

        results = await hybrid.search("query", top_k=5, mode="vector")

        assert len(results) == 1
        assert results[0]["doc_id"] == "v1"

    @pytest.mark.asyncio
    async def test_keyword_only_mode(self):
        """Test keyword-only search mode"""
        mock_vector = AsyncMock()

        bm25 = BM25Retriever()
        bm25.add_documents([
            {"doc_id": "k1", "text": "API authentication"},
        ])

        hybrid = HybridRetriever(mock_vector, bm25)

        results = await hybrid.search("API", top_k=5, mode="keyword")

        assert len(results) == 1
        assert results[0]["doc_id"] == "k1"

    def test_reciprocal_rank_fusion(self):
        """Test RRF score fusion algorithm"""
        mock_vector = Mock()
        bm25 = BM25Retriever()

        hybrid = HybridRetriever(mock_vector, bm25, alpha=0.7, beta=0.3)

        vector_results = [
            {"doc_id": "doc1", "relevance_score": 0.9, "metadata": {}},
            {"doc_id": "doc2", "relevance_score": 0.7, "metadata": {}},
        ]

        bm25_results = [
            {"doc_id": "doc2", "relevance_score": 0.8, "metadata": {}},
            {"doc_id": "doc3", "relevance_score": 0.6, "metadata": {}},
        ]

        fused = hybrid._fuse_results(vector_results, bm25_results, top_k=3)

        assert len(fused) == 3
        # doc2 should rank high due to appearing in both
        doc_ids = [r["doc_id"] for r in fused]
        assert "doc2" in doc_ids

    def test_invalid_alpha_beta_raises_error(self):
        """Test that invalid alpha/beta values raise error"""
        mock_vector = Mock()
        bm25 = BM25Retriever()

        with pytest.raises(ValueError):
            HybridRetriever(mock_vector, bm25, alpha=1.5, beta=0.3)

        with pytest.raises(ValueError):
            HybridRetriever(mock_vector, bm25, alpha=-0.1, beta=0.3)

    def test_mmr_lambda_validation(self):
        """Test MMR lambda parameter validation"""
        with pytest.raises(ValueError):
            MMRReranker(lambda_param=1.5)

        with pytest.raises(ValueError):
            MMRReranker(lambda_param=-0.1)


class TestIntegration:
    """Integration tests for complete retrieval pipeline"""

    @pytest.mark.asyncio
    async def test_end_to_end_hybrid_retrieval(self):
        """Test complete hybrid retrieval pipeline"""
        # Setup
        mock_vector = AsyncMock()
        mock_vector.query_knowledge = AsyncMock(return_value={
            "retrieved_documents": [
                {
                    "doc_id": "doc1",
                    "content_preview": "API authentication with OAuth",
                    "relevance_score": 0.85,
                    "metadata": {"category": "auth"},
                },
                {
                    "doc_id": "doc2",
                    "content_preview": "API rate limiting guide",
                    "relevance_score": 0.75,
                    "metadata": {"category": "api"},
                },
            ]
        })

        bm25 = BM25Retriever()
        bm25.add_documents([
            {"doc_id": "doc1", "text": "API authentication with OAuth tokens"},
            {"doc_id": "doc3", "text": "Password reset procedures"},
        ])

        hybrid = HybridRetriever(
            vector_retriever=mock_vector,
            bm25_retriever=bm25,
            alpha=0.7,
            beta=0.3,
            use_mmr=True,
            mmr_lambda=0.7,
        )

        # Execute
        results = await hybrid.search("API authentication", top_k=3)

        # Verify
        assert len(results) > 0
        assert all("relevance_score" in r for r in results)
        assert all("doc_id" in r for r in results)
