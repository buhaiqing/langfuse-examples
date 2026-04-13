"""产品信息系统适配器"""

from typing import Dict, Any, Optional
import aioredis
from utils.api_client import APIClient
from core.config import settings


class ProductAPIClient(APIClient):
    """产品信息系统 API 客户端"""

    async def get_product_info(self, product_name: str) -> Dict[str, Any]:
        """获取产品信息"""
        return await self.get(f"/api/v1/products/{product_name}")

    async def get_pricing_info(self, product_id: str) -> Dict[str, Any]:
        """获取定价信息"""
        return await self.get(f"/api/v1/products/{product_id}/pricing")


class ProductService:
    """产品服务封装（带 Redis 缓存）"""

    def __init__(self, base_url: str = ""):
        self.client = ProductAPIClient(base_url)
        self.redis: Optional[aioredis.Redis] = None

    async def connect_redis(self):
        """连接 Redis"""
        self.redis = await aioredis.from_url(
            f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
        )

    async def get_product_info(self, product_name: str) -> Dict[str, Any]:
        """获取产品信息（带缓存）"""
        cache_key = f"product:{product_name}:info"

        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return eval(cached)

        info = await self.client.get_product_info(product_name)

        if self.redis:
            await self.redis.setex(cache_key, 86400, str(info))

        return info

    async def invalidate_cache(self, product_name: str):
        """使缓存失效"""
        if self.redis:
            await self.redis.delete(f"product:{product_name}:info")


product_service = ProductService()
