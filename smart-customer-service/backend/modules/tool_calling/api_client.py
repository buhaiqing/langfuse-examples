"""
Enhanced API client with retry, circuit breaker, and logging
Provides robust HTTP communication for external service integration
"""

import asyncio
import json
import time
from typing import Any, Dict, Optional

import httpx
from core.logging_config import LogCategory, get_logger
from core.tracing import create_span, score_trace
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from pybreaker import CircuitBreaker

logger = get_logger(LogCategory.TOOL)


class APIClientError(Exception):
    """Base exception for API client errors"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class APITimeoutError(APIClientError):
    """Raised when API request times out"""

    pass


class APIRateLimitError(APIClientError):
    """Raised when API rate limit is exceeded"""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class CircuitBreakerOpenError(APIClientError):
    """Raised when circuit breaker is open"""

    pass


class ResilientAPIClient:
    """
    Robust HTTP client with retry logic, circuit breaker, and comprehensive logging.

    Features:
    - Exponential backoff retry with jitter
    - Circuit breaker pattern for fault tolerance
    - Request/response logging with sensitive data masking
    - Timeout control
    - Full Langfuse tracing
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        circuit_breaker_failure_threshold: int = 5,
        circuit_breaker_recovery_timeout: int = 30,
        rate_limit_per_second: Optional[float] = None,
    ):
        """
        Initialize resilient API client.

        Args:
            base_url: Base URL for API endpoints
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            circuit_breaker_failure_threshold: Number of failures before opening circuit
            circuit_breaker_recovery_timeout: Seconds before attempting recovery
            rate_limit_per_second: Optional rate limit (requests per second)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_per_second = rate_limit_per_second

        # Initialize HTTP client
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers=self._build_headers(),
        )

        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            fail_max=circuit_breaker_failure_threshold,
            reset_timeout=circuit_breaker_recovery_timeout,
        )

        # Rate limiting
        self._last_request_time: Optional[float] = None
        self._request_count = 0

        logger.info(
            f"ResilientAPIClient initialized: base_url={base_url}, "
            f"timeout={timeout}s, max_retries={max_retries}"
        )

    def _build_headers(self) -> Dict[str, str]:
        """Build default headers including authentication"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "SmartCustomerService/1.0",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform GET request with retry and circuit breaker.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Response JSON data
        """
        return await self._request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform POST request with retry and circuit breaker.

        Args:
            endpoint: API endpoint path
            data: Form data
            json_data: JSON data

        Returns:
            Response JSON data
        """
        return await self._request(
            "POST", endpoint, data=data, json_data=json_data
        )

    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform PUT request with retry and circuit breaker.

        Args:
            endpoint: API endpoint path
            data: Form data
            json_data: JSON data

        Returns:
            Response JSON data
        """
        return await self._request(
            "PUT", endpoint, data=data, json_data=json_data
        )

    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """
        Perform DELETE request with retry and circuit breaker.

        Args:
            endpoint: API endpoint path

        Returns:
            Response JSON data
        """
        return await self._request("DELETE", endpoint)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Internal request method with retry, circuit breaker, and logging.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Form data
            json_data: JSON data

        Returns:
            Response JSON data

        Raises:
            APIClientError: On request failure
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        with create_span("api_request", input_data={
            "method": method,
            "url": self._mask_sensitive_url(url),
            "has_params": params is not None,
        }) as main_span:
            start_time = time.time()
            attempt_count = 0

            try:
                # Check circuit breaker
                if self.circuit_breaker.current_state == "open":
                    raise CircuitBreakerOpenError(
                        "Circuit breaker is open. Service unavailable."
                    )

                # Apply rate limiting
                await self._apply_rate_limit()

                # Execute request with retry
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(self.max_retries),
                    wait=wait_exponential(multiplier=1, min=1, max=10),
                    retry=retry_if_exception_type(
                        (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)
                    ),
                    reraise=True,
                ):
                    attempt_count += 1

                    with create_span("http_request_attempt") as attempt_span:
                        attempt_span.add_event(
                            "retry_attempt",
                            output_data={"attempt": attempt_count},
                        )

                        # Prepare request
                        prep_span = create_span("request_preparation")
                        kwargs = self._prepare_request_kwargs(
                            params, data, json_data
                        )
                        prep_span.end()

                        # Execute HTTP request
                        response = await self._execute_request(
                            method, url, **kwargs
                        )

                        # Parse response
                        parse_span = create_span("response_parsing")
                        result = await self._parse_response(response)
                        parse_span.end(
                            output_data={"status_code": response.status_code}
                        )

                        attempt_span.end(
                            output_data={
                                "success": True,
                                "status_code": response.status_code,
                            }
                        )

                        # Record success in circuit breaker
                        self.circuit_breaker.call_succeed()

                        # Calculate latency
                        latency_ms = (time.time() - start_time) * 1000
                        score_trace("api_latency_ms", latency_ms)
                        score_trace("api_success_rate", 1.0)

                        main_span.end(
                            output_data={
                                "status": "success",
                                "attempts": attempt_count,
                                "latency_ms": latency_ms,
                            }
                        )

                        return result

            except CircuitBreakerOpenError:
                logger.warning(f"Circuit breaker open for {url}")
                score_trace("api_success_rate", 0.0)
                raise

            except httpx.TimeoutException as e:
                logger.error(f"Request timeout after {attempt_count} attempts: {e}")
                self.circuit_breaker.call_fail()
                score_trace("api_success_rate", 0.0)
                raise APITimeoutError(
                    f"Request timed out after {attempt_count} attempts: {str(e)}"
                )

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {e}")
                self.circuit_breaker.call_fail()

                if e.response.status_code == 429:
                    retry_after = e.response.headers.get("Retry-After")
                    raise APIRateLimitError(
                        f"Rate limit exceeded: {str(e)}",
                        retry_after=int(retry_after) if retry_after else None,
                    )

                raise APIClientError(
                    f"HTTP {e.response.status_code}: {str(e)}",
                    status_code=e.response.status_code,
                )

            except Exception as e:
                logger.error(f"Request failed after {attempt_count} attempts: {e}")
                self.circuit_breaker.call_fail()
                score_trace("api_success_rate", 0.0)
                raise APIClientError(f"Request failed: {str(e)}")

    async def _execute_request(
        self, method: str, url: str, **kwargs
    ) -> httpx.Response:
        """
        Execute HTTP request with logging.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request arguments

        Returns:
            HTTP response
        """
        # Log request (masked)
        logger.debug(
            f"Sending {method} request to {self._mask_sensitive_url(url)}"
        )

        # Execute request
        response = await self._client.request(method, url, **kwargs)

        # Log response status
        logger.debug(
            f"Received response: status={response.status_code}, "
            f"url={self._mask_sensitive_url(url)}"
        )

        # Raise for bad status codes
        response.raise_for_status()

        return response

    async def _parse_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Parse HTTP response to JSON.

        Args:
            response: HTTP response

        Returns:
            Parsed JSON data
        """
        try:
            return response.json()
        except json.JSONDecodeError:
            logger.warning(
                f"Response is not valid JSON: {response.text[:200]}"
            )
            return {"raw_response": response.text}

    def _prepare_request_kwargs(
        self,
        params: Optional[Dict],
        data: Optional[Dict],
        json_data: Optional[Dict],
    ) -> Dict[str, Any]:
        """
        Prepare keyword arguments for HTTP request.

        Args:
            params: Query parameters
            data: Form data
            json_data: JSON data

        Returns:
            Request kwargs
        """
        kwargs = {}

        if params:
            kwargs["params"] = params

        if data:
            kwargs["data"] = data

        if json_data:
            kwargs["json"] = json_data

        return kwargs

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting if configured"""
        if not self.rate_limit_per_second:
            return

        now = time.time()

        if self._last_request_time:
            elapsed = now - self._last_request_time
            min_interval = 1.0 / self.rate_limit_per_second

            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

        self._last_request_time = time.time()
        self._request_count += 1

    @staticmethod
    def _mask_sensitive_url(url: str) -> str:
        """
        Mask sensitive information in URL (tokens, keys).

        Args:
            url: Original URL

        Returns:
            Masked URL
        """
        import re

        # Mask common sensitive patterns
        masked = re.sub(r"(token|key|secret|password)=([^&]+)", r"\1=***", url)
        return masked

    async def health_check(self) -> bool:
        """
        Perform health check on the API service.

        Returns:
            True if service is healthy
        """
        try:
            # Try a simple GET request to root or health endpoint
            await self.get("/health", params={})
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the HTTP client"""
        await self._client.aclose()
        logger.info("API client closed")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
