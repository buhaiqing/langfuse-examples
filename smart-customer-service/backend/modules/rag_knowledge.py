"""
RAG knowledge base module with Langfuse tracing
Retrieves technical documentation and generates answers
Supports local files, remote URLs, and OpenAI embeddings
"""

import hashlib
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import lancedb
from lancedb.embeddings import get_registry
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from lxml import html

from config.settings import OPENAI_API_KEY
from core.logging_config import LogCategory, get_logger
from core.scoring import score_retrieval_relevance
from core.tracing import add_event, create_span, score_trace

logger = get_logger(LogCategory.RAG)


class DocumentSourceType(Enum):
    """Supported document source types"""

    LOCAL_FILE = "local_file"
    REMOTE_URL = "remote_url"
    DIRECT_TEXT = "direct_text"
    DIRECTORY = "directory"


@dataclass
class DocumentMetadata:
    """Metadata for a document"""

    source: str
    source_type: DocumentSourceType
    title: str | None = None
    category: str | None = None
    version: str | None = None
    created_at: str | None = None
    author: str | None = None
    tags: list[str] | None = None


class DocumentLoader(ABC):
    """Abstract base class for document loaders"""

    @abstractmethod
    async def load(self, source: str) -> list[dict[str, Any]]:
        """Load documents from source"""
        pass


class LocalFileLoader(DocumentLoader):
    """Loader for local files (markdown, text, HTML)"""

    SUPPORTED_EXTENSIONS = {".md", ".txt", ".html", ".htm", ".rst"}

    async def load(self, source: str) -> list[dict[str, Any]]:
        """Load documents from local file"""
        path = Path(source)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")

        if path.suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        return [
            {
                "text": content,
                "doc_id": self._generate_doc_id(content),
                "source": str(path.absolute()),
                "source_type": DocumentSourceType.LOCAL_FILE.value,
                "title": path.stem,
                "category": self._infer_category(path),
            }
        ]

    def _generate_doc_id(self, content: str) -> str:
        """Generate unique document ID from content hash"""
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _infer_category(self, path: Path) -> str:
        """Infer category from file path"""
        path_str = str(path).lower()
        if "auth" in path_str or "login" in path_str or "password" in path_str:
            return "authentication"
        elif "ticket" in path_str or "support" in path_str:
            return "tickets"
        elif "api" in path_str:
            return "api"
        elif "billing" in path_str or "payment" in path_str:
            return "billing"
        elif "product" in path_str:
            return "product"
        return "general"


class DirectoryLoader(DocumentLoader):
    """Loader for directories containing multiple documents"""

    def __init__(self):
        self.file_loader = LocalFileLoader()

    async def load(self, source: str) -> list[dict[str, Any]]:
        """Load all supported documents from a directory"""
        dir_path = Path(source)

        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {source}")

        documents = []
        for ext in LocalFileLoader.SUPPORTED_EXTENSIONS:
            for file_path in dir_path.rglob(f"*{ext}"):
                try:
                    docs = await self.file_loader.load(str(file_path))
                    documents.extend(docs)
                except Exception as e:
                    logger.warning(f"Failed to load file {file_path}: {e}")

        logger.info(f"Loaded {len(documents)} documents from directory {source}")
        return documents


class RemoteURLLoader(DocumentLoader):
    """Loader for remote URLs (web scraping)"""

    async def load(self, source: str) -> list[dict[str, Any]]:
        """Load document from remote URL"""
        if not source.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {source}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(source)
                response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            if "text/html" in content_type:
                text = self._extract_text_from_html(response.text)
            else:
                text = response.text

            if len(text) < 100:
                raise ValueError(f"Content too short from URL: {source}")

            return [
                {
                    "text": text,
                    "doc_id": self._generate_doc_id(text),
                    "source": source,
                    "source_type": DocumentSourceType.REMOTE_URL.value,
                    "title": self._extract_title(response.text) or urlparse(source).path,
                    "category": "web",
                }
            ]
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to fetch URL {source}: {e}")

    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract plain text from HTML"""
        try:
            tree = html.fromstring(html_content)
            for script in tree.xpath("//script|//style"):
                script.getparent().remove(script)
            text = tree.text_content()
            return " ".join(text.split())
        except Exception:
            from html.parser import HTMLParser

            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []

                def handle_data(self, data):
                    self.text.append(data)

            parser = TextExtractor()
            parser.feed(html_content)
            return " ".join(parser.text)

    def _extract_title(self, html_content: str) -> str | None:
        """Extract title from HTML"""
        try:
            tree = html.fromstring(html_content)
            title_elem = tree.xpath("//title")
            if title_elem:
                return title_elem[0].text_content().strip()
        except Exception:
            pass
        return None

    def _generate_doc_id(self, content: str) -> str:
        """Generate unique document ID from content hash"""
        return hashlib.md5(content.encode()).hexdigest()[:12]


class DirectTextLoader(DocumentLoader):
    """Loader for direct text content"""

    async def load(self, source: str) -> list[dict[str, Any]]:
        """Load document from direct text input"""
        return [
            {
                "text": source,
                "doc_id": f"doc_{uuid.uuid4().hex[:12]}",
                "source": "direct_input",
                "source_type": DocumentSourceType.DIRECT_TEXT.value,
                "title": source[:50] + "..." if len(source) > 50 else source,
                "category": "general",
            }
        ]


class DocumentLoaderFactory:
    """Factory for creating document loaders"""

    @staticmethod
    def create(source: str) -> DocumentLoader:
        """Create appropriate loader based on source"""
        if source.startswith(("http://", "https://")):
            return RemoteURLLoader()
        elif os.path.isdir(source):
            return DirectoryLoader()
        elif os.path.isfile(source):
            return LocalFileLoader()
        else:
            return DirectTextLoader()


class RAGKnowledgeBase:
    """RAG-based knowledge retrieval system with Langfuse tracing"""

    def __init__(self, docs_directory: str | None = None):
        logger.info("Initializing RAG Knowledge Base")
        start_time = time.time()

        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3, api_key=OPENAI_API_KEY)
        self.db = lancedb.connect(".lancedb")
        logger.debug("Connected to LanceDB database")

        self._initialize_embeddings()
        self._initialize_table()
        self._load_documents(docs_directory)

        logger.info(f"RAG Knowledge Base initialized in {time.time() - start_time:.2f}s")

    def _initialize_embeddings(self):
        """Initialize OpenAI embeddings"""
        try:
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set")

            self.embedding = get_registry().get("openai").create(model="text-embedding-3-small")
            self.use_embeddings = True
            logger.info("Successfully initialized OpenAI embedding (text-embedding-3-small)")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI embedding: {e}")
            logger.info("Using keyword-based fallback for retrieval")
            self.embedding = None
            self.use_embeddings = False

    def _initialize_table(self):
        """Initialize LanceDB table"""
        try:
            self.table = self.db.open_table("tech_support_docs")
            logger.info("Opened existing LanceDB table")
        except Exception:
            try:
                self.table = self.db.create_table(
                    "tech_support_docs",
                    data=[],
                    mode="create",
                )
                logger.info("Created new LanceDB table")
            except Exception as e:
                logger.error(f"Failed to create LanceDB table: {e}")
                raise

    def _load_documents(self, docs_directory: str | None):
        """Load documents from configured sources"""
        docs_loaded = False

        if docs_directory and os.path.isdir(docs_directory):
            try:
                loader = DirectoryLoader()
                docs = asyncio.run(loader.load(docs_directory))
                if docs:
                    self._add_documents_to_lancedb(docs)
                    docs_loaded = True
                    logger.info(f"Loaded {len(docs)} documents from directory: {docs_directory}")
            except Exception as e:
                logger.warning(f"Failed to load documents from directory: {e}")

        if not docs_loaded:
            self._initialize_sample_documents()

    def _add_documents_to_lancedb(self, documents: list[dict[str, Any]]):
        """Add documents to LanceDB with embeddings"""
        if not documents:
            return

        try:
            if self.use_embeddings and hasattr(self.embedding, 'embed_query'):
                texts = [doc["text"] for doc in documents]
                embeddings = self.embedding.embed_batch(texts)

                for doc, embedding in zip(documents, embeddings):
                    doc["vector"] = embedding

            for doc in documents:
                doc["version"] = doc.get("version", "v1.0")
                doc["category"] = doc.get("category", "general")

            self.table.add(documents)
            logger.info(f"Added {len(documents)} documents to LanceDB")
        except Exception as e:
            logger.error(f"Failed to add documents to LanceDB: {e}")

    def _initialize_sample_documents(self):
        """Initialize with sample technical documentation"""
        logger.debug("Initializing sample technical documentation")
        sample_docs = [
            {
                "text": """API Authentication - 403 Forbidden Error

When you receive a 403 Forbidden error from the API, it means your request lacks valid authentication credentials or sufficient permissions.

Common causes:
1. Missing or invalid API key in the request header
2. API key doesn't have permission for this endpoint
3. User role doesn't have access to this resource
4. IP address not whitelisted

Solution:
- Verify your API key is included in the Authorization header
- Check that your API key has the required scopes
- Contact your administrator to verify your user role permissions
- Ensure your IP is in the allowed list""",
                "doc_id": "auth_403_guide",
                "version": "v2.3",
                "category": "authentication",
            },
            {
                "text": """How to Query Ticket Status

You can check the status of your support ticket using the following methods:

Method 1: API Endpoint
GET /api/v2/tickets/{ticket_id}
Headers: Authorization: Bearer {your_api_key}

Response includes:
- status: open, in_progress, resolved, closed
- priority: low, medium, high, critical
- assigned_to: Support agent name
- last_updated: Timestamp of last update
- comments: Array of conversation history

Method 2: Web Portal
Login to support portal at support.example.com
Navigate to "My Tickets" section
Search by ticket ID or filter by status""",
                "doc_id": "ticket_status_guide",
                "version": "v2.3",
                "category": "tickets",
            },
            {
                "text": """Rate Limiting and Throttling

Our API implements rate limiting to ensure fair usage and system stability.

Rate Limits by Plan:
- Free: 100 requests/hour
- Basic: 1000 requests/hour
- Professional: 10000 requests/hour
- Enterprise: Custom limits

When rate limited, you'll receive:
- HTTP Status: 429 Too Many Requests
- Header: Retry-After: seconds to wait
- Response body: {"error": "rate_limit_exceeded", "retry_after": 60}

Best Practices:
- Implement exponential backoff for retries
- Cache responses when possible
- Use webhooks instead of polling
- Monitor your usage via the dashboard""",
                "doc_id": "rate_limiting_guide",
                "version": "v2.3",
                "category": "api_usage",
            },
            {
                "text": """Account Management and Profile Settings

Your account dashboard provides the following features:

1. Profile Management
   - Update your name, email, and profile picture
   - Change your password
   - Set up two-factor authentication (2FA)

2. API Key Management
   - Generate new API keys
   - Set expiration dates for keys
   - Configure key permissions and scopes
   - Monitor key usage

3. Team Management (Enterprise)
   - Invite team members
   - Assign roles and permissions
   - View team activity logs

4. Billing and Subscription
   - View current plan and usage
   - Upgrade or downgrade plan
   - Update payment method
   - Download invoices""",
                "doc_id": "account_management_guide",
                "version": "v2.3",
                "category": "account",
            },
            {
                "text": """Getting Started with the API

This guide will help you make your first API call.

Step 1: Get Your API Key
1. Log in to your dashboard
2. Go to Settings > API Keys
3. Click "Generate New Key"
4. Copy and securely store your key

Step 2: Make Your First Request
Base URL: https://api.example.com/v2

Example GET request:
curl -X GET https://api.example.com/v2/users/me \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json"

Step 3: Understand Response Codes
- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Rate Limited
- 500: Server Error

Step 4: SDK Installation
pip install example-api-sdk
npm install example-api-sdk

For more examples, visit our documentation at docs.example.com""",
                "doc_id": "getting_started_guide",
                "version": "v2.3",
                "category": "getting_started",
            },
        ]

        if sample_docs:
            self._add_documents_to_lancedb(sample_docs)
            logger.info(f"Added {len(sample_docs)} sample documents to knowledge base")

    async def add_documents(
        self,
        sources: list[str],
        category: str | None = None,
    ) -> int:
        """
        Add documents from multiple sources

        Args:
            sources: List of file paths or URLs
            category: Optional category to assign to all documents

        Returns:
            Number of documents added
        """
        all_docs = []
        for source in sources:
            try:
                loader = DocumentLoaderFactory.create(source)
                docs = await loader.load(source)
                if category:
                    for doc in docs:
                        doc["category"] = category
                all_docs.extend(docs)
            except Exception as e:
                logger.error(f"Failed to load document from {source}: {e}")

        if all_docs:
            self._add_documents_to_lancedb(all_docs)

        return len(all_docs)

    async def query_knowledge(
        self, user_query: str, session_id: str | None = None, top_k: int = 3
    ) -> dict[str, Any]:
        """
        Query knowledge base with full Langfuse tracing

        Args:
            user_query: User's question
            session_id: Session identifier
            top_k: Number of documents to retrieve

        Returns:
            Dictionary with answer and retrieved documents
        """
        start_time = time.time()
        logger.info(f"Querying knowledge base: '{user_query[:50]}...' (session: {session_id}, top_k: {top_k})")

        with create_span(
            name="rag_knowledge_query",
            input_data={"query": user_query, "top_k": top_k},
            metadata={"session_id": session_id},
        ) as main_span:

            rewrite_span = create_span(
                name="query_rewriting", input_data={"original_query": user_query}
            )
            logger.debug("Rewriting user query for better retrieval")
            rewritten_query = await self._rewrite_query(user_query)
            rewrite_span.end(
                output_data={"rewritten_query": rewritten_query},
                metadata={"model": "gpt-3.5-turbo"},
            )
            logger.debug(f"Query rewritten to: '{rewritten_query[:50]}...'")

            retrieval_span = create_span(
                name="vector_retrieval", input_data={"query": rewritten_query, "top_k": top_k}
            )

            retrieved_docs = await self._retrieve_documents(rewritten_query, top_k)

            retrieval_span.end(
                output_data={"retrieved_count": len(retrieved_docs), "documents": retrieved_docs}
            )

            add_event(
                name="documents_retrieved",
                output_data={
                    "doc_ids": [d["doc_id"] for d in retrieved_docs],
                    "scores": [d["relevance_score"] for d in retrieved_docs],
                },
            )

            generation_span = create_span(
                name="answer_generation",
                input_data={"query": user_query, "context_docs_count": len(retrieved_docs)},
                metadata={"model": "gpt-3.5-turbo", "temperature": 0.3},
            )

            logger.debug("Generating answer from retrieved documents")
            answer = await self._generate_answer(user_query, retrieved_docs)

            generation_span.end(
                output_data={"answer_length": len(answer), "has_citations": len(retrieved_docs) > 0}
            )

            processing_time = (time.time() - start_time) * 1000
            avg_relevance = (
                sum(d["relevance_score"] for d in retrieved_docs) / len(retrieved_docs)
                if retrieved_docs
                else 0
            )

            if retrieved_docs:
                score_retrieval_relevance(
                    avg_relevance, comment=f"Average relevance across {len(retrieved_docs)} docs"
                )

            score_trace(
                name="response_latency_ms",
                value=processing_time,
                data_type="NUMERIC",
                comment="Total RAG processing time",
            )

            main_span.end(
                output_data={
                    "answer": answer,
                    "retrieved_docs_count": len(retrieved_docs),
                    "avg_relevance": round(avg_relevance, 3),
                    "processing_time_ms": processing_time,
                }
            )

            logger.info(
                f"Query completed: {len(retrieved_docs)} docs retrieved, "
                f"avg relevance: {avg_relevance:.3f}, time: {processing_time:.0f}ms"
            )

            return {
                "answer": answer,
                "retrieved_documents": retrieved_docs,
                "processing_time_ms": processing_time,
            }

    async def _retrieve_documents(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Retrieve relevant documents using vector search or keyword fallback"""
        try:
            if self.use_embeddings and self.table is not None:
                results = self.table.search(query).limit(top_k).to_list()

                retrieved_docs = []
                for result in results:
                    retrieved_docs.append(
                        {
                            "doc_id": result.get("doc_id", "unknown"),
                            "content_preview": result.get("text", "")[:300],
                            "relevance_score": round(1.0 - result.get("_distance", 0), 3),
                            "metadata": {
                                "doc_id": result.get("doc_id", "unknown"),
                                "version": result.get("version", ""),
                                "category": result.get("category", ""),
                                "source": result.get("source", ""),
                            },
                        }
                    )
            else:
                retrieved_docs = await self._keyword_search(query, top_k)

            return retrieved_docs
        except Exception as e:
            logger.warning(f"Retrieval failed, using keyword fallback: {e}")
            return await self._keyword_search(query, top_k)

    async def _keyword_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Fallback keyword-based search when embeddings are not available"""
        try:
            all_docs = self.table.to_list() if self.table is not None else []
        except Exception:
            all_docs = []

        if not all_docs:
            return []

        query_words = set(query.lower().split())
        scored_docs = []

        for doc in all_docs:
            text_words = set(doc.get("text", "").lower().split())
            common_words = query_words & text_words
            if common_words:
                score = len(common_words) / len(query_words)
                scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, doc in scored_docs[:top_k]:
            results.append(
                {
                    "doc_id": doc.get("doc_id", "unknown"),
                    "content_preview": doc.get("text", "")[:300],
                    "relevance_score": round(score, 3),
                    "metadata": {
                        "doc_id": doc.get("doc_id", "unknown"),
                        "version": doc.get("version", ""),
                        "category": doc.get("category", ""),
                        "source": doc.get("source", ""),
                    },
                }
            )

        return results

    async def _rewrite_query(self, query: str) -> str:
        """Rewrite user query for better retrieval"""
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a query rewriting assistant. Rewrite the user's question to be more specific and keyword-rich for better document retrieval. Keep it concise.",
                ),
                ("human", "{query}"),
            ]
        )

        chain = prompt | self.llm
        response = await chain.ainvoke({"query": query})
        return response.content.strip()

    async def _generate_answer(self, query: str, docs: list[dict]) -> str:
        """Generate answer based on retrieved documents"""
        if not docs:
            return "抱歉，我在知识库中未找到相关信息。建议您提供更多细节或联系人工客服获取帮助。"

        context = "\n\n".join(
            [
                f"Document {i+1} (Category: {doc['metadata'].get('category', 'general')}):\n{doc['content_preview']}"
                for i, doc in enumerate(docs[:3])
            ]
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是一个专业的技术支持助手。基于提供的文档内容，准确回答用户的问题。

要求：
1. 只基于提供的文档内容回答
2. 如果文档中没有相关信息，明确说明
3. 提供清晰、分步骤的解决方案
4. 引用相关文档来源
5. 保持专业、友好的语气""",
                ),
                (
                    "human",
                    """用户问题：{query}

参考文档：
{context}

请提供详细的解答：""",
                ),
            ]
        )

        chain = prompt | self.llm
        response = await chain.ainvoke({"query": query, "context": context})

        return response.content.strip()

    def get_document_count(self) -> int:
        """Get total number of documents in knowledge base"""
        try:
            return len(self.table.to_list()) if self.table is not None else 0
        except Exception:
            return 0


import asyncio


rag_system = RAGKnowledgeBase()


async def query_knowledge_base(
    user_query: str, session_id: str | None = None, top_k: int = 3
) -> dict[str, Any]:
    """
    Convenience function to query knowledge base

    Args:
        user_query: User's question
        session_id: Session identifier
        top_k: Number of documents to retrieve

    Returns:
        Dictionary with answer and retrieved documents
    """
    return await rag_system.query_knowledge(user_query, session_id, top_k)


async def add_knowledge_documents(
    sources: list[str], category: str | None = None
) -> int:
    """
    Add documents to knowledge base

    Args:
        sources: List of file paths or URLs
        category: Optional category to assign

    Returns:
        Number of documents added
    """
    return await rag_system.add_documents(sources, category)


def get_knowledge_base_stats() -> dict[str, Any]:
    """Get knowledge base statistics"""
    return {
        "document_count": rag_system.get_document_count(),
        "use_embeddings": rag_system.use_embeddings,
    }


__all__ = [
    "RAGKnowledgeBase",
    "DocumentLoader",
    "LocalFileLoader",
    "DirectoryLoader",
    "RemoteURLLoader",
    "DirectTextLoader",
    "DocumentLoaderFactory",
    "query_knowledge_base",
    "add_knowledge_documents",
    "get_knowledge_base_stats",
]