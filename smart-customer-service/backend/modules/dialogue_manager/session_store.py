"""
会话存储模块 - 基于Redis的会话状态持久化。

提供会话的保存、加载、删除功能，支持序列化、压缩和TTL管理。
"""

import json
import logging
import zlib
from typing import Any, Dict, List, Optional

import msgpack
from langfuse import observe

logger = logging.getLogger(__name__)


class SessionStore:
    """基于Redis的会话存储后端。

    支持JSON和MessagePack两种序列化格式，可选LZ4压缩，
    并实现TTL自动过期机制。

    Attributes:
        redis_client: Redis客户端实例
        serialization_format: 序列化格式 ('json' 或 'msgpack')
        compression_enabled: 是否启用压缩
        default_ttl: 默认TTL（秒）
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        serialization_format: str = "msgpack",
        compression_enabled: bool = True,
        default_ttl: int = 86400,
        password: Optional[str] = None,
    ):
        """初始化会话存储。

        Args:
            redis_url: Redis连接URL
            serialization_format: 序列化格式 ('json' 或 'msgpack')
            compression_enabled: 是否启用压缩
            default_ttl: 默认TTL（秒），默认24小时
            password: Redis密码（可选）
        """
        try:
            import redis.asyncio as redis
        except ImportError:
            raise ImportError(
                "需要安装 redis 库。请运行: pip install redis"
            )

        self.redis_url = redis_url
        self.serialization_format = serialization_format
        self.compression_enabled = compression_enabled
        self.default_ttl = default_ttl

        # 创建Redis连接池
        self.redis_client = redis.from_url(
            redis_url,
            password=password,
            decode_responses=False,  # 返回bytes以便压缩
        )

        logger.info(
            f"SessionStore initialized: format={serialization_format}, "
            f"compression={compression_enabled}, ttl={default_ttl}s"
        )

    def _serialize(self, data: Dict[str, Any]) -> bytes:
        """序列化数据。

        Args:
            data: 要序列化的数据字典

        Returns:
            序列化后的字节数据
        """
        if self.serialization_format == "msgpack":
            serialized = msgpack.packb(data, use_bin_type=True)
        else:
            serialized = json.dumps(data).encode("utf-8")

        # 如果启用压缩且数据足够大
        if self.compression_enabled and len(serialized) > 100:
            compressed = zlib.compress(serialized)
            # 添加压缩标记
            return b"COMPRESSED:" + compressed

        return serialized

    def _deserialize(self, data: bytes) -> Dict[str, Any]:
        """反序列化数据。

        Args:
            data: 序列化后的字节数据

        Returns:
            反序列化后的数据字典
        """
        # 检查是否有压缩标记
        if data.startswith(b"COMPRESSED:"):
            compressed_data = data[len(b"COMPRESSED:"):]
            serialized = zlib.decompress(compressed_data)
        else:
            serialized = data

        # 根据格式反序列化
        if self.serialization_format == "msgpack":
            return msgpack.unpackb(serialized, raw=False)
        else:
            return json.loads(serialized.decode("utf-8"))

    @observe(name="save_session", as_type="span")
    async def save_session(
        self,
        session_id: str,
        state: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """保存会话状态到Redis。

        Args:
            session_id: 会话ID
            state: 会话状态数据
            ttl: TTL时间（秒），None则使用默认值
        """
        try:
            key = f"session:{session_id}:state"
            serialized_data = self._serialize(state)
            ttl_seconds = ttl if ttl is not None else self.default_ttl

            await self.redis_client.setex(key, ttl_seconds, serialized_data)

            logger.debug(f"Session saved: {session_id} (ttl={ttl_seconds}s)")

        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
            raise

    @observe(name="load_session", as_type="span")
    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """从Redis加载会话状态。

        Args:
            session_id: 会话ID

        Returns:
            会话状态数据，如果不存在则返回None
        """
        try:
            key = f"session:{session_id}:state"
            data = await self.redis_client.get(key)

            if data is None:
                logger.debug(f"Session not found: {session_id}")
                return None

            state = self._deserialize(data)
            logger.debug(f"Session loaded: {session_id}")
            return state

        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            raise

    @observe(name="delete_session", as_type="span")
    async def delete_session(self, session_id: str) -> None:
        """删除会话状态。

        Args:
            session_id: 会话ID
        """
        try:
            key = f"session:{session_id}:state"
            await self.redis_client.delete(key)
            logger.debug(f"Session deleted: {session_id}")

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise

    @observe(name="get_active_sessions", as_type="span")
    async def get_active_sessions(self) -> List[str]:
        """获取所有活跃会话ID列表。

        Returns:
            会话ID列表
        """
        try:
            pattern = "session:*:state"
            keys = []

            async for key in self.redis_client.scan_iter(match=pattern):
                # 提取session_id
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                parts = key_str.split(":")
                if len(parts) >= 2:
                    session_id = parts[1]
                    keys.append(session_id)

            logger.debug(f"Found {len(keys)} active sessions")
            return keys

        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            raise

    @observe(name="get_session_ttl", as_type="span")
    async def get_session_ttl(self, session_id: str) -> int:
        """获取会话剩余TTL。

        Args:
            session_id: 会话ID

        Returns:
            剩余TTL（秒），-1表示永不过期，-2表示不存在
        """
        try:
            key = f"session:{session_id}:state"
            ttl = await self.redis_client.ttl(key)
            return ttl

        except Exception as e:
            logger.error(f"Failed to get TTL for session {session_id}: {e}")
            raise

    async def close(self):
        """关闭Redis连接。"""
        await self.redis_client.aclose()
        logger.info("SessionStore closed")

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口。"""
        await self.close()
