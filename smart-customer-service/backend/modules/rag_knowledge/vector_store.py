"""
Vector store abstraction with multiple backend support
Supports ChromaDB (local) and Pinecone (cloud)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar
from uuid import uuid4

from core.logging_config import LogCategory, get_logger
from core.tracing import create_span, score_trace

logger = get_logger(LogCategory.RAG)

T = TypeVar("T")


@dataclass
class SearchResult:
    doc_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    distance: Optional[float] = None


class BaseVectorStore(ABC):
    """Abstract base class for vector stores"""

    @abstractmethod
    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        pass

    @abstractmethod
    def delete_documents(self, doc_ids: List[str]) -> None:
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        pass

    @abstractmethod
    def update_document(
        self, doc_id: str, new_content: str, new_embedding: List[float]
    ) -> None:
        pass

    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def count(self) -> int:
        pass


class ChromaDBAdapter(BaseVectorStore):
    """ChromaDB vector store adapter for local deployment"""

    def __init__(
        self,
        collection_name: str = "documents",
        persist_directory: Optional[str] = None,
        distance_func: str = "cosine",
    ):
        import chromadb

        self._client_settings = None
        if persist_directory:
            import chromadb.config

            self._client_settings = chromadb.config.Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False,
            )

        self._client = chromadb.Client(self._client_settings)
        self.collection_name = collection_name
        self.distance_func = distance_func

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": distance_func},
        )

        logger.info(f"Initialized ChromaDB collection: {collection_name}")

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        with create_span("chroma_add_documents") as span:
            if ids is None:
                ids = [str(uuid4()) for _ in documents]

            contents = [doc.get("content", doc.get("text", "")) for doc in documents]
            metadatas = [doc.get("metadata", {}) for doc in documents]

            self._collection.add(
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas,
                ids=ids,
            )

            span.add_event("documents_added", output_data={"count": len(ids)})
            score_trace("chroma_insert_latency_ms", 0)

            return ids

    def delete_documents(self, doc_ids: List[str]) -> None:
        with create_span("chroma_delete_documents") as span:
            self._collection.delete(ids=doc_ids)
            span.add_event("documents_deleted", output_data={"count": len(doc_ids)})

    def search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        with create_span("chroma_search") as span:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"],
            )

            search_results = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i] if "distances" in results else None
                    score = 1 - distance if distance is not None else 0.0

                    search_results.append(
                        SearchResult(
                            doc_id=doc_id,
                            content=results["documents"][0][i] if "documents" in results else "",
                            score=score,
                            metadata=results["metadatas"][0][i] if "metadatas" in results else {},
                            distance=distance,
                        )
                    )

            span.add_event(
                "search_completed",
                output_data={"result_count": len(search_results), "k": k},
            )

            return search_results

    def update_document(
        self, doc_id: str, new_content: str, new_embedding: List[float]
    ) -> None:
        with create_span("chroma_update_document") as span:
            self._collection.update(
                ids=[doc_id],
                documents=[new_content],
                embeddings=[new_embedding],
            )
            span.add_event("document_updated", output_data={"doc_id": doc_id})

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = self._collection.get(ids=[doc_id], include=["documents", "metadatas"])
            if result["ids"]:
                return {
                    "id": result["ids"][0],
                    "content": result["documents"][0] if "documents" in result else "",
                    "metadata": result["metadatas"][0] if "metadatas" in result else {},
                }
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {e}")
        return None

    def count(self) -> int:
        return self._collection.count()


class PineconeAdapter(BaseVectorStore):
    """Pinecone vector store adapter for cloud deployment"""

    def __init__(
        self,
        index_name: str = "documents",
        environment: Optional[str] = None,
        api_key: Optional[str] = None,
        namespace: str = "",
        batch_size: int = 100,
    ):
        import os

        try:
            from pinecone import Pinecone
        except ImportError:
            raise ImportError("pinecone-client is required. Install with: pip install pinecone-client")

        env_api_key = api_key or os.getenv("PINECONE_API_KEY", "")
        env_environment = environment or os.getenv("PINECONE_ENVIRONMENT", "")

        if not env_api_key:
            raise ValueError("PINECONE_API_KEY is required")

        self.index_name = index_name
        self.namespace = namespace
        self.batch_size = batch_size

        self._client = Pinecone(api_key=env_api_key)

        try:
            self._index = self._client.Index(index_name)
            logger.info(f"Connected to Pinecone index: {index_name}")
        except Exception as e:
            logger.warning(f"Index {index_name} not found, will use upsert: {e}")
            self._index = None

    def _ensure_index(self):
        if self._index is None:
            self._index = self._client.Index(self.index_name)

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        with create_span("pinecone_add_documents") as span:
            self._ensure_index()

            if ids is None:
                ids = [str(uuid4()) for _ in documents]

            vectors = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                content = doc.get("content", doc.get("text", ""))
                metadata = doc.get("metadata", {})
                metadata["text"] = content

                vectors.append({
                    "id": ids[i],
                    "values": embedding,
                    "metadata": metadata,
                })

            for i in range(0, len(vectors), self.batch_size):
                batch = vectors[i : i + self.batch_size]
                self._index.upsert(vectors=batch, namespace=self.namespace)

            span.add_event("documents_added", output_data={"count": len(ids)})
            return ids

    def delete_documents(self, doc_ids: List[str]) -> None:
        with create_span("pinecone_delete_documents") as span:
            self._ensure_index()

            for i in range(0, len(doc_ids), self.batch_size):
                batch = doc_ids[i : i + self.batch_size]
                self._index.delete(ids=batch, namespace=self.namespace)

            span.add_event("documents_deleted", output_data={"count": len(doc_ids)})

    def search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        with create_span("pinecone_search") as span:
            self._ensure_index()

            response = self._index.query(
                vector=query_embedding,
                top_k=k,
                namespace=self.namespace,
                include_metadata=True,
                filter=filter_metadata,
            )

            search_results = []
            for match in response.matches or []:
                metadata = match.metadata or {}
                content = metadata.pop("text", "")

                search_results.append(
                    SearchResult(
                        doc_id=match.id,
                        content=content,
                        score=match.score,
                        metadata=metadata,
                        distance=1 - match.score,
                    )
                )

            span.add_event(
                "search_completed",
                output_data={"result_count": len(search_results), "k": k},
            )

            return search_results

    def update_document(
        self, doc_id: str, new_content: str, new_embedding: List[float]
    ) -> None:
        with create_span("pinecone_update_document") as span:
            self._ensure_index()

            existing = self.get_document(doc_id)
            if existing:
                metadata = existing.get("metadata", {})
            else:
                metadata = {}

            metadata["text"] = new_content

            self._index.upsert(
                vectors=[{
                    "id": doc_id,
                    "values": new_embedding,
                    "metadata": metadata,
                }],
                namespace=self.namespace,
            )

            span.add_event("document_updated", output_data={"doc_id": doc_id})

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        try:
            self._ensure_index()
            response = self._index.fetch(ids=[doc_id], namespace=self.namespace)

            if response.vectors and doc_id in response.vectors:
                vector = response.vectors[doc_id]
                metadata = vector.metadata or {}
                content = metadata.pop("text", "")

                return {
                    "id": doc_id,
                    "content": content,
                    "metadata": metadata,
                    "embedding": vector.values,
                }
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {e}")
        return None

    def count(self) -> int:
        self._ensure_index()
        stats = self._index.describe_index_stats()
        return stats.total_record_count


class LanceDBAdapter(BaseVectorStore):
    """LanceDB vector store adapter for high-performance local deployment"""

    def __init__(
        self,
        table_name: str = "documents",
        persist_directory: str = ".lancedb",
        embedding_dim: int = 1536,
    ):
        try:
            import lancedb
            from lancedb.embeddings import get_registry
        except ImportError:
            raise ImportError("lancedb is required. Install with: pip install lancedb")

        self.table_name = table_name
        self.persist_directory = persist_directory
        self.embedding_dim = embedding_dim

        self._db = lancedb.connect(persist_directory)
        self._embedding = get_registry().get("openai").create(
            model="text-embedding-3-small"
        )

        self._table = self._db.create_table(
            table_name,
            data=[{"doc_id": "init", "content": "init", "vector": [0.0] * embedding_dim}],
            mode="overwrite",
        )

        logger.info(f"Initialized LanceDB table: {table_name}")

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        with create_span("lancedb_add_documents") as span:
            if ids is None:
                ids = [str(uuid4()) for _ in documents]

            records = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                content = doc.get("content", doc.get("text", ""))
                metadata = doc.get("metadata", {})

                records.append({
                    "doc_id": ids[i],
                    "content": content,
                    "vector": embedding,
                    "metadata": metadata,
                })

            self._table.add(records)

            span.add_event("documents_added", output_data={"count": len(ids)})
            return ids

    def delete_documents(self, doc_ids: List[str]) -> None:
        with create_span("lancedb_delete_documents") as span:
            self._table.delete(f"doc_id IN ({','.join(repr(id) for id in doc_ids)})")
            span.add_event("documents_deleted", output_data={"count": len(doc_ids)})

    def search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        with create_span("lancedb_search") as span:
            results = (
                self._table.search(query_embedding)
                .limit(k)
                .to_list()
            )

            search_results = []
            for result in results:
                search_results.append(
                    SearchResult(
                        doc_id=result["doc_id"],
                        content=result["content"],
                        score=1 - result.get("_distance", 0),
                        metadata=result.get("metadata", {}),
                        distance=result.get("_distance"),
                    )
                )

            span.add_event(
                "search_completed",
                output_data={"result_count": len(search_results), "k": k},
            )

            return search_results

    def update_document(
        self, doc_id: str, new_content: str, new_embedding: List[float]
    ) -> None:
        with create_span("lancedb_update_document") as span:
            self._table.update(
                where=f"doc_id = '{doc_id}'",
                values={
                    "content": new_content,
                    "vector": new_embedding,
                },
            )
            span.add_event("document_updated", output_data={"doc_id": doc_id})

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        try:
            results = self._table.filter(f"doc_id = '{doc_id}'").to_list()
            if results:
                result = results[0]
                return {
                    "id": result["doc_id"],
                    "content": result["content"],
                    "metadata": result.get("metadata", {}),
                    "embedding": result.get("vector"),
                }
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {e}")
        return None

    def count(self) -> int:
        return len(self._table.to_list())


def create_vector_store(
    provider: str = "chroma",
    **kwargs,
) -> BaseVectorStore:
    """
    Factory function to create a vector store by provider name.

    Args:
        provider: Provider name (chroma, pinecone, lancedb)
        **kwargs: Provider-specific configuration

    Returns:
        BaseVectorStore instance
    """
    providers = {
        "chroma": ChromaDBAdapter,
        "chromadb": ChromaDBAdapter,
        "pinecone": PineconeAdapter,
        "lance": LanceDBAdapter,
        "lancedb": LanceDBAdapter,
    }

    provider_lower = provider.lower().strip()
    adapter_class = providers.get(provider_lower)

    if not adapter_class:
        available = ", ".join(providers.keys())
        raise ValueError(
            f"Unknown vector store provider: {provider}. Available: {available}"
        )

    return adapter_class(**kwargs)


def list_vector_store_providers() -> List[str]:
    """Return list of available vector store providers"""
    return ["chroma", "pinecone", "lancedb"]
