"""
API客户端模块 - 提供统一的HTTP客户端封装。

包含重试机制、熔断器、超时控制等功能，
确保API调用的稳定性和可观测性。
"""

import logging
import time
from typing import Any, Dict, Optional

import httpx
import pybreaker
from langfuse import observe
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class CircuitBreakerError(Exception):
    """熔断器异常。"""

    pass


class APIClient:
    """统一的HTTP API客户端。

    提供GET、POST、PUT、DELETE等方法，内置重试、熔断、超时控制。

    Attributes:
        base_url: API基础URL
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
        headers: 默认请求头
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None,
    ):
        """初始化API客户端。

        Args:
            base_url: API基础URL
            api_key: API密钥（可选）
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            headers: 默认请求头
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        # 构建默认请求头
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            self.headers.update(headers)
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

        # 初始化熔断器：失败5次后熔断，30秒后恢复
        self.circuit_breaker = pybreaker.CircuitBreaker(
            fail_max=5,
            reset_timeout=30,
        )

        # 创建HTTP客户端
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers=self.headers,
        )

        logger.info(f"APIClient initialized: base_url={self.base_url}")

    @observe(name="api_call", as_type="span")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, ConnectionError)),
        reraise=True,
    )
    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行HTTP请求（内部方法）。

        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            url: 完整URL或相对路径
            params: URL查询参数
            json_data: JSON请求体

        Returns:
            响应数据字典

        Raises:
            httpx.HTTPStatusError: HTTP状态码错误
            httpx.RequestError: 请求错误
            CircuitBreakerError: 熔断器触发
        """
        # 检查熔断器状态
        if self.circuit_breaker.current_state == "open":
            raise CircuitBreakerError("熔断器已打开，请稍后重试")

        full_url = url if url.startswith("http") else f"{self.base_url}/{url.lstrip('/')}"

        logger.debug(f"Making {method} request to {full_url}")

        try:
            response = await self.client.request(
                method=method.upper(),
                url=full_url,
                params=params,
                json=json_data,
            )

            # 记录熔断器成功
            self.circuit_breaker.call_succeed()

            # 检查HTTP状态码
            response.raise_for_status()

            # 尝试解析JSON
            try:
                return response.json()
            except Exception:
                return {"text": response.text}

        except httpx.HTTPStatusError as e:
            # 记录熔断器失败
            self.circuit_breaker.call_fail()
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise

        except httpx.RequestError as e:
            # 记录熔断器失败
            self.circuit_breaker.call_fail()
            logger.error(f"Request error: {e}")
            raise

    @observe(name="api_get", as_type="span")
    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行GET请求。

        Args:
            url: API路径或完整URL
            params: URL查询参数

        Returns:
            响应数据字典
        """
        return await self._make_request("GET", url, params=params)

    @observe(name="api_post", as_type="span")
    async def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行POST请求。

        Args:
            url: API路径或完整URL
            data: 请求体数据

        Returns:
            响应数据字典
        """
        return await self._make_request("POST", url, json_data=data)

    @observe(name="api_put", as_type="span")
    async def put(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行PUT请求。

        Args:
            url: API路径或完整URL
            data: 请求体数据

        Returns:
            响应数据字典
        """
        return await self._make_request("PUT", url, json_data=data)

    @observe(name="api_delete", as_type="span")
    async def delete(self, url: str) -> Dict[str, Any]:
        """执行DELETE请求。

        Args:
            url: API路径或完整URL

        Returns:
            响应数据字典
        """
        return await self._make_request("DELETE", url)

    @observe(name="health_check", as_type="span")
    async def health_check(self) -> bool:
        """健康检查。

        Returns:
            True if healthy, False otherwise
        """
        try:
            # 尝试访问根路径或health端点
            await self.get("/health")
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    async def close(self):
        """关闭HTTP客户端连接。"""
        await self.client.aclose()
        logger.info("APIClient closed")

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口。"""
        await self.close()
