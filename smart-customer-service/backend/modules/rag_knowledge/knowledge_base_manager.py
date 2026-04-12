"""
Knowledge base manager with document CRUD, version control, and incremental updates
Integrates with RAG system for automatic re-indexing on changes
"""

import asyncio
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logging_config import LogCategory, get_logger
from core.tracing import create_span, score_trace

from .metadata_store import MetadataStore, compute_file_hash, KBStatistics
from .retrieval_strategy import BM25Retriever

logger = get_logger(LogCategory.RAG)


class KnowledgeBaseManager:
    """
    Manages knowledge base documents with version control and incremental updates.
    
    Features:
    - Document CRUD operations (add, update, delete, query)
    - Version control with history tracking
    - Incremental updates via file hash comparison
    - Scheduled automatic updates
    - Statistics and monitoring
    - Full Langfuse tracing
    """

    def __init__(
        self,
        rag_system: Any,
        metadata_db_path: str = ".lancedb/knowledge_base.db",
        watch_directories: Optional[List[str]] = None,
        update_interval_hours: int = 24,
    ):
        """
        Initialize knowledge base manager.

        Args:
            rag_system: RAGKnowledgeBase instance for indexing
            metadata_db_path: Path to SQLite metadata database
            watch_directories: Directories to watch for file changes
            update_interval_hours: Hours between automatic updates
        """
        self.rag_system = rag_system
        self.metadata_store = MetadataStore(metadata_db_path)
        self.watch_directories = watch_directories or []
        self.update_interval_hours = update_interval_hours

        # Scheduler for automatic updates
        self.scheduler = None
        self._is_running = False

        logger.info(
            f"KnowledgeBaseManager initialized: watching {len(self.watch_directories)} directories"
        )

    async def add_document(
        self,
        file_path: str,
        category: Optional[str] = None,
        title: Optional[str] = None,
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        """
        Add a new document to the knowledge base.

        Args:
            file_path: Path to the document file
            category: Document category (e.g., 'api_docs', 'troubleshooting')
            title: Document title
            force_reindex: Force re-indexing even if file hasn't changed

        Returns:
            Result dict with doc_id and status
        """
        with create_span("kb_add_document", input_data={
            "file_path": file_path,
            "category": category,
            "force_reindex": force_reindex,
        }) as span:
            start_time = time.time()

            try:
                # Validate file exists
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")

                # Compute file hash
                file_hash = compute_file_hash(file_path)

                # Check if document already exists
                existing_doc = self.metadata_store.get_document(file_path)

                if existing_doc and not force_reindex:
                    if existing_doc["file_hash"] == file_hash:
                        logger.info(f"Document unchanged, skipping: {file_path}")
                        return {
                            "doc_id": existing_doc["doc_id"],
                            "status": "unchanged",
                            "message": "File hash matches existing version",
                        }
                    else:
                        # File changed, update it
                        return await self.update_document(
                            file_path, category, title
                        )

                # Generate doc_id from file path
                doc_id = self._generate_doc_id(file_path)

                # Index document in RAG system
                index_result = await self.rag_system.add_documents([file_path])

                chunk_count = len(index_result.get("indexed_documents", []))
                token_count = sum(
                    doc.get("token_count", 0)
                    for doc in index_result.get("indexed_documents", [])
                )

                # Store metadata
                self.metadata_store.add_document(
                    doc_id=doc_id,
                    source_path=file_path,
                    file_hash=file_hash,
                    category=category,
                    title=title,
                    chunk_count=chunk_count,
                    token_count=token_count,
                )

                duration = time.time() - start_time
                score_trace("kb_add_duration_ms", duration * 1000)

                span.end(
                    output_data={
                        "doc_id": doc_id,
                        "status": "success",
                        "chunks": chunk_count,
                        "duration_ms": duration * 1000,
                    }
                )

                logger.info(
                    f"Added document: {doc_id} ({chunk_count} chunks, {duration:.2f}s)"
                )

                return {
                    "doc_id": doc_id,
                    "status": "success",
                    "chunks": chunk_count,
                    "tokens": token_count,
                    "version": 1,
                }

            except Exception as e:
                logger.error(f"Failed to add document {file_path}: {e}")
                span.end(output_data={"error": str(e)})
                raise

    async def update_document(
        self,
        file_path: str,
        category: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing document (creates new version).

        Args:
            file_path: Path to the document file
            category: Updated category (optional)
            title: Updated title (optional)

        Returns:
            Result dict with new version number
        """
        with create_span("kb_update_document", input_data={
            "file_path": file_path,
        }) as span:
            start_time = time.time()

            try:
                # Validate file exists
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")

                # Compute new file hash
                new_hash = compute_file_hash(file_path)

                # Get existing document
                doc_id = self._generate_doc_id(file_path)
                existing = self.metadata_store.get_document(doc_id)

                if not existing:
                    # Document doesn't exist, add it instead
                    return await self.add_document(file_path, category, title)

                if existing["file_hash"] == new_hash:
                    logger.info(f"Document unchanged: {doc_id}")
                    return {
                        "doc_id": doc_id,
                        "status": "unchanged",
                        "version": existing["current_version"],
                    }

                # Remove old vectors from RAG system
                await self._remove_document_vectors(doc_id)

                # Re-index document
                index_result = await self.rag_system.add_documents([file_path])

                chunk_count = len(index_result.get("indexed_documents", []))
                token_count = sum(
                    doc.get("token_count", 0)
                    for doc in index_result.get("indexed_documents", [])
                )

                # Update metadata and create new version
                new_version = self.metadata_store.update_document(
                    doc_id=doc_id,
                    new_file_hash=new_hash,
                    chunk_count=chunk_count,
                    token_count=token_count,
                )

                duration = time.time() - start_time
                score_trace("kb_update_duration_ms", duration * 1000)

                span.end(
                    output_data={
                        "doc_id": doc_id,
                        "status": "updated",
                        "new_version": new_version,
                        "chunks": chunk_count,
                        "duration_ms": duration * 1000,
                    }
                )

                logger.info(
                    f"Updated document: {doc_id} v{new_version} ({duration:.2f}s)"
                )

                return {
                    "doc_id": doc_id,
                    "status": "updated",
                    "old_version": existing["current_version"],
                    "new_version": new_version,
                    "chunks": chunk_count,
                    "tokens": token_count,
                }

            except Exception as e:
                logger.error(f"Failed to update document {file_path}: {e}")
                span.end(output_data={"error": str(e)})
                raise

    async def delete_document(self, doc_id_or_path: str) -> Dict[str, Any]:
        """
        Delete a document from the knowledge base.

        Args:
            doc_id_or_path: Document ID or file path

        Returns:
            Result dict with deletion status
        """
        with create_span("kb_delete_document", input_data={
            "identifier": doc_id_or_path,
        }) as span:
            try:
                # Determine doc_id
                if os.path.exists(doc_id_or_path):
                    doc_id = self._generate_doc_id(doc_id_or_path)
                else:
                    doc_id = doc_id_or_path

                # Get document metadata
                doc_metadata = self.metadata_store.get_document(doc_id)
                if not doc_metadata:
                    raise ValueError(f"Document not found: {doc_id}")

                # Remove vectors from RAG system
                await self._remove_document_vectors(doc_id)

                # Soft delete in metadata store
                self.metadata_store.delete_document(doc_id)

                span.end(
                    output_data={
                        "doc_id": doc_id,
                        "status": "deleted",
                    }
                )

                logger.info(f"Deleted document: {doc_id}")

                return {
                    "doc_id": doc_id,
                    "status": "deleted",
                    "source_path": doc_metadata["source_path"],
                }

            except Exception as e:
                logger.error(f"Failed to delete document {doc_id_or_path}: {e}")
                span.end(output_data={"error": str(e)})
                raise

    async def perform_incremental_update(self) -> Dict[str, Any]:
        """
        Perform incremental update by scanning watched directories.
        Detects new, modified, and deleted files.

        Returns:
            Update summary with counts of added/updated/deleted documents
        """
        with create_span("kb_incremental_update") as main_span:
            start_time = time.time()

            added_count = 0
            updated_count = 0
            deleted_count = 0
            errors = []

            try:
                for directory in self.watch_directories:
                    if not os.path.exists(directory):
                        logger.warning(f"Watch directory not found: {directory}")
                        continue

                    dir_span = create_span("scan_directory", input_data={
                        "directory": directory,
                    })

                    # Scan directory for supported files
                    supported_extensions = {".pdf", ".md", ".txt", ".html", ".docx"}
                    files_found = []

                    for root, _, files in os.walk(directory):
                        for filename in files:
                            ext = os.path.splitext(filename)[1].lower()
                            if ext in supported_extensions:
                                files_found.append(os.path.join(root, filename))

                    dir_span.add_event(
                        "files_scanned",
                        output_data={"count": len(files_found)},
                    )

                    # Process each file
                    for file_path in files_found:
                        try:
                            result = await self._process_file_for_update(file_path)
                            
                            if result["action"] == "added":
                                added_count += 1
                            elif result["action"] == "updated":
                                updated_count += 1
                            elif result["action"] == "skipped":
                                pass  # No change

                        except Exception as e:
                            error_msg = f"Failed to process {file_path}: {str(e)}"
                            errors.append(error_msg)
                            logger.error(error_msg)

                    dir_span.end(
                        output_data={
                            "processed": len(files_found),
                            "errors": len([e for e in errors if file_path in e]),
                        }
                    )

                # Check for deleted files
                deleted_count = await self._check_deleted_files()

                duration = time.time() - start_time

                # Log update operation
                status = "success" if not errors else "partial_success"
                self.metadata_store.log_update(
                    added=added_count,
                    updated=updated_count,
                    deleted=deleted_count,
                    duration=duration,
                    status=status,
                    error_message="; ".join(errors) if errors else None,
                )

                score_trace("kb_update_total_duration_ms", duration * 1000)
                score_trace("kb_documents_added", added_count)
                score_trace("kb_documents_updated", updated_count)
                score_trace("kb_documents_deleted", deleted_count)

                main_span.end(
                    output_data={
                        "added": added_count,
                        "updated": updated_count,
                        "deleted": deleted_count,
                        "errors": len(errors),
                        "duration_ms": duration * 1000,
                    }
                )

                logger.info(
                    f"Incremental update completed: +{added_count} ~{updated_count} -{deleted_count} "
                    f"({duration:.2f}s)"
                )

                return {
                    "status": status,
                    "added": added_count,
                    "updated": updated_count,
                    "deleted": deleted_count,
                    "errors": errors,
                    "duration_seconds": round(duration, 2),
                    "timestamp": datetime.now().isoformat(),
                }

            except Exception as e:
                duration = time.time() - start_time
                error_msg = f"Incremental update failed: {str(e)}"
                
                self.metadata_store.log_update(
                    added=0,
                    updated=0,
                    deleted=0,
                    duration=duration,
                    status="failed",
                    error_message=error_msg,
                )

                logger.error(error_msg)
                main_span.end(output_data={"error": error_msg})
                raise

    async def _process_file_for_update(self, file_path: str) -> Dict[str, Any]:
        """
        Process a single file for incremental update.

        Args:
            file_path: Path to file

        Returns:
            Action taken (added/updated/skipped)
        """
        doc_id = self._generate_doc_id(file_path)
        current_hash = compute_file_hash(file_path)

        stored_hash = self.metadata_store.get_file_hash(file_path)

        if not stored_hash:
            # New file
            await self.add_document(file_path)
            return {"action": "added", "doc_id": doc_id}
        elif stored_hash != current_hash:
            # Modified file
            await self.update_document(file_path)
            return {"action": "updated", "doc_id": doc_id}
        else:
            # Unchanged
            return {"action": "skipped", "doc_id": doc_id}

    async def _check_deleted_files(self) -> int:
        """
        Check for files that have been deleted from watched directories.

        Returns:
            Number of deleted documents
        """
        deleted_count = 0
        active_docs = self.metadata_store.get_all_active_documents()

        for doc in active_docs:
            source_path = doc["source_path"]
            
            # Check if file still exists in any watched directory
            file_exists = any(
                source_path.startswith(directory)
                for directory in self.watch_directories
            ) and os.path.exists(source_path)

            if not file_exists:
                try:
                    await self.delete_document(doc["doc_id"])
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete orphaned document {doc['doc_id']}: {e}")

        return deleted_count

    async def _remove_document_vectors(self, doc_id: str) -> None:
        """
        Remove document vectors from RAG system.

        Args:
            doc_id: Document identifier
        """
        # This would integrate with the vector database to delete vectors
        # For now, we'll log the operation
        logger.debug(f"Removing vectors for document: {doc_id}")
        
        # TODO: Implement actual vector deletion based on your vector DB
        # Example for LanceDB:
        # if hasattr(self.rag_system, 'table'):
        #     self.rag_system.table.delete(f"doc_id = '{doc_id}'")

    def get_statistics(self) -> KBStatistics:
        """
        Get knowledge base statistics.

        Returns:
            KBStatistics object
        """
        return self.metadata_store.get_statistics()

    def get_document_history(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Get version history for a document.

        Args:
            doc_id: Document identifier

        Returns:
            List of version dicts
        """
        versions = self.metadata_store.get_document_versions(doc_id)
        return [
            {
                "version": v.version_number,
                "file_hash": v.file_hash,
                "file_path": v.file_path,
                "created_at": v.created_at.isoformat(),
                "file_size": v.file_size,
                "chunk_count": v.chunk_count,
            }
            for v in versions
        ]

    def start_scheduler(self):
        """Start the automatic update scheduler"""
        if self.scheduler:
            logger.warning("Scheduler already running")
            return

        self.scheduler = AsyncIOScheduler()

        # Schedule periodic incremental updates
        self.scheduler.add_job(
            self.perform_incremental_update,
            trigger=CronTrigger(hour=f"*/{self.update_interval_hours}"),
            id="kb_incremental_update",
            name="Knowledge Base Incremental Update",
            replace_existing=True,
        )

        self.scheduler.start()
        self._is_running = True

        logger.info(
            f"Scheduled incremental updates every {self.update_interval_hours} hours"
        )

    def stop_scheduler(self):
        """Stop the automatic update scheduler"""
        if self.scheduler:
            self.scheduler.shutdown()
            self.scheduler = None
            self._is_running = False
            logger.info("Scheduler stopped")

    @staticmethod
    def _generate_doc_id(file_path: str) -> str:
        """
        Generate a unique document ID from file path.

        Args:
            file_path: Absolute file path

        Returns:
            Document ID string
        """
        # Use relative path from project root or full path hash
        import hashlib

        path_hash = hashlib.md5(file_path.encode()).hexdigest()[:12]
        filename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(filename)[0]

        return f"doc_{name_without_ext}_{path_hash}"

    def close(self):
        """Cleanup resources"""
        self.stop_scheduler()
        self.metadata_store.close()
        logger.info("KnowledgeBaseManager closed")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()
