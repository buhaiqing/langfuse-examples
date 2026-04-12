"""
Hybrid retrieval strategy combining vector search and BM25 keyword search
Implements score fusion and MMR reranking for improved relevance
"""

import math
from typing import Any, Dict, List, Optional

from core.logging_config import LogCategory, get_logger
from core.tracing import create_span, score_trace

logger = get_logger(LogCategory.RAG)


class BM25Retriever:
    """
    BM25 (Best Matching 25) keyword-based retriever.
    Implements the Okapi BM25 ranking function for better keyword matching.
    """

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        epsilon: float = 0.25,
    ):
        """
        Initialize BM25 retriever.

        Args:
            k1: Term frequency saturation parameter (typically 1.2-2.0)
            b: Length normalization parameter (typically 0.5-0.8)
            epsilon: Smoothing parameter for IDF calculation
        """
        self.k1 = k1
        self.b = b
        self.epsilon = epsilon

        # Document statistics
        self.doc_freqs: Dict[str, int] = {}  # term -> number of docs containing term
        self.doc_lengths: Dict[str, int] = {}  # doc_id -> document length (word count)
        self.avg_doc_length: float = 0.0
        self.num_docs: int = 0
        self.corpus: Dict[str, str] = {}  # doc_id -> text content
        self.idf_cache: Dict[str, float] = {}  # Cache for IDF values

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add documents to the BM25 index.

        Args:
            documents: List of documents with 'doc_id' and 'text' keys
        """
        with create_span("bm25_index_documents") as span:
            for doc in documents:
                doc_id = doc.get("doc_id", "")
                text = doc.get("text", doc.get("content", ""))

                if not doc_id or not text:
                    continue

                self.corpus[doc_id] = text
                words = self._tokenize(text)
                self.doc_lengths[doc_id] = len(words)

                # Update document frequency
                unique_words = set(words)
                for word in unique_words:
                    self.doc_freqs[word] = self.doc_freqs.get(word, 0) + 1

            self.num_docs = len(self.corpus)
            if self.doc_lengths:
                self.avg_doc_length = sum(self.doc_lengths.values()) / len(
                    self.doc_lengths
                )

            span.add_event(
                "index_built",
                output_data={
                    "num_docs": self.num_docs,
                    "avg_doc_length": self.avg_doc_length,
                    "vocab_size": len(self.doc_freqs),
                },
            )

            logger.info(
                f"BM25 index built: {self.num_docs} docs, "
                f"avg length: {self.avg_doc_length:.0f} words"
            )

    def search(
        self, query: str, top_k: int = 5, filter_metadata: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search documents using BM25 scoring.

        Args:
            query: Search query string
            top_k: Number of results to return
            filter_metadata: Optional metadata filters (not used in basic BM25)

        Returns:
            List of scored documents sorted by relevance
        """
        with create_span("bm25_search", input_data={"query": query, "top_k": top_k}) as span:
            if not self.corpus:
                logger.warning("BM25 index is empty")
                return []

            query_words = self._tokenize(query)
            scores: Dict[str, float] = {}

            for doc_id, text in self.corpus.items():
                score = self._calculate_bm25_score(query_words, doc_id, text)
                if score > 0:
                    scores[doc_id] = score

            # Sort by score descending
            sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

            results = []
            for doc_id, score in sorted_docs:
                results.append(
                    {
                        "doc_id": doc_id,
                        "content_preview": self.corpus[doc_id][:300],
                        "relevance_score": round(score, 4),
                        "metadata": {"source": "bm25"},
                    }
                )

            span.add_event(
                "search_completed",
                output_data={"result_count": len(results), "top_score": results[0]["relevance_score"] if results else 0},
            )

            return results

    def _calculate_bm25_score(
        self, query_words: List[str], doc_id: str, doc_text: str
    ) -> float:
        """
        Calculate BM25 score for a document given query terms.

        BM25 formula:
        Score(q,d) = Σ IDF(qi) * (tf(qi,d) * (k1 + 1)) / (tf(qi,d) + k1 * (1 - b + b * |d|/avgdl))

        Args:
            query_words: Tokenized query terms
            doc_id: Document identifier
            doc_text: Document text content

        Returns:
            BM25 relevance score
        """
        doc_words = self._tokenize(doc_text)
        doc_len = self.doc_lengths.get(doc_id, len(doc_words))

        # Calculate term frequencies in document
        tf = {}
        for word in doc_words:
            tf[word] = tf.get(word, 0) + 1

        score = 0.0
        for query_word in query_words:
            # Get document frequency
            df = self.doc_freqs.get(query_word, 0)

            if df == 0:
                continue

            # Calculate IDF with smoothing
            idf = self._calculate_idf(df)

            # Get term frequency in this document
            term_freq = tf.get(query_word, 0)

            if term_freq == 0:
                continue

            # Calculate BM25 term score
            numerator = term_freq * (self.k1 + 1)
            denominator = term_freq + self.k1 * (
                1 - self.b + self.b * (doc_len / self.avg_doc_length)
            )

            bm25_term_score = idf * (numerator / denominator)
            score += bm25_term_score

        return score

    def _calculate_idf(self, df: int) -> float:
        """
        Calculate Inverse Document Frequency with smoothing.

        IDF(q) = log((N - df + 0.5) / (df + 0.5) + 1)

        Args:
            df: Document frequency (number of docs containing term)

        Returns:
            IDF value
        """
        if df in self.idf_cache:
            return self.idf_cache[df]

        # Smoothed IDF calculation
        idf = math.log(
            (self.num_docs - df + 0.5) / (df + 0.5) + self.epsilon
        )

        self.idf_cache[df] = max(idf, 0.0)  # Ensure non-negative
        return self.idf_cache[df]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        Simple tokenization: lowercase and split on whitespace/punctuation.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        import re

        # Convert to lowercase and extract words
        text = text.lower()
        tokens = re.findall(r"\b\w+\b", text)

        # Filter out very short tokens and common stop words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after",
        }

        return [t for t in tokens if len(t) > 2 and t not in stop_words]


class MMRReranker:
    """
    Maximal Marginal Relevance (MMR) reranker.
    Balances relevance and diversity in search results.

    MMR selects items that are both relevant to the query
    and dissimilar to already selected items.
    """

    def __init__(self, lambda_param: float = 0.7):
        """
        Initialize MMR reranker.

        Args:
            lambda_param: Trade-off parameter between relevance and diversity
                         (0.0 = pure diversity, 1.0 = pure relevance)
        """
        if not 0 <= lambda_param <= 1:
            raise ValueError("lambda_param must be between 0 and 1")

        self.lambda_param = lambda_param

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using MMR algorithm.

        Args:
            query: Original search query
            documents: List of candidate documents with 'relevance_score'
            top_k: Number of documents to return after reranking

        Returns:
            Reranked list of documents
        """
        with create_span("mmr_reranking", input_data={
            "query": query,
            "candidate_count": len(documents),
            "top_k": top_k,
            "lambda": self.lambda_param,
        }) as span:
            if not documents or top_k <= 0:
                return []

            # If we have fewer candidates than top_k, return all
            if len(documents) <= top_k:
                return documents

            selected = []
            remaining = documents.copy()

            # Greedily select documents
            for _ in range(top_k):
                if not remaining:
                    break

                best_idx = self._select_best_mmr(
                    query, remaining, selected
                )

                if best_idx >= 0:
                    selected.append(remaining.pop(best_idx))

            span.add_event(
                "reranking_completed",
                output_data={
                    "selected_count": len(selected),
                    "diversity_improvement": self._calculate_diversity(selected),
                },
            )

            return selected

    def _select_best_mmr(
        self,
        query: str,
        remaining: List[Dict[str, Any]],
        selected: List[Dict[str, Any]],
    ) -> int:
        """
        Select the document with highest MMR score.

        MMR = argmax [ λ * Rel(d,q) - (1-λ) * max Sim(d, d_selected) ]

        Args:
            query: Search query
            remaining: Remaining candidate documents
            selected: Already selected documents

        Returns:
            Index of best document in remaining list
        """
        best_score = float("-inf")
        best_idx = -1

        for i, doc in enumerate(remaining):
            # Relevance to query (use existing relevance_score)
            rel_score = doc.get("relevance_score", 0.0)

            # Maximum similarity to already selected documents
            max_sim = 0.0
            if selected:
                similarities = [
                    self._calculate_similarity(doc, sel_doc)
                    for sel_doc in selected
                ]
                max_sim = max(similarities) if similarities else 0.0

            # MMR score
            mmr_score = (
                self.lambda_param * rel_score
                - (1 - self.lambda_param) * max_sim
            )

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i

        return best_idx

    @staticmethod
    def _calculate_similarity(
        doc1: Dict[str, Any], doc2: Dict[str, Any]
    ) -> float:
        """
        Calculate similarity between two documents using Jaccard similarity.

        Args:
            doc1: First document
            doc2: Second document

        Returns:
            Similarity score (0-1)
        """
        text1 = doc1.get("content_preview", "").lower()
        text2 = doc2.get("content_preview", "").lower()

        # Simple word-level Jaccard similarity
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    @staticmethod
    def _calculate_diversity(documents: List[Dict[str, Any]]) -> float:
        """
        Calculate average pairwise diversity of selected documents.

        Args:
            documents: List of documents

        Returns:
            Average diversity score (0-1, higher = more diverse)
        """
        if len(documents) < 2:
            return 1.0

        total_diversity = 0.0
        pair_count = 0

        for i in range(len(documents)):
            for j in range(i + 1, len(documents)):
                similarity = MMRReranker._calculate_similarity(
                    documents[i], documents[j]
                )
                total_diversity += (1 - similarity)
                pair_count += 1

        return total_diversity / pair_count if pair_count > 0 else 1.0


class HybridRetriever:
    """
    Hybrid retriever combining vector search and BM25 keyword search.
    Implements reciprocal rank fusion for score combination.
    """

    def __init__(
        self,
        vector_retriever: Any,
        bm25_retriever: BM25Retriever,
        alpha: float = 0.7,
        beta: float = 0.3,
        use_mmr: bool = True,
        mmr_lambda: float = 0.7,
    ):
        """
        Initialize hybrid retriever.

        Args:
            vector_retriever: Vector-based retriever (e.g., LanceDB)
            bm25_retriever: BM25 keyword retriever
            alpha: Weight for vector search scores (0-1)
            beta: Weight for BM25 scores (0-1), should satisfy alpha + beta = 1
            use_mmr: Whether to apply MMR reranking
            mmr_lambda: MMR lambda parameter
        """
        if not 0 <= alpha <= 1 or not 0 <= beta <= 1:
            raise ValueError("alpha and beta must be between 0 and 1")

        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.alpha = alpha
        self.beta = beta
        self.use_mmr = use_mmr
        self.mmr_reranker = MMRReranker(lambda_param=mmr_lambda)

        logger.info(
            f"HybridRetriever initialized: alpha={alpha}, beta={beta}, "
            f"use_mmr={use_mmr}"
        )

    async def search(
        self,
        query: str,
        top_k: int = 5,
        mode: str = "hybrid",
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector and BM25 results.

        Args:
            query: Search query
            top_k: Number of results to return
            mode: Search mode ('vector', 'keyword', 'hybrid')
            filter_metadata: Optional metadata filters

        Returns:
            Combined and ranked search results
        """
        with create_span("hybrid_search", input_data={
            "query": query,
            "top_k": top_k,
            "mode": mode,
        }) as main_span:
            # Retrieve from both sources
            vector_results = []
            bm25_results = []

            if mode in ["vector", "hybrid"]:
                vector_span = create_span("vector_search_component")
                try:
                    # Call vector retriever (assumes it has search method)
                    if hasattr(self.vector_retriever, "search"):
                        vector_results = await self._call_vector_search(
                            query, top_k * 2, filter_metadata
                        )
                    vector_span.end(
                        output_data={"result_count": len(vector_results)}
                    )
                except Exception as e:
                    logger.error(f"Vector search failed: {e}")
                    vector_span.end(output_data={"error": str(e)})

            if mode in ["keyword", "hybrid"]:
                bm25_span = create_span("bm25_search_component")
                try:
                    bm25_results = self.bm25_retriever.search(
                        query, top_k * 2, filter_metadata
                    )
                    bm25_span.end(
                        output_data={"result_count": len(bm25_results)}
                    )
                except Exception as e:
                    logger.error(f"BM25 search failed: {e}")
                    bm25_span.end(output_data={"error": str(e)})

            # Combine results based on mode
            if mode == "vector":
                combined = vector_results[:top_k]
            elif mode == "keyword":
                combined = bm25_results[:top_k]
            else:  # hybrid
                combined = self._fuse_results(
                    vector_results, bm25_results, top_k
                )

            # Apply MMR reranking if enabled
            if self.use_mmr and len(combined) > top_k:
                rerank_span = create_span("mmr_reranking_component")
                combined = self.mmr_reranker.rerank(query, combined, top_k)
                rerank_span.end(
                    output_data={"reranked_count": len(combined)}
                )
            else:
                combined = combined[:top_k]

            # Calculate average relevance
            avg_relevance = (
                sum(doc["relevance_score"] for doc in combined) / len(combined)
                if combined
                else 0.0
            )

            score_trace("hybrid_retrieval_relevance", avg_relevance)

            main_span.end(
                output_data={
                    "result_count": len(combined),
                    "vector_count": len(vector_results),
                    "bm25_count": len(bm25_results),
                    "avg_relevance": round(avg_relevance, 4),
                }
            )

            return combined

    async def _call_vector_search(
        self, query: str, top_k: int, filter_metadata: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Call vector retriever's search method.

        Args:
            query: Search query
            top_k: Number of results
            filter_metadata: Metadata filters

        Returns:
            Vector search results
        """
        # Handle different vector retriever interfaces
        if hasattr(self.vector_retriever, "query_knowledge"):
            # RAGKnowledgeBase interface
            result = await self.vector_retriever.query_knowledge(
                query, top_k=top_k
            )
            return result.get("retrieved_documents", [])
        elif hasattr(self.vector_retriever, "search"):
            # Direct search interface
            return await self.vector_retriever.search(
                query, top_k=top_k, filter_metadata=filter_metadata
            )
        else:
            raise ValueError("Unsupported vector retriever interface")

    def _fuse_results(
        self,
        vector_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        Fuse vector and BM25 results using Reciprocal Rank Fusion (RRF).

        RRF formula:
        RRF_score(d) = Σ 1 / (k + rank_i(d))

        Args:
            vector_results: Results from vector search
            bm25_results: Results from BM25 search
            top_k: Number of final results

        Returns:
            Fused and ranked results
        """
        with create_span("score_fusion") as span:
            # Create ranking maps
            vector_rank = {
                doc["doc_id"]: idx + 1
                for idx, doc in enumerate(vector_results)
            }
            bm25_rank = {
                doc["doc_id"]: idx + 1
                for idx, doc in enumerate(bm25_results)
            }

            # Get all unique document IDs
            all_doc_ids = set(vector_rank.keys()) | set(bm25_rank.keys())

            # Calculate RRF scores with weighted combination
            k_constant = 60  # Standard RRF constant
            fused_scores: Dict[str, float] = {}

            for doc_id in all_doc_ids:
                vector_score = 0.0
                bm25_score = 0.0

                # Vector component
                if doc_id in vector_rank:
                    vector_score = self.alpha / (k_constant + vector_rank[doc_id])

                # BM25 component
                if doc_id in bm25_rank:
                    bm25_score = self.beta / (k_constant + bm25_rank[doc_id])

                fused_scores[doc_id] = vector_score + bm25_score

            # Sort by fused score
            sorted_docs = sorted(
                fused_scores.items(), key=lambda x: x[1], reverse=True
            )[:top_k]

            # Build result list
            results_map = {}
            for doc in vector_results + bm25_results:
                results_map[doc["doc_id"]] = doc

            fused_results = []
            for doc_id, score in sorted_docs:
                if doc_id in results_map:
                    doc = results_map[doc_id].copy()
                    doc["relevance_score"] = round(score, 6)
                    doc["metadata"]["fusion_method"] = "rrf"
                    fused_results.append(doc)

            span.add_event(
                "fusion_completed",
                output_data={
                    "fused_count": len(fused_results),
                    "top_fused_score": fused_results[0]["relevance_score"]
                    if fused_results
                    else 0,
                },
            )

            return fused_results
