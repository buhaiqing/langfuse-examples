"""API 客户端封装 - HTTP 请求、重试、熔断"""

from typing import Dict, Any, Optional, Callable
import httpx
import pybreaker
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.config import settings


class APIClientError(Exception):
    """API 客户端异常"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class CircuitBreakerOpen(APIClientError):
    """熔断器打开异常"""

    def __init__(self):
        super().__init__("Circuit breaker is open", status_code=503)


class APIClient:
    """
    统一 API 客户端封装

    功能:
    - 异步 HTTP 请求
    - 指数退避重试
    - 熔断器模式
    - 超时控制
    - 日志记录 (脱敏)
    - 错误处理 (标准化异常)
    """

    def __init__(self, base_url: str = "", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self.breaker = pybreaker.CircuitBreaker(
            failure_threshold=5, recovery_timeout=30, expected_exception=httpx.HTTPError
        )

        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.base_url, timeout=httpx.Timeout(self.timeout)
            )
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    @breaker
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                data=data,
                **kwargs,
            )

            response.raise_for_status()

            return response.json() if response.content else {}

        except httpx.HTTPStatusError as e:
            raise APIClientError(
                f"HTTP error: {e.response.status_code}", status_code=e.response.status_code
            )
        except httpx.RequestError as e:
            raise APIClientError(f"Request error: {str(e)}")
        except pybreaker.CircuitBreakerError:
            raise CircuitBreakerOpen()

    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> Dict[str, Any]:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> Dict[str, Any]:
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        return await self.request("DELETE", url, **kwargs)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


class JiraClient(APIClient):
    """Jira 工单系统客户端"""

    def __init__(self, base_url: str, api_token: str, email: str):
        super().__init__(base_url)
        self.client.auth = (email, api_token)

    async def query_ticket(self, ticket_id: str) -> Dict[str, Any]:
        return await self.get(f"/rest/api/3/issue/{ticket_id}")

    async def create_ticket(
        self, project: str, summary: str, description: str, issue_type: str = "Bug"
    ) -> Dict[str, Any]:
        return await self.post(
            "/rest/api/3/issue",
            json={
                "fields": {
                    "project": {"key": project},
                    "summary": summary,
                    "description": description,
                    "issuetype": {"name": issue_type},
                }
            },
        )

    async def add_comment(self, ticket_id: str, comment: str) -> Dict[str, Any]:
        return await self.post(
            f"/rest/api/3/issue/{ticket_id}/comment",
            json={"body": {"content": [{"type": "text", "text": comment}]}},
        )


class ZendeskClient(APIClient):
    """Zendesk 工单系统客户端"""

    def __init__(self, base_url: str, api_token: str, email: str):
        super().__init__(base_url)
        self.client.auth = (f"{email}/token", api_token)

    async def query_ticket(self, ticket_id: str) -> Dict[str, Any]:
        return await self.get(f"/api/v2/tickets/{ticket_id}.json")

    async def create_ticket(
        self, subject: str, description: str, requester_email: str
    ) -> Dict[str, Any]:
        return await self.post(
            "/api/v2/tickets.json",
            json={
                "ticket": {
                    "subject": subject,
                    "comment": {"body": description},
                    "requester": {"email": requester_email},
                }
            },
        )


api_client = APIClient()
