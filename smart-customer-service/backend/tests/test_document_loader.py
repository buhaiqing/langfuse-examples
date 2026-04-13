"""文档加载器模块测试套件。"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modules.rag_knowledge.document_loader import (
    Document,
    DocumentChunker,
    DocumentParser,
    import_documents,
)


class TestDocument:
    """Document数据模型测试。"""

    def test_document_creation_with_auto_id(self):
        """测试文档创建时自动生成doc_id。"""
        doc = Document(page_content="Test content")
        assert doc.page_content == "Test content"
        assert doc.doc_id.startswith("doc_")
        assert len(doc.doc_id) == 20  # "doc_" + 16 char hash

    def test_document_creation_with_custom_id(self):
        """测试文档创建时使用自定义doc_id。"""
        doc = Document(page_content="Test content", doc_id="custom_id")
        assert doc.doc_id == "custom_id"

    def test_document_with_metadata(self):
        """测试文档包含元数据。"""
        metadata = {"source": "test.pdf", "page": 1}
        doc = Document(page_content="Test", metadata=metadata)
        assert doc.metadata == metadata

    def test_document_default_values(self):
        """测试文档默认值。"""
        doc = Document(page_content="Test")
        assert doc.embedding is None
        assert doc.metadata == {}


class TestDocumentParser:
    """DocumentParser解析器测试。"""

    def setup_method(self):
        """每个测试方法前的设置。"""
        self.parser = DocumentParser()

    def test_parse_unsupported_format(self, tmp_path):
        """测试不支持的文件格式。"""
        file_path = tmp_path / "test.xyz"
        file_path.write_text("content")

        with pytest.raises(ValueError, match="不支持的文件格式"):
            self.parser.parse(file_path)

    def test_parse_nonexistent_file(self):
        """测试不存在的文件。"""
        with pytest.raises(FileNotFoundError):
            self.parser.parse(Path("/nonexistent/file.pdf"))

    def test_parse_markdown(self, tmp_path):
        """测试Markdown文件解析。"""
        file_path = tmp_path / "test.md"
        content = "# Title\n\nThis is a test paragraph.\n\n## Section 2\n\nMore content."
        file_path.write_text(content)

        result = self.parser.parse(file_path)
        assert result == content

    def test_parse_html(self, tmp_path):
        """测试HTML文件解析。"""
        file_path = tmp_path / "test.html"
        content = "<html><body><h1>Title</h1><p>Paragraph</p></body></html>"
        file_path.write_text(content)

        result = self.parser.parse(file_path)
        assert "Title" in result
        assert "Paragraph" in result

    @patch("modules.rag_knowledge.document_loader.fitz")
    def test_parse_pdf_with_pymupdf(self, mock_fitz, tmp_path):
        """测试PDF解析（使用PyMuPDF）。"""
        file_path = tmp_path / "test.pdf"
        file_path.write_text("fake pdf")

        # Mock PyMuPDF
        mock_page = MagicMock()
        mock_page.get_text.return_value = "PDF content page 1"
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz.open.return_value = mock_doc

        result = self.parser.parse(file_path)
        assert "PDF content page 1" in result

    @patch("modules.rag_knowledge.document_loader.Document")
    def test_parse_docx(self, mock_docx_class, tmp_path):
        """测试Word文档解析。"""
        file_path = tmp_path / "test.docx"
        file_path.write_text("fake docx")

        # Mock python-docx
        mock_para1 = MagicMock()
        mock_para1.text = "Paragraph 1"
        mock_para2 = MagicMock()
        mock_para2.text = "Paragraph 2"
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_docx_class.return_value = mock_doc

        result = self.parser.parse(file_path)
        assert "Paragraph 1" in result
        assert "Paragraph 2" in result


class TestDocumentChunker:
    """DocumentChunker分块器测试。"""

    def test_recursive_chunking(self):
        """测试递归字符分块。"""
        chunker = DocumentChunker(strategy="recursive", chunk_size=50, chunk_overlap=10)
        text = "This is a test. " * 20  # 重复文本

        chunks = chunker.chunk(text)
        assert len(chunks) > 1
        assert all(isinstance(chunk, Document) for chunk in chunks)

    def test_paragraph_chunking(self):
        """测试段落分块。"""
        chunker = DocumentChunker(strategy="paragraph", chunk_size=100, chunk_overlap=0)
        text = "Para 1\n\nPara 2\n\nPara 3"

        chunks = chunker.chunk(text)
        assert len(chunks) >= 1

    def test_title_chunking(self):
        """测试标题分块。"""
        chunker = DocumentChunker(strategy="title", chunk_size=200, chunk_overlap=0)
        text = "# Title 1\n\nContent 1\n\n## Subtitle\n\nContent 2\n\n# Title 2\n\nContent 3"

        chunks = chunker.chunk(text)
        assert len(chunks) >= 1
        # 验证标题被保留
        assert any("# Title 1" in chunk.page_content for chunk in chunks)

    def test_chunking_with_metadata(self):
        """测试分块时添加元数据。"""
        chunker = DocumentChunker(strategy="recursive", chunk_size=50)
        text = "Test content " * 10
        metadata = {"source": "test.md", "author": "Test Author"}

        chunks = chunker.chunk(text, metadata=metadata)
        assert all(chunk.metadata["source"] == "test.md" for chunk in chunks)
        assert all("chunk_index" in chunk.metadata for chunk in chunks)

    def test_invalid_strategy(self):
        """测试无效的分块策略。"""
        chunker = DocumentChunker(strategy="invalid")

        with pytest.raises(ValueError, match="不支持的分块策略"):
            chunker.chunk("test content")

    def test_empty_text_chunking(self):
        """测试空文本分块。"""
        chunker = DocumentChunker(strategy="recursive")
        chunks = chunker.chunk("")
        assert len(chunks) == 0

    def test_chunk_metadata_includes_strategy(self):
        """测试分块元数据包含策略信息。"""
        chunker = DocumentChunker(strategy="recursive")
        chunks = chunker.chunk("Test content")

        if chunks:
            assert chunks[0].metadata["chunk_strategy"] == "recursive"


class TestImportDocuments:
    """import_documents函数测试。"""

    def test_import_single_markdown_file(self, tmp_path):
        """测试导入单个Markdown文件。"""
        file_path = tmp_path / "test.md"
        file_path.write_text("# Test\n\nContent here.")

        documents = import_documents([file_path], chunk_strategy="recursive", chunk_size=100)

        assert len(documents) >= 1
        assert documents[0].metadata["source"] == str(file_path)
        assert documents[0].metadata["filename"] == "test.md"

    def test_import_multiple_files(self, tmp_path):
        """测试导入多个文件。"""
        file1 = tmp_path / "test1.md"
        file1.write_text("# File 1\n\nContent 1.")

        file2 = tmp_path / "test2.md"
        file2.write_text("# File 2\n\nContent 2.")

        documents = import_documents([file1, file2])

        assert len(documents) >= 2

    def test_import_with_custom_metadata(self, tmp_path):
        """测试导入时添加自定义元数据。"""
        file_path = tmp_path / "test.md"
        file_path.write_text("Test content.")

        custom_metadata = {"category": "FAQ", "version": "1.0"}
        documents = import_documents(
            [file_path],
            chunk_strategy="recursive",
            metadata=custom_metadata,
        )

        assert documents[0].metadata["category"] == "FAQ"
        assert documents[0].metadata["version"] == "1.0"
