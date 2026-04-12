"""
Tests for knowledge base manager (metadata store, CRUD, version control)
"""

import os
import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from modules.rag_knowledge.metadata_store import MetadataStore, compute_file_hash, KBStatistics


class TestMetadataStore:
    """Test suite for MetadataStore"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def metadata_store(self, temp_db):
        """Create metadata store instance"""
        store = MetadataStore(temp_db)
        yield store
        store.close()

    def test_initialization_creates_tables(self, metadata_store):
        """Test that initialization creates database tables"""
        assert os.path.exists(metadata_store.db_path)
        
        # Check tables exist
        cursor = metadata_store._conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        assert "documents" in tables
        assert "document_versions" in tables
        assert "update_history" in tables

    def test_add_document(self, metadata_store):
        """Test adding a document to metadata store"""
        metadata_store.add_document(
            doc_id="doc_001",
            source_path="/path/to/doc.pdf",
            file_hash="abc123",
            category="api_docs",
            title="API Guide",
            chunk_count=10,
            token_count=5000,
        )

        doc = metadata_store.get_document("doc_001")
        assert doc is not None
        assert doc["doc_id"] == "doc_001"
        assert doc["source_path"] == "/path/to/doc.pdf"
        assert doc["file_hash"] == "abc123"
        assert doc["category"] == "api_docs"
        assert doc["title"] == "API Guide"
        assert doc["chunk_count"] == 10
        assert doc["token_count"] == 5000
        assert doc["current_version"] == 1
        assert doc["is_active"] == 1

    def test_add_duplicate_document_raises_error(self, metadata_store):
        """Test that adding duplicate document raises error"""
        metadata_store.add_document(
            doc_id="doc_001",
            source_path="/path/to/doc.pdf",
            file_hash="abc123",
        )

        with pytest.raises(ValueError, match="already exists"):
            metadata_store.add_document(
                doc_id="doc_001",
                source_path="/path/to/doc.pdf",
                file_hash="def456",
            )

    def test_update_document_creates_new_version(self, metadata_store):
        """Test updating document creates new version"""
        # Add initial document
        metadata_store.add_document(
            doc_id="doc_001",
            source_path="/path/to/doc.pdf",
            file_hash="abc123",
            chunk_count=10,
        )

        # Update document
        new_version = metadata_store.update_document(
            doc_id="doc_001",
            new_file_hash="def456",
            chunk_count=15,
        )

        assert new_version == 2

        # Verify document updated
        doc = metadata_store.get_document("doc_001")
        assert doc["file_hash"] == "def456"
        assert doc["current_version"] == 2
        assert doc["chunk_count"] == 15

        # Verify version history
        versions = metadata_store.get_document_versions("doc_001")
        assert len(versions) == 2
        assert versions[0].version_number == 2
        assert versions[1].version_number == 1

    def test_delete_document_soft_deletes(self, metadata_store):
        """Test that delete performs soft delete"""
        metadata_store.add_document(
            doc_id="doc_001",
            source_path="/path/to/doc.pdf",
            file_hash="abc123",
        )

        metadata_store.delete_document("doc_001")

        # Document should be marked inactive
        doc = metadata_store.get_document("doc_001")
        assert doc["is_active"] == 0

        # Should not appear in active documents
        active_docs = metadata_store.get_all_active_documents()
        assert len(active_docs) == 0

    def test_get_document_versions_returns_sorted(self, metadata_store):
        """Test that versions are returned sorted by version number descending"""
        metadata_store.add_document(
            doc_id="doc_001",
            source_path="/path/to/doc.pdf",
            file_hash="v1",
        )

        metadata_store.update_document("doc_001", "v2")
        metadata_store.update_document("doc_001", "v3")

        versions = metadata_store.get_document_versions("doc_001")

        assert len(versions) == 3
        assert versions[0].version_number == 3
        assert versions[1].version_number == 2
        assert versions[2].version_number == 1

    def test_get_file_hash(self, metadata_store):
        """Test retrieving file hash by source path"""
        metadata_store.add_document(
            doc_id="doc_001",
            source_path="/path/to/doc.pdf",
            file_hash="abc123",
        )

        stored_hash = metadata_store.get_file_hash("/path/to/doc.pdf")
        assert stored_hash == "abc123"

    def test_get_file_hash_nonexistent_returns_none(self, metadata_store):
        """Test that nonexistent file returns None"""
        stored_hash = metadata_store.get_file_hash("/nonexistent/file.pdf")
        assert stored_hash is None

    def test_log_update(self, metadata_store):
        """Test logging update operations"""
        metadata_store.log_update(
            added=5,
            updated=3,
            deleted=1,
            duration=12.5,
            status="success",
        )

        cursor = metadata_store._conn.cursor()
        cursor.execute("SELECT * FROM update_history ORDER BY id DESC LIMIT 1")
        log = cursor.fetchone()

        assert log["documents_added"] == 5
        assert log["documents_updated"] == 3
        assert log["documents_deleted"] == 1
        assert log["duration_seconds"] == 12.5
        assert log["status"] == "success"

    def test_get_statistics(self, metadata_store):
        """Test getting knowledge base statistics"""
        # Add some documents
        metadata_store.add_document(
            doc_id="doc_001",
            source_path="/path/to/doc1.pdf",
            file_hash="hash1",
            chunk_count=10,
            token_count=5000,
        )

        metadata_store.add_document(
            doc_id="doc_002",
            source_path="/path/to/doc2.pdf",
            file_hash="hash2",
            chunk_count=15,
            token_count=7500,
        )

        stats = metadata_store.get_statistics()

        assert stats.total_documents == 2
        assert stats.total_chunks == 25
        assert stats.total_tokens == 12500
        assert stats.unique_sources == 2
        assert stats.average_chunk_size == 500.0  # 12500 / 25
        assert isinstance(stats.storage_size_mb, float)

    def test_compute_file_hash(self, tmp_path):
        """Test MD5 file hash computation"""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        file_hash = compute_file_hash(str(test_file))

        assert isinstance(file_hash, str)
        assert len(file_hash) == 32  # MD5 produces 32-char hex string

        # Same content should produce same hash
        file_hash2 = compute_file_hash(str(test_file))
        assert file_hash == file_hash2

    def test_compute_file_hash_different_content(self, tmp_path):
        """Test that different content produces different hash"""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("Content A")
        file2.write_text("Content B")

        hash1 = compute_file_hash(str(file1))
        hash2 = compute_file_hash(str(file2))

        assert hash1 != hash2


class TestKnowledgeBaseManager:
    """Test suite for KnowledgeBaseManager"""

    @pytest.fixture
    def mock_rag_system(self):
        """Create mock RAG system"""
        mock = AsyncMock()
        mock.add_documents = AsyncMock(return_value={
            "indexed_documents": [
                {"token_count": 100},
                {"token_count": 150},
            ]
        })
        return mock

    @pytest.fixture
    async def kb_manager(self, mock_rag_system, tmp_path):
        """Create knowledge base manager instance"""
        from modules.rag_knowledge.knowledge_base_manager import KnowledgeBaseManager

        db_path = str(tmp_path / "kb_test.db")
        watch_dir = str(tmp_path / "watch")
        os.makedirs(watch_dir, exist_ok=True)

        manager = KnowledgeBaseManager(
            rag_system=mock_rag_system,
            metadata_db_path=db_path,
            watch_directories=[watch_dir],
            update_interval_hours=24,
        )

        yield manager
        manager.close()

    @pytest.mark.asyncio
    async def test_add_document(self, kb_manager, tmp_path):
        """Test adding a document"""
        # Create test file
        test_file = tmp_path / "test_doc.md"
        test_file.write_text("# Test Document\nThis is a test.")

        result = await kb_manager.add_document(str(test_file), category="test")

        assert result["status"] == "success"
        assert "doc_id" in result
        assert result["chunks"] == 2
        assert result["tokens"] == 250

    @pytest.mark.asyncio
    async def test_add_document_unchanged(self, kb_manager, tmp_path):
        """Test adding unchanged document returns 'unchanged' status"""
        # Create test file
        test_file = tmp_path / "test_doc.md"
        test_file.write_text("# Test Document")

        # Add first time
        await kb_manager.add_document(str(test_file))

        # Add again (should detect unchanged)
        result = await kb_manager.add_document(str(test_file))

        assert result["status"] == "unchanged"

    @pytest.mark.asyncio
    async def test_update_document(self, kb_manager, tmp_path):
        """Test updating a document"""
        # Create and add document
        test_file = tmp_path / "test_doc.md"
        test_file.write_text("# Version 1")
        await kb_manager.add_document(str(test_file))

        # Modify file
        test_file.write_text("# Version 2 - Updated content")

        # Update
        result = await kb_manager.update_document(str(test_file))

        assert result["status"] == "updated"
        assert result["new_version"] == 2
        assert result["old_version"] == 1

    @pytest.mark.asyncio
    async def test_delete_document(self, kb_manager, tmp_path):
        """Test deleting a document"""
        # Add document
        test_file = tmp_path / "test_doc.md"
        test_file.write_text("# Test")
        add_result = await kb_manager.add_document(str(test_file))

        # Delete
        delete_result = await kb_manager.delete_document(add_result["doc_id"])

        assert delete_result["status"] == "deleted"

        # Verify document is deleted
        doc = kb_manager.metadata_store.get_document(add_result["doc_id"])
        assert doc["is_active"] == 0

    @pytest.mark.asyncio
    async def test_incremental_update_detects_changes(self, kb_manager, tmp_path):
        """Test incremental update detects file changes"""
        watch_dir = kb_manager.watch_directories[0]

        # Create initial file
        test_file = Path(watch_dir) / "doc1.md"
        test_file.write_text("# Initial content")

        # First update (should add)
        result1 = await kb_manager.perform_incremental_update()
        assert result1["added"] >= 1

        # Modify file
        test_file.write_text("# Updated content")

        # Second update (should detect update)
        result2 = await kb_manager.perform_incremental_update()
        assert result2["updated"] >= 1

    @pytest.mark.asyncio
    async def test_incremental_update_detects_deletions(self, kb_manager, tmp_path):
        """Test incremental update detects deleted files"""
        watch_dir = kb_manager.watch_directories[0]

        # Create file
        test_file = Path(watch_dir) / "doc1.md"
        test_file.write_text("# Test")

        # Add it
        await kb_manager.perform_incremental_update()

        # Delete file
        test_file.unlink()

        # Update should detect deletion
        result = await kb_manager.perform_incremental_update()
        assert result["deleted"] >= 1

    def test_get_statistics(self, kb_manager, tmp_path):
        """Test getting statistics"""
        stats = kb_manager.get_statistics()

        assert isinstance(stats, KBStatistics)
        assert stats.total_documents == 0  # Initially empty
        assert isinstance(stats.storage_size_mb, float)

    def test_get_document_history(self, kb_manager, tmp_path):
        """Test getting document version history"""
        # This would require actually adding/updating documents
        # For now, test with empty history
        history = kb_manager.get_document_history("nonexistent_doc")
        assert history == []

    def test_scheduler_starts_and_stops(self, kb_manager):
        """Test scheduler start/stop"""
        kb_manager.start_scheduler()
        assert kb_manager.scheduler is not None
        assert kb_manager._is_running is True

        kb_manager.stop_scheduler()
        assert kb_manager.scheduler is None
        assert kb_manager._is_running is False

    def test_generate_doc_id(self, kb_manager):
        """Test document ID generation"""
        doc_id1 = kb_manager._generate_doc_id("/path/to/document.pdf")
        doc_id2 = kb_manager._generate_doc_id("/path/to/document.pdf")

        # Same path should generate same ID
        assert doc_id1 == doc_id2

        # Different paths should generate different IDs
        doc_id3 = kb_manager._generate_doc_id("/different/path.pdf")
        assert doc_id1 != doc_id3

        # ID format should be consistent
        assert doc_id1.startswith("doc_")


class TestIntegration:
    """Integration tests for complete workflow"""

    @pytest.mark.asyncio
    async def test_full_document_lifecycle(self, tmp_path):
        """Test complete document lifecycle: add -> update -> delete"""
        from modules.rag_knowledge.knowledge_base_manager import KnowledgeBaseManager

        # Setup
        mock_rag = AsyncMock()
        mock_rag.add_documents = AsyncMock(return_value={
            "indexed_documents": [{"token_count": 100}]
        })

        db_path = str(tmp_path / "lifecycle_test.db")
        manager = KnowledgeBaseManager(
            rag_system=mock_rag,
            metadata_db_path=db_path,
        )

        try:
            # Create test file
            test_file = tmp_path / "lifecycle.md"
            test_file.write_text("# Version 1")

            # Add
            add_result = await manager.add_document(str(test_file))
            assert add_result["status"] == "success"
            doc_id = add_result["doc_id"]

            # Update
            test_file.write_text("# Version 2")
            update_result = await manager.update_document(str(test_file))
            assert update_result["status"] == "updated"
            assert update_result["new_version"] == 2

            # Get history
            history = manager.get_document_history(doc_id)
            assert len(history) == 2

            # Delete
            delete_result = await manager.delete_document(doc_id)
            assert delete_result["status"] == "deleted"

            # Verify deleted
            doc = manager.metadata_store.get_document(doc_id)
            assert doc["is_active"] == 0

        finally:
            manager.close()
