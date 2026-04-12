"""
Knowledge base manager with metadata storage, version control, and incremental updates
Manages document lifecycle with SQLite backend and scheduled updates
"""

import hashlib
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.logging_config import LogCategory, get_logger
from core.tracing import create_span, score_trace

logger = get_logger(LogCategory.RAG)


@dataclass
class DocumentVersion:
    """Represents a version of a document"""

    doc_id: str
    version_number: int
    file_hash: str
    file_path: str
    created_at: datetime = field(default_factory=datetime.now)
    file_size: int = 0
    chunk_count: int = 0


@dataclass
class KBStatistics:
    """Knowledge base statistics"""

    total_documents: int
    total_chunks: int
    total_tokens: int
    last_update_time: Optional[datetime]
    unique_sources: int
    average_chunk_size: float
    storage_size_mb: float


class MetadataStore:
    """
    SQLite-based metadata storage for knowledge base documents.
    Tracks document versions, file hashes, and update history.
    """

    def __init__(self, db_path: str = ".lancedb/knowledge_base.db"):
        """
        Initialize metadata store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._initialize_schema()

        logger.info(f"MetadataStore initialized: {db_path}")

    def _initialize_schema(self):
        """Create database tables if they don't exist"""
        cursor = self._conn.cursor()

        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                source_path TEXT NOT NULL,
                current_version INTEGER DEFAULT 1,
                file_hash TEXT NOT NULL,
                category TEXT,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                chunk_count INTEGER DEFAULT 0,
                token_count INTEGER DEFAULT 0
            )
        """)

        # Document versions table (history)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
            )
        """)

        # Update history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS update_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                documents_added INTEGER DEFAULT 0,
                documents_updated INTEGER DEFAULT 0,
                documents_deleted INTEGER DEFAULT 0,
                duration_seconds REAL,
                status TEXT,
                error_message TEXT
            )
        """)

        # Create indexes for performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_doc_source ON documents(source_path)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_doc_hash ON documents(file_hash)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_version_doc ON document_versions(doc_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_update_time ON update_history(update_time)"
        )

        self._conn.commit()
        logger.debug("Database schema initialized")

    def add_document(
        self,
        doc_id: str,
        source_path: str,
        file_hash: str,
        category: Optional[str] = None,
        title: Optional[str] = None,
        chunk_count: int = 0,
        token_count: int = 0,
    ) -> None:
        """
        Add a new document to the metadata store.

        Args:
            doc_id: Unique document identifier
            source_path: Path to the source file
            file_hash: MD5 hash of file content
            category: Document category
            title: Document title
            chunk_count: Number of chunks
            token_count: Estimated token count
        """
        cursor = self._conn.cursor()

        try:
            # Insert document
            cursor.execute(
                """
                INSERT INTO documents 
                (doc_id, source_path, file_hash, category, title, chunk_count, token_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, source_path, file_hash, category, title, chunk_count, token_count),
            )

            # Create initial version
            file_size = os.path.getsize(source_path) if os.path.exists(source_path) else 0
            cursor.execute(
                """
                INSERT INTO document_versions 
                (doc_id, version_number, file_hash, file_path, file_size, chunk_count)
                VALUES (?, 1, ?, ?, ?, ?)
                """,
                (doc_id, file_hash, source_path, file_size, chunk_count),
            )

            self._conn.commit()
            logger.debug(f"Added document metadata: {doc_id}")

        except sqlite3.IntegrityError as e:
            self._conn.rollback()
            raise ValueError(f"Document {doc_id} already exists: {e}")

    def update_document(
        self,
        doc_id: str,
        new_file_hash: str,
        new_source_path: Optional[str] = None,
        chunk_count: Optional[int] = None,
        token_count: Optional[int] = None,
    ) -> int:
        """
        Update document metadata and create new version.

        Args:
            doc_id: Document identifier
            new_file_hash: New file hash
            new_source_path: Updated file path (optional)
            chunk_count: New chunk count (optional)
            token_count: New token count (optional)

        Returns:
            New version number
        """
        cursor = self._conn.cursor()

        try:
            # Get current version
            cursor.execute(
                "SELECT current_version, source_path FROM documents WHERE doc_id = ?",
                (doc_id,),
            )
            row = cursor.fetchone()

            if not row:
                raise ValueError(f"Document {doc_id} not found")

            current_version = row["current_version"]
            source_path = new_source_path or row["source_path"]
            new_version = current_version + 1

            # Update documents table
            update_fields = ["file_hash = ?", "updated_at = CURRENT_TIMESTAMP"]
            update_values = [new_file_hash]

            if new_source_path:
                update_fields.append("source_path = ?")
                update_values.append(new_source_path)

            if chunk_count is not None:
                update_fields.append("chunk_count = ?")
                update_values.append(chunk_count)

            if token_count is not None:
                update_fields.append("token_count = ?")
                update_values.append(token_count)

            update_values.append(doc_id)
            update_sql = f"UPDATE documents SET {', '.join(update_fields)} WHERE doc_id = ?"

            cursor.execute(update_sql, update_values)

            # Create new version record
            file_size = (
                os.path.getsize(source_path) if os.path.exists(source_path) else 0
            )
            cursor.execute(
                """
                INSERT INTO document_versions 
                (doc_id, version_number, file_hash, file_path, file_size, chunk_count)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    new_version,
                    new_file_hash,
                    source_path,
                    file_size,
                    chunk_count or 0,
                ),
            )

            self._conn.commit()
            logger.debug(f"Updated document {doc_id} to version {new_version}")

            return new_version

        except Exception as e:
            self._conn.rollback()
            raise

    def delete_document(self, doc_id: str) -> None:
        """
        Soft delete a document (mark as inactive).

        Args:
            doc_id: Document identifier
        """
        cursor = self._conn.cursor()

        cursor.execute(
            "UPDATE documents SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE doc_id = ?",
            (doc_id,),
        )

        if cursor.rowcount == 0:
            raise ValueError(f"Document {doc_id} not found")

        self._conn.commit()
        logger.debug(f"Deleted document: {doc_id}")

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document metadata.

        Args:
            doc_id: Document identifier

        Returns:
            Document metadata dict or None
        """
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_document_versions(self, doc_id: str) -> List[DocumentVersion]:
        """
        Get all versions of a document.

        Args:
            doc_id: Document identifier

        Returns:
            List of document versions sorted by version number
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT * FROM document_versions 
            WHERE doc_id = ? 
            ORDER BY version_number DESC
            """,
            (doc_id,),
        )

        versions = []
        for row in cursor.fetchall():
            versions.append(
                DocumentVersion(
                    doc_id=row["doc_id"],
                    version_number=row["version_number"],
                    file_hash=row["file_hash"],
                    file_path=row["file_path"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    file_size=row["file_size"],
                    chunk_count=row["chunk_count"],
                )
            )

        return versions

    def get_file_hash(self, source_path: str) -> Optional[str]:
        """
        Get stored file hash for a source path.

        Args:
            source_path: File path

        Returns:
            File hash or None if not found
        """
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT file_hash FROM documents WHERE source_path = ? AND is_active = 1",
            (source_path,),
        )

        row = cursor.fetchone()
        return row["file_hash"] if row else None

    def get_all_active_documents(self) -> List[Dict[str, Any]]:
        """
        Get all active documents.

        Returns:
            List of document metadata dicts
        """
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE is_active = 1")

        return [dict(row) for row in cursor.fetchall()]

    def log_update(
        self,
        added: int,
        updated: int,
        deleted: int,
        duration: float,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log an update operation.

        Args:
            added: Number of documents added
            updated: Number of documents updated
            deleted: Number of documents deleted
            duration: Duration in seconds
            status: Update status (success/failed)
            error_message: Error message if failed
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO update_history 
            (documents_added, documents_updated, documents_deleted, duration_seconds, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (added, updated, deleted, duration, status, error_message),
        )
        self._conn.commit()

    def get_statistics(self) -> KBStatistics:
        """
        Get knowledge base statistics.

        Returns:
            KBStatistics object
        """
        cursor = self._conn.cursor()

        # Total documents
        cursor.execute("SELECT COUNT(*) as count FROM documents WHERE is_active = 1")
        total_docs = cursor.fetchone()["count"]

        # Total chunks and tokens
        cursor.execute(
            "SELECT COALESCE(SUM(chunk_count), 0) as chunks, COALESCE(SUM(token_count), 0) as tokens FROM documents WHERE is_active = 1"
        )
        row = cursor.fetchone()
        total_chunks = row["chunks"]
        total_tokens = row["tokens"]

        # Last update time
        cursor.execute(
            "SELECT MAX(update_time) as last_update FROM update_history WHERE status = 'success'"
        )
        last_update_row = cursor.fetchone()
        last_update = (
            datetime.fromisoformat(last_update_row["last_update"])
            if last_update_row["last_update"]
            else None
        )

        # Unique sources
        cursor.execute(
            "SELECT COUNT(DISTINCT source_path) as count FROM documents WHERE is_active = 1"
        )
        unique_sources = cursor.fetchone()["count"]

        # Average chunk size
        avg_chunk_size = total_tokens / total_chunks if total_chunks > 0 else 0

        # Storage size (approximate)
        storage_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        storage_size_mb = storage_size / (1024 * 1024)

        return KBStatistics(
            total_documents=total_docs,
            total_chunks=total_chunks,
            total_tokens=total_tokens,
            last_update_time=last_update,
            unique_sources=unique_sources,
            average_chunk_size=avg_chunk_size,
            storage_size_mb=round(storage_size_mb, 2),
        )

    def close(self):
        """Close database connection"""
        if self._conn:
            self._conn.close()
            logger.debug("MetadataStore connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def compute_file_hash(file_path: str) -> str:
    """
    Compute MD5 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        MD5 hash string
    """
    hash_md5 = hashlib.md5()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()
