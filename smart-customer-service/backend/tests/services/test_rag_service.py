"""RAG 服务测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.services.rag_service import RAGService, RAGQueryResult
from backend.services.rag_query_rewriter import QueryRewriter
from backend.services.rag_document_importer import DocumentImportEngine, ImportResult


class TestRAGService:
    """RAG 服务测试"""

    @pytest.fixture
    def rag_service(self):
        """创建 RAG 服务实例"""
        return RAGService()

    def test_init(self, rag_service):
        """测试初始化"""
        assert rag_service.llm is not None
        assert rag_service.embeddings is not None
        assert rag_service.rag_prompt is not None
        assert rag_service.chain is not None

    def test_build_context(self, rag_service):
        """测试上下文构建"""
        mock_docs = [
            MagicMock(page_content="内容 1", metadata={"source": "doc1.pdf"}),
            MagicMock(page_content="内容 2", metadata={"source": "doc2.md"}),
        ]

        context = rag_service._build_context(mock_docs)

        assert "[文档 1]: 内容 1" in context
        assert "[文档 2]: 内容 2" in context

    def test_build_context_empty(self, rag_service):
        """测试空文档列表"""
        context = rag_service._build_context([])
        assert context == ""

    @pytest.mark.asyncio
    async def test_query_basic(self, rag_service):
        """测试基本查询"""
        with patch.object(
            rag_service, "_retrieve_documents", new_callable=AsyncMock
        ) as mock_retrieve:
            with patch.object(
                rag_service, "_generate_answer", new_callable=AsyncMock
            ) as mock_generate:
                mock_retrieve.return_value = [
                    MagicMock(page_content="测试内容", metadata={"source": "test.pdf"})
                ]
                mock_generate.return_value = "这是答案"

                result = await rag_service.query("测试问题", top_k=3)

                assert isinstance(result, RAGQueryResult)
                assert result.answer == "这是答案"
                assert len(result.documents) == 1
                assert result.sources == ["test.pdf"]

    @pytest.mark.asyncio
    async def test_query_with_filters(self, rag_service):
        """测试带过滤条件的查询"""
        filters = {"product_version": "v2.3", "category": "api"}

        with patch.object(
            rag_service, "_retrieve_documents", new_callable=AsyncMock
        ) as mock_retrieve:
            with patch.object(
                rag_service, "_generate_answer", new_callable=AsyncMock
            ) as mock_generate:
                mock_retrieve.return_value = []
                mock_generate.return_value = "基于检索结果..."

                result = await rag_service.query("问题", filters=filters)

                mock_retrieve.assert_called_once()
                assert result.answer is not None

    @pytest.mark.asyncio
    async def test_retrieve_documents(self, rag_service):
        """测试文档检索"""
        with patch("backend.services.rag_service.chroma_client") as mock_chroma:
            mock_chroma.similarity_search = AsyncMock(
                return_value=[MagicMock(page_content="内容", metadata={})]
            )

            docs = await rag_service._retrieve_documents("查询", top_k=5)

            assert len(docs) == 1
            mock_chroma.similarity_search.assert_called_once()


class TestQueryRewriter:
    """查询重写器测试"""

    @pytest.fixture
    def rewriter(self):
        """创建查询重写器实例"""
        return QueryRewriter()

    def test_init(self, rewriter):
        """测试初始化"""
        assert rewriter.llm is not None
        assert rewriter.synonym_prompt is not None

    @pytest.mark.asyncio
    async def test_rewrite_basic(self, rewriter):
        """测试基本重写"""
        with patch.object(rewriter.llm, "ainvoke", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = MagicMock(
                content='{"original": "API 错误", "expanded": ["API 报错", "接口错误"]}'
            )

            result = await rewriter.rewrite("API 错误")

            assert "original" in result
            assert "expanded" in result
            assert "rewritten" in result

    @pytest.mark.asyncio
    async def test_rewrite_empty_query(self, rewriter):
        """测试空查询重写"""
        result = await rewriter.rewrite("")
        assert result["original"] == ""

    def test_extract_keywords(self, rewriter):
        """测试关键词提取"""
        keywords = rewriter._extract_keywords("API 403 错误怎么办")
        assert len(keywords) > 0
        assert "API" in keywords or "403" in keywords


class TestDocumentImportEngine:
    """文档导入引擎测试"""

    @pytest.fixture
    def importer(self):
        """创建文档导入引擎实例"""
        return DocumentImportEngine()

    def test_init(self, importer):
        """测试初始化"""
        assert importer.text_splitter is not None
        assert importer.md_splitter is not None
        assert len(importer.loader_map) >= 4

    def test_compute_hash(self, importer):
        """测试哈希计算"""
        hash1 = importer._compute_hash("测试内容")
        hash2 = importer._compute_hash("测试内容")
        hash3 = importer._compute_hash("不同内容")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 32  # MD5 哈希长度

    def test_split_document(self, importer):
        """测试文档分块"""
        from langchain_core.documents import Document

        doc = Document(page_content="测试" * 100, metadata={"source": "test.pdf"})
        chunks = importer._split_document(doc)

        assert len(chunks) > 0
        for chunk in chunks:
            assert "chunk_index" in chunk.metadata
            assert "doc_hash" in chunk.metadata

    @pytest.mark.asyncio
    async def test_import_files_basic(self, importer):
        """测试基本文件导入"""
        # Mock _load_file 方法
        with patch.object(importer, "_load_file", new_callable=AsyncMock) as mock_load:
            from langchain_core.documents import Document

            mock_load.return_value = [Document(page_content="测试内容")]

            result = await importer.import_files(["test.txt"])

            assert isinstance(result, ImportResult)
            assert result.total_chunks >= 0

    @pytest.mark.asyncio
    async def test_import_files_with_metadata(self, importer):
        """测试带元数据的文件导入"""
        with patch.object(importer, "_load_file", new_callable=AsyncMock) as mock_load:
            from langchain_core.documents import Document

            mock_load.return_value = [Document(page_content="内容")]

            metadata = {"category": "api_docs", "version": "v2.3"}
            result = await importer.import_files(["test.txt"], metadata=metadata)

            assert result.metadata["total_files"] == 1

    @pytest.mark.asyncio
    async def test_import_files_failure(self, importer):
        """测试文件导入失败"""
        with patch.object(importer, "_load_file", new_callable=AsyncMock) as mock_load:
            mock_load.side_effect = Exception("文件不存在")

            result = await importer.import_files(["nonexistent.txt"])

            assert len(result.failed_files) > 0
            assert result.total_chunks == 0

    @pytest.mark.asyncio
    async def test_load_file_unsupported_format(self, importer):
        """测试不支持的文件格式"""
        with pytest.raises(ValueError) as exc_info:
            await importer._load_file("test.xyz")

        assert "不支持的文件类型" in str(exc_info.value)
