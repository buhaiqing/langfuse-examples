"""ChromaDB 向量数据库客户端测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.storage.chroma_client import ChromaClient, chroma_client


class TestChromaClient:
    """ChromaDB 客户端测试"""

    @pytest.fixture
    def client(self):
        """创建 ChromaDB 客户端实例"""
        return ChromaClient(host="localhost", port=8000, collection_name="test_collection")

    def test_init(self, client):
        """测试初始化"""
        assert client.host == "localhost"
        assert client.port == 8000
        assert client.collection_name == "test_collection"
        assert client.client is None

    def test_singleton_instance(self):
        """测试单例模式"""
        assert chroma_client is not None

    @pytest.mark.asyncio
    async def test_connect(self, client):
        """测试连接 ChromaDB"""
        with patch("backend.storage.chroma_client.chromadb.Client") as mock_chromadb:
            mock_client = MagicMock()
            mock_chromadb.return_value = mock_client

            await client.connect()

            assert client.client is not None
            mock_chromadb.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_documents(self, client):
        """测试添加文档"""
        client._get_or_create_collection = AsyncMock()
        mock_collection = MagicMock()
        client._get_or_create_collection.return_value = mock_collection

        from langchain_core.documents import Document

        docs = [
            Document(page_content="内容 1", metadata={"source": "doc1.pdf"}),
            Document(page_content="内容 2", metadata={"source": "doc2.pdf"}),
        ]

        await client.add_documents(docs)

        mock_collection.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_similarity_search(self, client):
        """测试相似性搜索"""
        client._get_or_create_collection = AsyncMock()
        mock_collection = MagicMock()
        mock_collection.query = MagicMock(
            return_value={
                "documents": [["文档内容"]],
                "metadatas": [[{"source": "doc.pdf"}]],
                "distances": [[0.5]],
            }
        )
        client._get_or_create_collection.return_value = mock_collection

        results = await client.similarity_search("查询", k=3)

        assert len(results) > 0
        mock_collection.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_similarity_search_with_filter(self, client):
        """测试带过滤的相似性搜索"""
        client._get_or_create_collection = AsyncMock()
        mock_collection = MagicMock()
        mock_collection.query = MagicMock(
            return_value={
                "documents": [["文档内容"]],
                "metadatas": [[{"source": "doc.pdf", "category": "api"}]],
                "distances": [[0.5]],
            }
        )
        client._get_or_create_collection.return_value = mock_collection

        results = await client.similarity_search("查询", k=3, filter_metadata={"category": "api"})

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_delete_documents(self, client):
        """测试删除文档"""
        client._get_or_create_collection = AsyncMock()
        mock_collection = MagicMock()
        client._get_or_create_collection.return_value = mock_collection

        await client.delete_documents(["doc_id_1", "doc_id_2"])

        mock_collection.delete.assert_called_once_with(ids=["doc_id_1", "doc_id_2"])

    @pytest.mark.asyncio
    async def test_get_or_create_collection(self, client):
        """测试获取或创建集合"""
        client.client = MagicMock()
        mock_collection = MagicMock()
        client.client.get_collection = MagicMock(side_effect=ValueError("Not found"))
        client.client.create_collection = MagicMock(return_value=mock_collection)

        collection = await client._get_or_create_collection("test_collection")

        assert collection == mock_collection
        client.client.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_collection_exists(self, client):
        """测试获取存在的集合"""
        client.client = MagicMock()
        mock_collection = MagicMock()
        client.client.get_collection = MagicMock(return_value=mock_collection)

        collection = await client._get_or_create_collection("existing_collection")

        assert collection == mock_collection
        client.client.get_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_collection_stats(self, client):
        """测试获取集合统计"""
        client._get_or_create_collection = AsyncMock()
        mock_collection = MagicMock()
        mock_collection.count = MagicMock(return_value=100)
        client._get_or_create_collection.return_value = mock_collection

        stats = await client.get_collection_stats()

        assert stats["document_count"] == 100

    @pytest.mark.asyncio
    async def test_clear_collection(self, client):
        """测试清空集合"""
        client._get_or_create_collection = AsyncMock()
        mock_collection = MagicMock()
        mock_collection.get = MagicMock(return_value={"ids": ["id1", "id2"]})
        mock_collection.delete = MagicMock()
        client._get_or_create_collection.return_value = mock_collection

        await client.clear_collection()

        mock_collection.delete.assert_called()

    @pytest.mark.asyncio
    async def test_add_documents_batch(self, client):
        """测试批量添加文档"""
        from langchain_core.documents import Document

        docs = [Document(page_content=f"内容{i}") for i in range(150)]

        client._get_or_create_collection = AsyncMock()
        mock_collection = MagicMock()
        client._get_or_create_collection.return_value = mock_collection

        await client.add_documents(docs, batch_size=100)

        # 应该分 2 批添加
        assert mock_collection.add.call_count == 2
