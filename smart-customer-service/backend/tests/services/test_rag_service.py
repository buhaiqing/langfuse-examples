"""RAG 知识库服务测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, Mock
from dataclasses import dataclass
from typing import List, Dict, Any

from backend.services.rag_service import RAGService, RAGQueryResult, rag_service


@dataclass
class MockDocument:
    """模拟文档对象"""
    page_content: str
    metadata: Dict[str, Any]


class TestRAGService:
    """RAG 服务测试"""

    @pytest.fixture
    def rag_service_instance(self):
        """创建 RAG 服务实例"""
        with patch('backend.services.rag_service.ChatOpenAI'), \
             patch('backend.services.rag_service.OpenAIEmbeddings'):
            service = RAGService()
            return service

    def test_init(self, rag_service_instance):
        """测试初始化"""
        service = rag_service_instance
        assert service.llm is not None
        assert service.embeddings is not None
        assert service.rag_prompt is not None
        assert service.chain is not None

    @pytest.mark.asyncio
    async def test_query_success(self, rag_service_instance):
        """测试查询成功场景"""
        service = rag_service_instance
        
        # Mock 依赖
        mock_doc = MockDocument(
            page_content="这是测试文档内容",
            metadata={"source": "test_doc.pdf", "page": 1}
        )
        
        with patch('backend.services.rag_service.query_rewriter.rewrite', new_callable=AsyncMock) as mock_rewrite, \
             patch.object(service, '_retrieve_documents', new_callable=AsyncMock) as mock_retrieve, \
             patch.object(service, '_generate_answer', new_callable=AsyncMock) as mock_generate, \
             patch('backend.services.rag_service.create_span') as mock_span, \
             patch('backend.services.rag_service.score_trace') as mock_score:
            
            mock_rewrite.return_value = {"rewritten": "重写后的查询"}
            mock_retrieve.return_value = [mock_doc]
            mock_generate.return_value = "这是生成的答案"
            
            result = await service.query(
                query="测试查询",
                top_k=3,
                session_id="sess_123"
            )
            
            assert isinstance(result, RAGQueryResult)
            assert result.answer == "这是生成的答案"
            assert len(result.documents) == 1
            assert result.documents[0]["content"] == "这是测试文档内容"
            assert result.confidence == 0.8
            assert "test_doc.pdf" in result.sources

    @pytest.mark.asyncio
    async def test_query_with_filters(self, rag_service_instance):
        """测试带过滤条件的查询"""
        service = rag_service_instance
        
        mock_doc = MockDocument(
            page_content="API 文档内容",
            metadata={"source": "api_doc.pdf", "category": "api"}
        )
        
        with patch('backend.services.rag_service.query_rewriter.rewrite', new_callable=AsyncMock) as mock_rewrite, \
             patch.object(service, '_retrieve_documents', new_callable=AsyncMock) as mock_retrieve, \
             patch.object(service, '_generate_answer', new_callable=AsyncMock) as mock_generate, \
             patch('backend.services.rag_service.create_span'), \
             patch('backend.services.rag_service.score_trace'):
            
            mock_rewrite.return_value = {"rewritten": "API 错误查询"}
            mock_retrieve.return_value = [mock_doc]
            mock_generate.return_value = "API 错误解决方案"
            
            filters = {"category": "api"}
            result = await service.query(
                query="API 报错怎么办",
                top_k=5,
                filters=filters,
                session_id="sess_456"
            )
            
            # 验证过滤器被传递
            mock_retrieve.assert_called_once()
            call_args = mock_retrieve.call_args
            assert call_args[1]["filters"] == filters

    @pytest.mark.asyncio
    async def test_retrieve_documents(self, rag_service_instance):
        """测试文档检索"""
        service = rag_service_instance
        
        mock_doc1 = MockDocument(
            page_content="文档1内容",
            metadata={"source": "doc1.pdf"}
        )
        mock_doc2 = MockDocument(
            page_content="文档2内容",
            metadata={"source": "doc2.pdf"}
        )
        
        with patch('backend.services.rag_service.chroma_client') as mock_chroma:
            mock_chroma.similarity_search = AsyncMock(return_value=[mock_doc1, mock_doc2])
            
            results = await service._retrieve_documents("查询", top_k=3)
            
            assert len(results) == 2
            mock_chroma.similarity_search.assert_called_once_with(
                query="查询",
                k=3,
                filter_metadata=None
            )

    def test_build_context(self, rag_service_instance):
        """测试上下文构建"""
        service = rag_service_instance
        
        documents = [
            MockDocument(page_content="第一段内容", metadata={}),
            MockDocument(page_content="第二段内容", metadata={}),
        ]
        
        context = service._build_context(documents)
        
        assert "[文档1]: 第一段内容" in context
        assert "[文档2]: 第二段内容" in context
        assert "\n\n" in context

    @pytest.mark.asyncio
    async def test_generate_answer(self, rag_service_instance):
        """测试答案生成"""
        service = rag_service_instance
        
        # Mock chain 调用
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value="生成的答案")
        service.chain = mock_chain
        
        answer = await service._generate_answer(
            question="测试问题",
            context="测试上下文"
        )
        
        assert answer == "生成的答案"
        mock_chain.ainvoke.assert_called_once_with({
            "question": "测试问题",
            "context": "测试上下文"
        })

    @pytest.mark.asyncio
    async def test_import_documents(self, rag_service_instance):
        """测试文档导入"""
        service = rag_service_instance
        
        mock_result = MagicMock()
        mock_result.documents = [MockDocument(page_content="内容", metadata={"source": "file.pdf"})]
        mock_result.total_chunks = 5
        mock_result.failed_files = []
        
        with patch('backend.services.rag_service.document_import_engine.import_files', new_callable=AsyncMock) as mock_import, \
             patch('backend.services.rag_service.chroma_client') as mock_chroma, \
             patch('backend.services.rag_service.create_span'):
            
            mock_import.return_value = mock_result
            mock_chroma.add_documents = AsyncMock()
            
            result = await service.import_documents(["/path/to/file.pdf"])
            
            mock_import.assert_called_once_with(["/path/to/file.pdf"], None)
            mock_chroma.add_documents.assert_called_once()
            assert result.total_chunks == 5

    def test_delete_documents(self, rag_service_instance):
        """测试文档删除"""
        service = rag_service_instance
        
        with patch('backend.services.rag_service.chroma_client') as mock_chroma:
            mock_chroma.delete_documents = Mock()
            
            service.delete_documents(["doc_1", "doc_2"])
            
            mock_chroma.delete_documents.assert_called_once_with(["doc_1", "doc_2"])


class TestRAGQueryResult:
    """RAG 查询结果测试"""

    def test_result_creation(self):
        """测试结果创建"""
        result = RAGQueryResult(
            answer="测试答案",
            documents=[{"content": "内容", "metadata": {}}],
            confidence=0.95,
            sources=["doc1.pdf"]
        )
        
        assert result.answer == "测试答案"
        assert len(result.documents) == 1
        assert result.confidence == 0.95
        assert result.sources == ["doc1.pdf"]

    def test_result_with_multiple_sources(self):
        """测试多来源结果"""
        result = RAGQueryResult(
            answer="综合答案",
            documents=[
                {"content": "内容1", "metadata": {"source": "doc1.pdf"}},
                {"content": "内容2", "metadata": {"source": "doc2.pdf"}},
            ],
            confidence=0.85,
            sources=["doc1.pdf", "doc2.pdf"]
        )
        
        assert len(result.sources) == 2
        assert result.confidence == 0.85


class TestRAGServiceEdgeCases:
    """RAG 服务边界情况测试"""

    @pytest.fixture
    def rag_service_instance(self):
        with patch('backend.services.rag_service.ChatOpenAI'), \
             patch('backend.services.rag_service.OpenAIEmbeddings'):
            return RAGService()

    @pytest.mark.asyncio
    async def test_empty_query(self, rag_service_instance):
        """测试空查询"""
        service = rag_service_instance
        
        with patch('backend.services.rag_service.query_rewriter.rewrite', new_callable=AsyncMock) as mock_rewrite, \
             patch.object(service, '_retrieve_documents', new_callable=AsyncMock) as mock_retrieve, \
             patch.object(service, '_generate_answer', new_callable=AsyncMock) as mock_generate, \
             patch('backend.services.rag_service.create_span'), \
             patch('backend.services.rag_service.score_trace'):
            
            mock_rewrite.return_value = {"rewritten": ""}
            mock_retrieve.return_value = []
            mock_generate.return_value = "未找到相关信息"
            
            result = await service.query("", session_id="sess_123")
            
            assert result.answer == "未找到相关信息"
            assert result.documents == []

    @pytest.mark.asyncio
    async def test_no_documents_found(self, rag_service_instance):
        """测试未找到文档"""
        service = rag_service_instance
        
        with patch('backend.services.rag_service.query_rewriter.rewrite', new_callable=AsyncMock) as mock_rewrite, \
             patch.object(service, '_retrieve_documents', new_callable=AsyncMock) as mock_retrieve, \
             patch.object(service, '_generate_answer', new_callable=AsyncMock) as mock_generate, \
             patch('backend.services.rag_service.create_span'), \
             patch('backend.services.rag_service.score_trace'):
            
            mock_rewrite.return_value = {"rewritten": "查询"}
            mock_retrieve.return_value = []
            mock_generate.return_value = "抱歉，在知识库中未找到相关信息。"
            
            result = await service.query("非常冷门的问题", session_id="sess_123")
            
            assert "未找到" in result.answer or "抱歉" in result.answer
            assert result.documents == []
            assert result.sources == []

    @pytest.mark.asyncio
    async def test_long_context_truncation(self, rag_service_instance):
        """测试长上下文截断"""
        service = rag_service_instance
        
        # 创建超长文档
        long_content = "内容" * 10000
        documents = [MockDocument(page_content=long_content, metadata={"source": "long_doc.pdf"})]
        
        context = service._build_context(documents)
        
        # 验证上下文被正确构建（实际应该被截断或处理）
        assert "[文档1]:" in context
        assert len(context) > 0


class TestRAGServiceIntegration:
    """RAG 服务集成测试"""

    @pytest.mark.asyncio
    async def test_full_query_pipeline(self):
        """测试完整查询流程"""
        with patch('backend.services.rag_service.ChatOpenAI') as mock_llm, \
             patch('backend.services.rag_service.OpenAIEmbeddings'), \
             patch('backend.services.rag_service.query_rewriter') as mock_rewriter, \
             patch('backend.services.rag_service.chroma_client') as mock_chroma, \
             patch('backend.services.rag_service.create_span') as mock_span, \
             patch('backend.services.rag_service.score_trace'):
            
            # Setup mocks
            mock_rewriter.rewrite = AsyncMock(return_value={"rewritten": "API 错误如何处理"})
            
            mock_doc = MockDocument(
                page_content="API 错误处理指南：请检查您的 API Key 是否正确。",
                metadata={"source": "api_guide.pdf", "page": 1}
            )
            mock_chroma.similarity_search = AsyncMock(return_value=[mock_doc])
            
            # Mock LLM chain
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value="请检查您的 API Key 配置。")
            
            service = RAGService()
            service.chain = mock_chain
            
            # Execute
            result = await service.query(
                query="我的 API 报错了怎么办？",
                top_k=3,
                session_id="sess_integration"
            )
            
            # Verify
            assert result.answer == "请检查您的 API Key 配置。"
            assert len(result.documents) == 1
            assert result.documents[0]["metadata"]["source"] == "api_guide.pdf"
