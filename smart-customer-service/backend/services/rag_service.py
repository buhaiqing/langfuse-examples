"""RAG 知识库服务"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.config import settings
from storage.chroma_client import chroma_client
from core.langfuse_client import create_span, score_trace
from services.rag_query_rewriter import query_rewriter
from services.rag_document_importer import document_import_engine, ImportResult


@dataclass
class RAGQueryResult:
    """RAG 查询结果"""

    answer: str
    documents: List[Dict[str, Any]]
    confidence: float
    sources: List[str]


class RAGService:
    """RAG 知识库服务"""

    def __init__(self):
        self.llm = ChatOpenAI(model=settings.openai_model, temperature=0.1)
        self.embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model)

        # RAG 提示词模板
        self.rag_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是一个智能客服助手，基于以下知识库内容回答用户问题。

要求：
1. 只根据提供的上下文回答问题
2. 如果上下文中没有答案，明确告知用户
3. 回答要简洁、准确、专业
4. 引用来源时要说明文档名称

上下文信息：
{context}

用户问题：{question}""",
                ),
            ]
        )

        self.chain = self.rag_prompt | self.llm | StrOutputParser()

    async def query(
        self,
        query: str,
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> RAGQueryResult:
        """RAG 查询主方法"""

        with create_span("rag_query") as span:
            # 1. 查询重写
            with create_span("query_rewrite"):
                rewritten_query = await query_rewriter.rewrite(query)

            # 2. 向量检索
            with create_span("vector_search"):
                documents = await self._retrieve_documents(
                    rewritten_query["rewritten"], top_k, filters
                )

            # 3. 构建上下文
            context = self._build_context(documents)

            # 4. 生成答案
            with create_span("answer_generation"):
                answer = await self._generate_answer(query, context)

            # 5. 提取来源
            sources = [doc.metadata.get("source", "未知") for doc in documents]

            # 6. 记录 Span
            span.end(
                output_data={
                    "query": query,
                    "rewritten_query": rewritten_query["rewritten"],
                    "doc_count": len(documents),
                    "answer_length": len(answer),
                }
            )

            # 7. 评分
            score_trace("retrieval_relevance", 0.8)  # TODO: 动态计算
            score_trace("rag_query_latency_ms", 100)  # TODO: 实际延迟

            return RAGQueryResult(
                answer=answer,
                documents=[
                    {"content": doc.page_content, "metadata": doc.metadata} for doc in documents
                ],
                confidence=0.8,
                sources=sources,
            )

    async def _retrieve_documents(
        self,
        query: str,
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None,
    ):
        """检索相关文档"""
        # TODO: 实现混合检索 (向量 + BM25)
        # 目前使用简单的向量检索
        results = await chroma_client.similarity_search(
            query=query,
            k=top_k,
            filter_metadata=filters,
        )
        return results

    def _build_context(self, documents: List) -> str:
        """构建上下文"""
        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"[文档{i}]: {doc.page_content}")

        return "\n\n".join(context_parts)

    async def _generate_answer(self, question: str, context: str) -> str:
        """生成答案"""
        return await self.chain.ainvoke(
            {
                "question": question,
                "context": context,
            }
        )

    async def import_documents(self, file_paths: List[str], metadata: Optional[Dict] = None):
        """添加文档到知识库"""
        with create_span("document_import"):
            result = await document_import_engine.import_files(file_paths, metadata)

            # 添加到 ChromaDB
            if result.documents:
                await chroma_client.add_documents(result.documents)

            return result

    def delete_documents(self, doc_ids: List[str]):
        """删除文档"""
        chroma_client.delete_documents(doc_ids)


# 全局服务实例
rag_service = RAGService()
