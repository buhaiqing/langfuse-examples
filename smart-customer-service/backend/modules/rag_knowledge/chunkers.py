"""
Text chunking strategies for document segmentation
Supports recursive, title-based, and semantic chunking
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from modules.rag_knowledge.document_loader import Document


class BaseChunker(ABC):
    """Abstract base class for text chunkers"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @abstractmethod
    def chunk(self, document: Document) -> List[Document]:
        """Split document into chunks"""
        pass

    def _create_chunk(
        self,
        content: str,
        metadata: dict[str, Any],
        chunk_index: int,
        total_chunks: int,
    ) -> Document:
        """Helper to create a new chunk document"""
        from uuid import uuid4

        chunk_metadata = metadata.copy()
        chunk_metadata["chunk_index"] = chunk_index
        chunk_metadata["total_chunks"] = total_chunks
        chunk_metadata["chunk_size"] = len(content)

        return Document(
            page_content=content,
            metadata=chunk_metadata,
            doc_id=f"{metadata.get('doc_id', 'unknown')}_chunk_{chunk_index}",
        )


class RecursiveCharacterTextSplitter(BaseChunker):
    """
    Splits text recursively by character count while trying to preserve paragraph boundaries.
    Based on LangChain's RecursiveCharacterTextSplitter.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.separators = separators or [
            "\n\n",
            "\n",
            " ",
            ".",
            ",",
            ";",
            "!",
            "?",
            "]",
            ")",
            "}",
            "\n\n\n",
        ]

    def chunk(self, document: Document) -> List[Document]:
        text = document.page_content
        metadata = document.metadata

        chunks = []
        chunk_index = 0

        while text:
            if len(text) <= self.chunk_size:
                if text.strip():
                    chunk = self._create_chunk(
                        text.strip(),
                        metadata,
                        chunk_index,
                        -1,
                    )
                    chunks.append(chunk)
                break

            split_pos = self._find_split_position(text[: self.chunk_size])

            if split_pos == -1:
                split_pos = self.chunk_size

            chunk_text = text[:split_pos].strip()
            if chunk_text:
                chunk = self._create_chunk(chunk_text, metadata, chunk_index, -1)
                chunks.append(chunk)
                chunk_index += 1

            text = text[split_pos:]
            if chunk_index > 0 and self.chunk_overlap > 0:
                overlap_text = text[: self.chunk_overlap]
                text = overlap_text + "\n\n" + text[self.chunk_overlap :]

        for i, chunk in enumerate(chunks):
            chunk.metadata["total_chunks"] = len(chunks)

        return chunks

    def _find_split_position(self, text: str) -> int:
        for separator in self.separators:
            pos = text.rfind(separator)
            if pos > self.chunk_size * 0.5:
                return pos + len(separator)
        return -1


class TitleBasedTextSplitter(BaseChunker):
    """
    Splits text based on heading structure.
    Works with Markdown and HTML headings (# heading, <h1>, etc.)
    """

    MARKDOWN_HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
    HTML_HEADING_PATTERN = re.compile(r"<h([1-6])[^>]*>(.+?)</h\1>", re.IGNORECASE | re.DOTALL)

    def __init__(
        self,
        chunk_size: int = 2000,
        chunk_overlap: int = 200,
        min_section_length: int = 100,
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.min_section_length = min_section_length

    def chunk(self, document: Document) -> List[Document]:
        text = document.page_content
        metadata = document.metadata

        sections = self._split_by_headings(text)

        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0

        for section in sections:
            section_text = section["content"]
            section_size = len(section_text)

            if section_size > self.chunk_size:
                if current_chunk:
                    chunk = self._create_chunk_from_sections(
                        current_chunk, metadata, chunk_index, []
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_chunk = []
                    current_size = 0

                sub_chunks = self._split_large_section(
                    section_text, metadata, section, chunk_index
                )
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
                continue

            if current_size + section_size > self.chunk_size:
                chunk = self._create_chunk_from_sections(
                    current_chunk, metadata, chunk_index, []
                )
                chunks.append(chunk)
                chunk_index += 1

                if self.chunk_overlap > 0 and current_chunk:
                    overlap_section = current_chunk[-1]
                    current_chunk = [overlap_section]
                    current_size = len(overlap_section["content"])
                else:
                    current_chunk = []
                    current_size = 0

            current_chunk.append(section)
            current_size += section_size

        if current_chunk:
            chunk = self._create_chunk_from_sections(
                current_chunk, metadata, chunk_index, []
            )
            chunks.append(chunk)

        for i, chunk in enumerate(chunks):
            chunk.metadata["total_chunks"] = len(chunks)

        return chunks

    def _split_by_headings(self, text: str) -> List[dict[str, Any]]:
        lines = text.split("\n")
        sections = []
        current_heading = {"level": 0, "text": "Document Start", "content": ""}
        headings = []

        for line in lines:
            md_match = self.MARKDOWN_HEADING_PATTERN.match(line.strip())
            html_match = self.HTML_HEADING_PATTERN.search(line)

            if md_match:
                level = len(md_match.group(1)) - len(md_match.group(1).lstrip("#"))
                heading_text = md_match.group(2).strip()
            elif html_match:
                level = int(html_match.group(1))
                heading_text = html_match.group(2).strip()
            else:
                if current_heading["content"] or sections:
                    current_heading["content"] += "\n" + line
                continue

            if current_heading["content"].strip():
                sections.append(current_heading.copy())

            current_heading = {
                "level": level,
                "text": heading_text,
                "content": "",
            }
            headings.append({"level": level, "text": heading_text})

        if current_heading["content"].strip():
            sections.append(current_heading)

        return sections

    def _split_large_section(
        self, text: str, metadata: dict, section: dict, start_index: int
    ) -> List[Document]:
        chunks = []
        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        temp_doc = Document(
            page_content=text,
            metadata={
                **metadata,
                "section_heading": section["text"],
                "section_level": section["level"],
            },
        )

        sub_chunks = recursive_splitter.chunk(temp_doc)
        for i, sub_chunk in enumerate(sub_chunks):
            sub_chunk.metadata["is_sub_chunk"] = True
            sub_chunk.metadata["parent_section"] = section["text"]

        chunks.extend(sub_chunks)
        return chunks

    def _create_chunk_from_sections(
        self,
        sections: List[dict],
        metadata: dict,
        chunk_index: int,
        excluded_indices: List[int],
    ) -> Document:
        content_parts = []
        heading_path = []

        for i, section in enumerate(sections):
            if i not in excluded_indices:
                prefix = "#" * section["level"] + " " + section["text"]
                content_parts.append(prefix)
                content_parts.append(section["content"])
                heading_path.append(section["text"])

        full_content = "\n\n".join(content_parts)

        chunk_metadata = metadata.copy()
        chunk_metadata["heading_path"] = heading_path
        chunk_metadata["section_count"] = len(sections)

        return self._create_chunk(full_content, chunk_metadata, chunk_index, -1)


class SemanticChunker(BaseChunker):
    """
    Advanced chunker that uses embeddings to find semantically coherent splits.
    More compute-intensive but produces higher quality chunks.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        breakpoint_threshold: float = 0.5,
        embedding_model: Optional[str] = None,
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.breakpoint_threshold = breakpoint_threshold
        self.embedding_model = embedding_model

    def chunk(self, document: Document) -> List[Document]:
        from numpy import array, cosine

        text = document.page_content
        metadata = document.metadata

        sentences = self._split_into_sentences(text)

        if len(sentences) <= 1:
            return [self._create_chunk(text, metadata, 0, 1)]

        embeddings = self._get_embeddings(sentences)

        breakpoints = self._find_breakpoints(embeddings)

        chunks = []
        start_idx = 0

        for i, bp in enumerate(breakpoints):
            chunk_sentences = sentences[start_idx : bp + 1]
            chunk_content = " ".join(chunk_sentences)

            chunk = self._create_chunk(
                chunk_content.strip(),
                metadata,
                i,
                len(breakpoints),
            )
            chunks.append(chunk)
            start_idx = bp + 1

        if start_idx < len(sentences):
            chunk_content = " ".join(sentences[start_idx:])
            chunk = self._create_chunk(
                chunk_content.strip(),
                metadata,
                len(chunks),
                len(chunks),
            )
            chunks.append(chunk)

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        import re
        sentence_endings = re.compile(r"(?<=[.!?])\s+")
        sentences = sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def _get_embeddings(self, sentences: List[str]) -> List[List[float]]:
        try:
            from sentence_transformers import SentenceTransformer

            if not hasattr(self, "_model"):
                model_name = self.embedding_model or "all-MiniLM-L6-v2"
                self._model = SentenceTransformer(model_name)

            embeddings = self._model.encode(sentences)
            return embeddings.tolist()
        except ImportError:
            import random

            dim = 384
            return [[random.random() for _ in range(dim)] for _ in sentences]

    def _find_breakpoints(self, embeddings: List[List[float]]) -> List[int]:
        from numpy import array, cosine

        if len(embeddings) < 2:
            return []

        breakpoints = []
        prev_embedding = array(embeddings[0])

        for i in range(1, len(embeddings)):
            current_embedding = array(embeddings[i])
            similarity = 1 - cosine(prev_embedding, current_embedding)

            if similarity < self.breakpoint_threshold:
                breakpoints.append(i - 1)
                prev_embedding = current_embedding

        return breakpoints


_CHUNKERS = {
    "recursive": RecursiveCharacterTextSplitter,
    "title_based": TitleBasedTextSplitter,
    "title-based": TitleBasedTextSplitter,
    "semantic": SemanticChunker,
}


def get_chunker(
    strategy: str = "recursive",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    **kwargs,
) -> BaseChunker:
    """
    Factory function to get a chunker by name.

    Args:
        strategy: Chunking strategy name
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks
        **kwargs: Additional arguments for specific chunker

    Returns:
        BaseChunker instance
    """
    strategy_lower = strategy.lower().strip()
    chunker_class = _CHUNKERS.get(strategy_lower)

    if not chunker_class:
        available = ", ".join(_CHUNKERS.keys())
        raise ValueError(
            f"Unknown chunking strategy: {strategy}. Available: {available}"
        )

    return chunker_class(chunk_size=chunk_size, chunk_overlap=chunk_overlap, **kwargs)


def list_chunking_strategies() -> List[str]:
    """Return list of available chunking strategies"""
    return list(_CHUNKERS.keys())
