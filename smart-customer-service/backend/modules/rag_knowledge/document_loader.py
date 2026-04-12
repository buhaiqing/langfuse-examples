"""
Document loader for multiple file formats
Supports PDF, DOCX, Markdown, and HTML
"""

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, List, Optional

from core.logging_config import LogCategory, get_logger
from core.tracing import create_span

logger = get_logger(LogCategory.RAG)


@dataclass
class Document:
    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    doc_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class DocumentParser:
    """Unified interface for parsing multiple document formats"""

    def __init__(self):
        self._parsers = {
            ".pdf": self._parse_pdf,
            ".docx": self._parse_docx,
            ".md": self._parse_markdown,
            ".markdown": self._parse_markdown,
            ".html": self._parse_html,
            ".htm": self._parse_html,
        }

    def parse(self, file_path: Path) -> Document:
        suffix = file_path.suffix.lower()
        parser = self._parsers.get(suffix)

        if not parser:
            raise ValueError(f"Unsupported file format: {suffix}")

        logger.debug(f"Parsing document: {file_path}")
        return parser(file_path)

    def parse_batch(self, file_paths: List[Path]) -> List[Document]:
        documents = []
        for file_path in file_paths:
            try:
                doc = self.parse(file_path)
                documents.append(doc)
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")
                continue
        return documents

    def _parse_pdf(self, file_path: Path) -> Document:
        import fitz

        text_parts = []
        metadata = {
            "source": str(file_path),
            "filename": file_path.name,
            "format": "pdf",
        }

        with fitz.open(file_path) as doc:
            metadata["page_count"] = len(doc)
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    text_parts.append({
                        "page_num": page_num + 1,
                        "text": text,
                        "page_width": page.rect.width,
                        "page_height": page.rect.height,
                    })

        full_text = "\n\n".join(part["text"] for part in text_parts)
        metadata["pages"] = text_parts

        return Document(
            page_content=full_text,
            metadata=metadata,
            doc_id=f"doc_{uuid.uuid4().hex[:8]}",
        )

    def _parse_docx(self, file_path: Path) -> Document:
        from docx import Document as DocxDocument

        doc = DocxDocument(file_path)
        paragraphs = []
        tables = []

        for element in doc.element.body:
            if element.tag.endswith("p"):
                para = doc.paragraphs[len(paragraphs)]
                if para.text.strip():
                    paragraphs.append(para.text)
            elif element.tag.endswith("tbl"):
                table_data = []
                table = doc.tables[len(tables)]
                for row in table.rows:
                    row_data = [cell.text for cell in row.cells]
                    table_data.append(row_data)
                tables.append(table_data)

        full_text = "\n\n".join(paragraphs)
        metadata = {
            "source": str(file_path),
            "filename": file_path.name,
            "format": "docx",
            "paragraph_count": len(paragraphs),
            "table_count": len(tables),
            "tables": tables,
            "headings": [p for p in paragraphs if self._is_heading(p)],
        }

        return Document(
            page_content=full_text,
            metadata=metadata,
            doc_id=f"doc_{uuid.uuid4().hex[:8]}",
        )

    def _parse_markdown(self, file_path: Path) -> Document:
        import re

        content = file_path.read_text(encoding="utf-8")

        headings = []
        sections = re.split(r"(?=^#{1,6}\s)", content, flags=re.MULTILINE)

        for section in sections:
            match = re.match(r"^(#{1,6})\s+(.+)$", section.strip(), re.MULTILINE)
            if match:
                headings.append({
                    "level": len(match.group(1)),
                    "text": match.group(2).strip(),
                })

        metadata = {
            "source": str(file_path),
            "filename": file_path.name,
            "format": "markdown",
            "headings": headings,
            "section_count": len(sections),
        }

        return Document(
            page_content=content,
            metadata=metadata,
            doc_id=f"doc_{uuid.uuid4().hex[:8]}",
        )

    def _parse_html(self, file_path: Path) -> Document:
        from bs4 import BeautifulSoup
        import re

        html_content = file_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html_content, "html.parser")

        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text(separator="\n", strip=True)

        headings = []
        for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            for heading in soup.find_all(tag):
                if heading.text.strip():
                    headings.append({
                        "level": int(tag[1]),
                        "text": heading.text.strip(),
                    })

        links = []
        for link in soup.find_all("a"):
            href = link.get("href", "")
            text_content = link.text.strip()
            if href and text_content:
                links.append({"text": text_content, "url": href})

        metadata = {
            "source": str(file_path),
            "filename": file_path.name,
            "format": "html",
            "headings": headings,
            "links": links,
        }

        return Document(
            page_content=text,
            metadata=metadata,
            doc_id=f"doc_{uuid.uuid4().hex[:8]}",
        )

    def _is_heading(self, text: str) -> bool:
        import re
        return bool(re.match(r"^#{1,6}\s", text)) or (
            text.isupper() and len(text) < 100
        )


def import_documents(
    file_paths: List[Path],
    chunk_strategy: str = "recursive",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    metadata: Optional[dict[str, Any]] = None,
) -> List[Document]:
    """
    Import documents from file paths with document parsing and optional chunking.

    Args:
        file_paths: List of file paths to import
        chunk_strategy: Chunking strategy (recursive, title_based, or None for no chunking)
        chunk_size: Target size for each chunk
        chunk_overlap: Overlap between chunks
        metadata: Additional metadata to attach to documents

    Returns:
        List of Document objects
    """
    with create_span("document_import", input_data={
        "file_count": len(file_paths),
        "chunk_strategy": chunk_strategy,
        "chunk_size": chunk_size,
    }) as span:
        parser = DocumentParser()
        documents = parser.parse_batch(file_paths)

        for doc in documents:
            if metadata:
                doc.metadata.update(metadata)

        span.add_event("documents_parsed", output_data={"count": len(documents)})

        if chunk_strategy and chunk_strategy != "none":
            from modules.rag_knowledge.chunkers import get_chunker
            chunker = get_chunker(chunk_strategy, chunk_size, chunk_overlap)

            all_chunks = []
            for doc in documents:
                chunks = chunker.chunk(doc)
                all_chunks.extend(chunks)

            span.add_event("documents_chunked", output_data={"chunk_count": len(all_chunks)})
            documents = all_chunks
        else:
            span.add_event("documents_chunked", output_data={"chunk_count": len(documents)})

        return documents
