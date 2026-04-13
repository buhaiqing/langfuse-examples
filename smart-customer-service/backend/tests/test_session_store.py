"""会话存储模块测试套件。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from modules.dialogue_manager.session_store import SessionStore


class TestSessionStore:
    """SessionStore测试套件。"""

    @pytest.fixture
    def mock_redis(self):
        """创建Mock Redis客户端。"""
        redis_mock = MagicMock()
        redis_mock.setex = AsyncMock()
        redis_mock.get = AsyncMock()
        redis_mock.delete = AsyncMock()
        redis_mock.scan_iter = MagicMock()
        redis_mock.ttl = AsyncMock()
        redis_mock.aclose = AsyncMock()
        return redis_mock

    @pytest.fixture
    def session_store(self, mock_redis):
        """创建会话存储fixture（使用Mock Redis）。"""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = SessionStore(
                redis_url="redis://localhost:6379",
                serialization_format="msgpack",
                compression_enabled=True,
                default_ttl=3600,
            )
            store.redis_client = mock_redis
            return store

    @pytest.mark.asyncio
    async def test_save_session(self, session_store, mock_redis):
        """测试保存会话。"""
        session_id = "test_session_123"
        state = {"user_id": "user_456", "messages": [{"role": "user", "content": "Hello"}]}

        await session_store.save_session(session_id, state)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == f"session:{session_id}:state"
        assert call_args[0][1] == 3600  # TTL

    @pytest.mark.asyncio
    async def test_load_session_existing(self, session_store, mock_redis):
        """测试加载存在的会话。"""
        session_id = "test_session_123"
        state = {"user_id": "user_456", "messages": []}

        # Mock序列化后的数据
        import msgpack
        serialized = msgpack.packb(state, use_bin_type=True)
        mock_redis.get.return_value = serialized

        result = await session_store.load_session(session_id)

        assert result is not None
        assert result["user_id"] == "user_456"
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_session_not_found(self, session_store, mock_redis):
        """测试加载不存在的会话。"""
        mock_redis.get.return_value = None

        result = await session_store.load_session("nonexistent_session")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_session(self, session_store, mock_redis):
        """测试删除会话。"""
        session_id = "test_session_123"

        await session_store.delete_session(session_id)

        mock_redis.delete.assert_called_once()
        call_args = mock_redis.delete.call_args
        assert call_args[0][0] == f"session:{session_id}:state"

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, session_store, mock_redis):
        """测试获取活跃会话列表。"""
        # Mock scan_iter返回的keys
        async def mock_scan_iter(match):
            yield b"session:session1:state"
            yield b"session:session2:state"
            yield b"session:session3:state"

        mock_redis.scan_iter = mock_scan_iter

        sessions = await session_store.get_active_sessions()

        assert len(sessions) == 3
        assert "session1" in sessions
        assert "session2" in sessions
        assert "session3" in sessions

    @pytest.mark.asyncio
    async def test_get_session_ttl(self, session_store, mock_redis):
        """测试获取会话TTL。"""
        session_id = "test_session_123"
        mock_redis.ttl.return_value = 1800

        ttl = await session_store.get_session_ttl(session_id)

        assert ttl == 1800
        mock_redis.ttl.assert_called_once()

    @pytest.mark.asyncio
    async def test_serialization_json(self):
        """测试JSON序列化格式。"""
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_redis.aclose = AsyncMock()
            mock_from_url.return_value = mock_redis

            store = SessionStore(
                redis_url="redis://localhost:6379",
                serialization_format="json",
                compression_enabled=False,
            )
            store.redis_client = mock_redis

            # 测试序列化
            data = {"key": "value", "number": 123}
            serialized = store._serialize(data)
            deserialized = store._deserialize(serialized)

            assert deserialized == data

    @pytest.mark.asyncio
    async def test_serialization_msgpack(self):
        """测试MessagePack序列化格式。"""
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_redis.aclose = AsyncMock()
            mock_from_url.return_value = mock_redis

            store = SessionStore(
                redis_url="redis://localhost:6379",
                serialization_format="msgpack",
                compression_enabled=False,
            )
            store.redis_client = mock_redis

            # 测试序列化
            data = {"key": "value", "number": 123}
            serialized = store._serialize(data)
            deserialized = store._deserialize(serialized)

            assert deserialized == data

    @pytest.mark.asyncio
    async def test_compression_enabled(self, session_store):
        """测试压缩功能。"""
        # 大数据应该被压缩
        large_data = {"data": "x" * 1000}
        serialized = session_store._serialize(large_data)

        # 检查是否有压缩标记
        assert serialized.startswith(b"COMPRESSED:")

        # 验证可以正确反序列化
        deserialized = session_store._deserialize(serialized)
        assert deserialized == large_data

    @pytest.mark.asyncio
    async def test_compression_disabled_small_data(self):
        """测试小数据不压缩。"""
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_redis.aclose = AsyncMock()
            mock_from_url.return_value = mock_redis

            store = SessionStore(
                redis_url="redis://localhost:6379",
                compression_enabled=True,
            )
            store.redis_client = mock_redis

            # 小数据不应该被压缩
            small_data = {"key": "value"}
            serialized = store._serialize(small_data)

            # 检查没有压缩标记
            assert not serialized.startswith(b"COMPRESSED:")

    @pytest.mark.asyncio
    async def test_save_session_with_custom_ttl(self, session_store, mock_redis):
        """测试保存会话时使用自定义TTL。"""
        session_id = "test_session"
        state = {"data": "test"}
        custom_ttl = 7200

        await session_store.save_session(session_id, state, ttl=custom_ttl)

        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == custom_ttl

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试异步上下文管理器。"""
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_redis.aclose = AsyncMock()
            mock_from_url.return_value = mock_redis

            async with SessionStore(redis_url="redis://localhost:6379") as store:
                assert store.redis_client is not None

            mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_method(self, session_store, mock_redis):
        """测试关闭方法。"""
        await session_store.close()
        mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_session_error_handling(self, session_store, mock_redis):
        """测试保存会话时的错误处理。"""
        mock_redis.setex.side_effect = Exception("Redis connection failed")

        with pytest.raises(Exception):
            await session_store.save_session("test_session", {"data": "test"})

    @pytest.mark.asyncio
    async def test_load_session_error_handling(self, session_store, mock_redis):
        """测试加载会话时的错误处理。"""
        mock_redis.get.side_effect = Exception("Redis connection failed")

        with pytest.raises(Exception):
            await session_store.load_session("test_session")
