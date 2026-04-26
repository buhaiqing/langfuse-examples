"""
LLM 客户端池测试

测试:
- 客户端单例模式
- 速率限制
- 响应缓存
"""

import time

from core.llm_client_pool import (
    LLMClientPool,
    LLMResponseCache,
    RateLimiter,
    get_chat_client,
    get_embedding_client,
    get_llm_pool,
)


class TestRateLimiter:
    """速率限制器测试"""

    def test_initial_state(self):
        """测试初始状态"""
        limiter = RateLimiter(requests_per_minute=60)

        assert limiter.requests_per_minute == 60
        assert len(limiter._requests) == 0

    def test_acquire_within_limit(self):
        """测试在限制内获取许可"""
        limiter = RateLimiter(requests_per_minute=10)

        # 连续获取多次许可
        for _i in range(5):
            result = limiter.acquire(timeout=0.1)
            assert result is True

    def test_acquire_exceed_limit(self):
        """测试超过限制"""
        limiter = RateLimiter(requests_per_minute=5)

        # 先消耗 5 次许可
        for _i in range(5):
            limiter.acquire(timeout=0.1)

        # 第 6 次应该失败（timeout=0 表示不等待）
        result = limiter.acquire(timeout=0)
        assert result is False

    def test_get_current_rate(self):
        """测试获取当前速率"""
        limiter = RateLimiter(requests_per_minute=10)

        # 发送几次请求
        for _i in range(3):
            limiter.acquire(timeout=0.1)

        current_rate = limiter.get_current_rate()
        assert current_rate == 3


class TestLLMResponseCache:
    """LLM 响应缓存测试"""

    def test_initial_state(self):
        """测试初始状态"""
        cache = LLMResponseCache(max_size=100, ttl_seconds=300)

        assert cache.max_size == 100
        assert cache.ttl_seconds == 300
        assert len(cache._cache) == 0

    def test_set_and_get(self):
        """测试设置和获取"""
        cache = LLMResponseCache(max_size=100, ttl_seconds=300)

        messages = [{"role": "user", "content": "你好"}]
        model = "gpt-4"
        temperature = 0.0
        response = "你好！有什么可以帮助你的吗？"

        cache.set(messages, model, temperature, response)

        cached_response = cache.get(messages, model, temperature)
        assert cached_response == response

    def test_cache_miss(self):
        """测试缓存未命中"""
        cache = LLMResponseCache()

        messages = [{"role": "user", "content": "测试"}]
        result = cache.get(messages, "gpt-4", 0.0)

        assert result is None

    def test_different_keys(self):
        """测试不同键"""
        cache = LLMResponseCache()

        messages1 = [{"role": "user", "content": "问题1"}]
        messages2 = [{"role": "user", "content": "问题2"}]

        cache.set(messages1, "gpt-4", 0.0, "答案1")

        result = cache.get(messages2, "gpt-4", 0.0)
        assert result is None

    def test_cache_eviction(self):
        """测试缓存淘汰"""
        cache = LLMResponseCache(max_size=3)

        # 添加 4 个条目（超过 max_size）
        for i in range(4):
            messages = [{"role": "user", "content": f"问题{i}"}]
            cache.set(messages, "gpt-4", 0.0, f"答案{i}")

        # 应该淘汰了最旧的条目
        stats = cache.get_stats()
        assert stats["size"] <= 3

    def test_cache_ttl(self):
        """测试缓存过期"""
        cache = LLMResponseCache(max_size=100, ttl_seconds=1)

        messages = [{"role": "user", "content": "测试"}]
        cache.set(messages, "gpt-4", 0.0, "答案")

        # 立即获取应该有值
        assert cache.get(messages, "gpt-4", 0.0) == "答案"

        # 等待过期
        time.sleep(1.5)

        # 过期后应该返回 None
        assert cache.get(messages, "gpt-4", 0.0) is None

    def test_clear_cache(self):
        """测试清空缓存"""
        cache = LLMResponseCache()

        messages = [{"role": "user", "content": "测试"}]
        cache.set(messages, "gpt-4", 0.0, "答案")

        cache.clear()

        assert cache.get(messages, "gpt-4", 0.0) is None

    def test_get_stats(self):
        """测试获取统计"""
        cache = LLMResponseCache()

        messages = [{"role": "user", "content": "测试"}]
        cache.set(messages, "gpt-4", 0.0, "答案")

        stats = cache.get_stats()

        assert "size" in stats
        assert "max_size" in stats
        assert "ttl_seconds" in stats


class TestLLMClientPool:
    """LLM 客户端池测试"""

    def test_initial_state(self):
        """测试初始状态"""
        pool = LLMClientPool()

        assert len(pool._chat_clients) == 0
        assert len(pool._embedding_clients) == 0
        assert pool._cache is None

    def test_get_chat_client_singleton(self):
        """测试 Chat 客户端单例"""
        pool = LLMClientPool()

        client1 = pool.get_chat_client(model="gpt-4", temperature=0.0)
        client2 = pool.get_chat_client(model="gpt-4", temperature=0.0)

        # 应返回同一个实例
        assert client1 is client2

    def test_get_chat_client_different_params(self):
        """测试不同参数返回不同客户端"""
        pool = LLMClientPool()

        client1 = pool.get_chat_client(model="gpt-4", temperature=0.0)
        client2 = pool.get_chat_client(model="gpt-4", temperature=0.5)

        # 不同参数应返回不同实例
        assert client1 is not client2

    def test_get_embedding_client_singleton(self):
        """测试 Embedding 客户端单例"""
        pool = LLMClientPool()

        client1 = pool.get_embedding_client(model="text-embedding-3-small")
        client2 = pool.get_embedding_client(model="text-embedding-3-small")

        assert client1 is client2

    def test_initialize_cache(self):
        """测试初始化缓存"""
        pool = LLMClientPool()

        pool.initialize_cache(max_size=50, ttl_seconds=60)

        assert pool._cache is not None
        assert pool._cache.max_size == 50

    def test_get_rate_limiter(self):
        """测试获取速率限制器"""
        pool = LLMClientPool()

        # 获取客户端时自动创建速率限制器
        pool.get_chat_client(model="gpt-4")

        rate_limiter = pool.get_rate_limiter("chat:gpt-4:0.0")

        assert rate_limiter is not None
        assert rate_limiter.requests_per_minute == 60

    def test_get_stats(self):
        """测试获取统计"""
        pool = LLMClientPool()

        pool.get_chat_client(model="gpt-4")
        pool.get_embedding_client()

        stats = pool.get_stats()

        assert "chat_clients" in stats
        assert "embedding_clients" in stats
        assert "rate_limiters" in stats

    def test_warm_up(self):
        """测试预热"""
        pool = LLMClientPool()

        pool.warm_up(models=["gpt-4"])

        stats = pool.get_stats()
        assert stats["chat_clients"] >= 1


class TestGlobalFunctions:
    """全局函数测试"""

    def test_get_llm_pool(self):
        """测试获取连接池"""
        pool1 = get_llm_pool()
        pool2 = get_llm_pool()

        # 应返回同一个实例
        assert pool1 is pool2

    def test_get_chat_client(self):
        """测试获取 Chat 客户端"""
        client = get_chat_client()

        assert client is not None

    def test_get_embedding_client(self):
        """测试获取 Embedding 客户端"""
        client = get_embedding_client()

        assert client is not None
