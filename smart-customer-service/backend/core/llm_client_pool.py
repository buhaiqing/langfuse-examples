"""
LLM 客户端缓存管理模块

提供:
- LLM 客户端单例模式（避免重复创建）
- 连接池管理（复用 LLM 客户端）
- 速率限制（控制 LLM API 调用频率）
- 响应缓存（缓存相似请求的响应）
- 模型实例预热
"""

import asyncio
import hashlib
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from threading import Lock
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from core.config import settings

logger = logging.getLogger(__name__)


# ==================== LLM 客户端配置 ====================
@dataclass
class LLMClientConfig:
    """LLM 客户端配置"""

    model_name: str
    temperature: float = 0.0
    max_tokens: int | None = None
    request_timeout: float = 60.0
    max_retries: int = 3

    # 速率限制
    requests_per_minute: int = 60
    tokens_per_minute: int = 90000

    # 缓存
    enable_cache: bool = True
    cache_ttl_seconds: int = 300
    cache_max_size: int = 100


@dataclass
class EmbeddingClientConfig:
    """Embedding 客户端配置"""

    model_name: str
    chunk_size: int = 1000

    # 速率限制
    requests_per_minute: int = 60


# ==================== 速率限制器 ====================
class RateLimiter:
    """
    速率限制器

    使用滑动窗口算法限制 API 调用频率
    """

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self._requests: list[float] = []
        self._lock = Lock()

    def acquire(self, timeout: float = 10.0) -> bool:
        """
        获取调用许可

        Args:
            timeout: 最大等待时间（秒）

        Returns:
            是否成功获取许可
        """
        current_time = time.time()
        window_start = current_time - 60.0  # 1分钟窗口

        with self._lock:
            # 清理过期请求
            self._requests = [t for t in self._requests if t > window_start]

            # 检查是否超过限制
            if len(self._requests) >= self.requests_per_minute:
                # 计算等待时间
                oldest_request = min(self._requests)
                wait_time = oldest_request + 60.0 - current_time

                if wait_time > timeout:
                    return False

                # 等待
                time.sleep(wait_time + 0.1)

                # 再次清理
                current_time = time.time()
                window_start = current_time - 60.0
                self._requests = [t for t in self._requests if t > window_start]

            # 记录本次请求
            self._requests.append(current_time)
            return True

    def get_current_rate(self) -> int:
        """获取当前窗口内的请求数"""
        current_time = time.time()
        window_start = current_time - 60.0

        with self._lock:
            return len([t for t in self._requests if t > window_start])


# ==================== LLM 响应缓存 ====================
class LLMResponseCache:
    """
    LLM 响应缓存

    缓存相似请求的响应，减少 API 调用
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def _generate_key(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> str:
        """生成缓存键"""
        # 使用消息内容、模型名和温度生成唯一键
        content = json.dumps(
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
            },
            sort_keys=True,
        )

        return hashlib.sha256(content.encode()).hexdigest()

    def get(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> str | None:
        """获取缓存的响应"""
        key = self._generate_key(messages, model, temperature)

        with self._lock:
            entry = self._cache.get(key)

            if not entry:
                return None

            # 检查是否过期
            if time.time() - entry["timestamp"] > self.ttl_seconds:
                del self._cache[key]
                return None

            return entry["response"]

    def set(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        response: str,
    ):
        """缓存响应"""
        key = self._generate_key(messages, model, temperature)

        with self._lock:
            # 检查容量
            if len(self._cache) >= self.max_size:
                # 删除最旧的条目
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
                del self._cache[oldest_key]

            self._cache[key] = {
                "response": response,
                "timestamp": time.time(),
            }

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            current_time = time.time()

            # 清理过期条目
            expired_keys = [
                k
                for k, v in self._cache.items()
                if current_time - v["timestamp"] > self.ttl_seconds
            ]
            for k in expired_keys:
                del self._cache[k]

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
            }


# ==================== LLM 客户端池 ====================
class LLMClientPool:
    """
    LLM 客户端连接池

    管理 LLM 客户端实例的创建、复用和生命周期
    """

    def __init__(self):
        self._chat_clients: dict[str, ChatOpenAI] = {}
        self._embedding_clients: dict[str, OpenAIEmbeddings] = {}
        self._rate_limiters: dict[str, RateLimiter] = {}
        self._cache: LLMResponseCache | None = None
        self._lock = Lock()

        # 请求队列（用于排队处理）
        self._request_queue: asyncio.Queue = None
        self._queue_processor_task: asyncio.Task | None = None

    def get_chat_client(
        self,
        model: str | None = None,
        temperature: float = 0.0,
        config: LLMClientConfig | None = None,
    ) -> ChatOpenAI:
        """
        获取 ChatOpenAI 客户端

        使用单例模式，避免重复创建

        Args:
            model: 模型名称（默认使用配置中的模型）
            temperature: 温度参数
            config: 客户端配置

        Returns:
            ChatOpenAI 客户端实例
        """
        model = model or settings.openai_model
        cache_key = f"chat:{model}:{temperature}"

        with self._lock:
            if cache_key not in self._chat_clients:
                config = config or LLMClientConfig(model_name=model, temperature=temperature)

                client = ChatOpenAI(
                    model=model,
                    temperature=temperature,
                    request_timeout=config.request_timeout,
                    max_retries=config.max_retries,
                )

                self._chat_clients[cache_key] = client

                # 创建速率限制器
                if cache_key not in self._rate_limiters:
                    self._rate_limiters[cache_key] = RateLimiter(
                        requests_per_minute=config.requests_per_minute
                    )

                logger.debug(f"创建 LLM 客户端: {cache_key}")

            return self._chat_clients[cache_key]

    def get_embedding_client(
        self,
        model: str | None = None,
        config: EmbeddingClientConfig | None = None,
    ) -> OpenAIEmbeddings:
        """
        获取 OpenAIEmbeddings 客户端

        Args:
            model: 模型名称
            config: 客户端配置

        Returns:
            OpenAIEmbeddings 客户端实例
        """
        model = model or settings.openai_embedding_model
        cache_key = f"embedding:{model}"

        with self._lock:
            if cache_key not in self._embedding_clients:
                config = config or EmbeddingClientConfig(model_name=model)

                client = OpenAIEmbeddings(
                    model=model,
                    chunk_size=config.chunk_size,
                )

                self._embedding_clients[cache_key] = client

                # 创建速率限制器
                if cache_key not in self._rate_limiters:
                    self._rate_limiters[cache_key] = RateLimiter(
                        requests_per_minute=config.requests_per_minute
                    )

                logger.debug(f"创建 Embedding 客户端: {cache_key}")

            return self._embedding_clients[cache_key]

    def get_rate_limiter(self, client_key: str) -> RateLimiter:
        """获取速率限制器"""
        return self._rate_limiters.get(client_key)

    def initialize_cache(
        self,
        max_size: int = 100,
        ttl_seconds: int = 300,
    ):
        """初始化响应缓存"""
        with self._lock:
            if self._cache is None:
                self._cache = LLMResponseCache(
                    max_size=max_size,
                    ttl_seconds=ttl_seconds,
                )
                logger.info(f"LLM 响应缓存初始化 (max_size={max_size}, ttl={ttl_seconds}s)")

    def get_cache(self) -> LLMResponseCache | None:
        """获取响应缓存"""
        return self._cache

    def warm_up(self, models: list[str] | None = None):
        """
        预热客户端

        提前创建常用的客户端实例

        Args:
            models: 需要预热的模型列表
        """
        models = models or [settings.openai_model, settings.openai_embedding_model]

        for model in models:
            if model.startswith("gpt"):
                self.get_chat_client(model)
            elif model.startswith("text-embedding"):
                self.get_embedding_client(model)

        logger.info(f"LLM 客户端预热完成: {models}")

    def get_stats(self) -> dict[str, Any]:
        """获取连接池统计"""
        with self._lock:
            stats = {
                "chat_clients": len(self._chat_clients),
                "embedding_clients": len(self._embedding_clients),
                "rate_limiters": len(self._rate_limiters),
                "cache_stats": self._cache.get_stats() if self._cache else None,
            }

            # 速率限制器统计
            rate_stats = {}
            for key, limiter in self._rate_limiters.items():
                rate_stats[key] = {
                    "current_rate": limiter.get_current_rate(),
                    "max_rate": limiter.requests_per_minute,
                }
            stats["rate_stats"] = rate_stats

            return stats

    def clear_cache(self):
        """清空响应缓存"""
        if self._cache:
            self._cache.clear()

    def reset_rate_limiters(self):
        """重置速率限制器"""
        with self._lock:
            self._rate_limiters.clear()


# ==================== 全局连接池 ====================
_llm_pool: LLMClientPool | None = None


def get_llm_pool() -> LLMClientPool:
    """获取 LLM 连接池"""
    global _llm_pool

    if _llm_pool is None:
        _llm_pool = LLMClientPool()
        _llm_pool.initialize_cache()
        _llm_pool.warm_up()

    return _llm_pool


def get_chat_client(
    model: str | None = None,
    temperature: float = 0.0,
) -> ChatOpenAI:
    """获取 ChatOpenAI 客户端"""
    return get_llm_pool().get_chat_client(model, temperature)


def get_embedding_client(model: str | None = None) -> OpenAIEmbeddings:
    """获取 OpenAIEmbeddings 客户端"""
    return get_llm_pool().get_embedding_client(model)


# ==================== 异步调用包装 ====================
async def call_llm_with_rate_limit(
    client: ChatOpenAI,
    messages: list[dict[str, str]],
    use_cache: bool = True,
) -> str:
    """
    带速率限制和缓存的 LLM 调用

    Args:
        client: LLM 客户端
        messages: 消息列表
        use_cache: 是否使用缓存

    Returns:
        LLM 响应
    """
    pool = get_llm_pool()
    cache = pool.get_cache()

    model = client.model_name
    temperature = client.temperature

    # 1. 检查缓存
    if use_cache and cache:
        cached_response = cache.get(messages, model, temperature)
        if cached_response:
            logger.debug(f"使用缓存响应 (model={model})")
            return cached_response

    # 2. 速率限制
    client_key = f"chat:{model}:{temperature}"
    rate_limiter = pool.get_rate_limiter(client_key)

    if rate_limiter:
        # 异步等待获取许可
        await asyncio.get_event_loop().run_in_executor(None, rate_limiter.acquire)

    # 3. 调用 LLM
    try:
        # 构建提示词
        prompt = ChatPromptTemplate.from_messages([(m["role"], m["content"]) for m in messages])
        chain = prompt | client

        response = await chain.ainvoke({})
        response_text = response.content if hasattr(response, "content") else str(response)

        # 4. 缓存响应
        if use_cache and cache:
            cache.set(messages, model, temperature, response_text)

        return response_text

    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        raise


async def call_embedding_with_rate_limit(
    client: OpenAIEmbeddings,
    texts: list[str],
) -> list[list[float]]:
    """
    带速率限制的 Embedding 调用

    Args:
        client: Embedding 客户端
        texts: 文本列表

    Returns:
        Embedding 向量列表
    """
    pool = get_llm_pool()

    model = client.model
    client_key = f"embedding:{model}"
    rate_limiter = pool.get_rate_limiter(client_key)

    if rate_limiter:
        await asyncio.get_event_loop().run_in_executor(None, rate_limiter.acquire)

    try:
        embeddings = await client.aembed_documents(texts)
        return embeddings

    except Exception as e:
        logger.error(f"Embedding 调用失败: {e}")
        raise


# ==================== 装饰器 ====================
def with_llm_rate_limit(model: str | None = None):
    """
    LLM 速率限制装饰器

    使用示例:
    ```python
    @with_llm_rate_limit(model="gpt-4")
    async def analyze_intent(message: str):
        client = get_chat_client()
        ...
    ```
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            pool = get_llm_pool()
            client = pool.get_chat_client(model)

            client_key = f"chat:{model or settings.openai_model}:{client.temperature}"
            rate_limiter = pool.get_rate_limiter(client_key)

            if rate_limiter:
                await asyncio.get_event_loop().run_in_executor(None, rate_limiter.acquire)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ==================== 导出 ====================
__all__ = [
    "LLMClientConfig",
    "EmbeddingClientConfig",
    "RateLimiter",
    "LLMResponseCache",
    "LLMClientPool",
    "get_llm_pool",
    "get_chat_client",
    "get_embedding_client",
    "call_llm_with_rate_limit",
    "call_embedding_with_rate_limit",
    "with_llm_rate_limit",
]
