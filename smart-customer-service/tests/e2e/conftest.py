"""
E2E 测试配置和工具函数

提供:
- Playwright 浏览器配置
- 测试夹具 (fixtures)
- 辅助函数
- 测试数据生成
"""

import asyncio
import pytest
import os
from typing import Generator, Optional, Dict, Any
from datetime import datetime
import httpx

# Playwright 导入
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ==================== 配置 ====================

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("TEST_API_KEY", "test-service-key-12345")
TIMEOUT = int(os.getenv("TEST_TIMEOUT", "30000"))


# ==================== Fixtures ====================


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def http_client():
    """创建 HTTP 客户端"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
async def api_headers():
    """API 请求头"""
    return {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
    }


# Playwright Fixtures
@pytest.fixture(scope="session")
async def browser():
    """创建浏览器实例"""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright 未安装")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def context(browser: Browser):
    """创建浏览器上下文"""
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="E2E Test Bot/1.0",
    )
    yield context
    await context.close()


@pytest.fixture
async def page(context: BrowserContext) -> Page:
    """创建页面实例"""
    page = await context.new_page()
    page.set_default_timeout(TIMEOUT)
    yield page


# ==================== 辅助函数 ====================


async def check_service_health(client: httpx.AsyncClient) -> bool:
    """检查服务健康状态"""
    try:
        response = await client.get("/health")
        return response.status_code == 200
    except Exception:
        return False


async def create_test_session(client: httpx.AsyncClient, user_id: str) -> str:
    """创建测试会话"""
    response = await client.post(
        "/api/v1/conversations",
        json={"user_id": user_id},
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    )

    if response.status_code == 200:
        data = response.json()
        return data["data"]["session_id"]
    else:
        raise RuntimeError(f"创建会话失败：{response.status_code}")


async def send_message(
    client: httpx.AsyncClient,
    session_id: str,
    content: str,
    role: str = "user",
) -> Dict[str, Any]:
    """发送消息"""
    response = await client.post(
        f"/api/v1/conversations/{session_id}/messages",
        json={"role": role, "content": content},
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    )

    if response.status_code == 200:
        return response.json()
    else:
        return {"success": False, "message": f"发送消息失败：{response.status_code}"}


async def recognize_intent(
    client: httpx.AsyncClient,
    message: str,
    session_id: str,
    user_id: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """意图识别"""
    response = await client.post(
        "/api/v1/intent/recognize",
        json={
            "user_message": message,
            "session_id": session_id,
            "user_id": user_id,
            "context": context,
        },
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    )

    if response.status_code == 200:
        return response.json()
    else:
        return {"success": False, "message": f"意图识别失败：{response.status_code}"}


async def query_rag(
    client: httpx.AsyncClient,
    query: str,
    session_id: str,
    top_k: int = 3,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """RAG 查询"""
    response = await client.post(
        "/api/v1/rag/query",
        json={
            "query": query,
            "session_id": session_id,
            "top_k": top_k,
            "filters": filters,
        },
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    )

    if response.status_code == 200:
        return response.json()
    else:
        return {"success": False, "message": f"RAG 查询失败：{response.status_code}"}


async def execute_tool(
    client: httpx.AsyncClient,
    tool_name: str,
    parameters: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """工具调用"""
    response = await client.post(
        "/api/v1/tools/execute",
        json={
            "tool_name": tool_name,
            "parameters": parameters,
            "session_id": session_id,
        },
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    )

    if response.status_code == 200:
        return response.json()
    else:
        return {"success": False, "message": f"工具调用失败：{response.status_code}"}


async def check_escalation(
    client: httpx.AsyncClient,
    session_id: str,
    user_id: str,
    intent_confidence: float,
    user_message: str,
    is_vip: bool = False,
    failure_count: int = 0,
) -> Dict[str, Any]:
    """升级检查"""
    response = await client.post(
        "/api/v1/escalations/check",
        json={
            "session_id": session_id,
            "user_id": user_id,
            "intent_confidence": intent_confidence,
            "user_message": user_message,
            "is_vip": is_vip,
            "failure_count": failure_count,
        },
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    )

    if response.status_code == 200:
        return response.json()
    else:
        return {"success": False, "message": f"升级检查失败：{response.status_code}"}


async def cleanup_test_data(client: httpx.AsyncClient, session_id: str):
    """清理测试数据"""
    try:
        await client.delete(
            f"/api/v1/conversations/{session_id}",
            headers={"X-API-Key": API_KEY},
        )
    except Exception as e:
        print(f"清理测试数据失败：{e}")


# ==================== 测试数据生成 ====================


def generate_test_user_id() -> str:
    """生成测试用户 ID"""
    return f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def generate_test_session_id() -> str:
    """生成测试会话 ID"""
    return f"test_session_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def generate_test_agent_id() -> str:
    """生成测试客服 ID"""
    return f"test_agent_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


# ==================== 测试场景定义 ====================

TEST_SCENARIOS = {
    "user_consultation": {
        "name": "用户咨询流程",
        "steps": ["创建会话", "发送消息", "意图识别", "RAG 查询", "获得回复"],
    },
    "agent_workflow": {
        "name": "客服工作流程",
        "steps": ["客服登录", "接收会话", "查看历史", "发送回复", "会话转移"],
    },
    "escalation_flow": {
        "name": "升级流程",
        "steps": ["用户咨询", "触发升级", "客服接管", "解决问题"],
    },
}


# ==================== 环境检查 ====================


@pytest.fixture(scope="session", autouse=True)
async def check_environment():
    """环境检查"""
    import sys

    print("\n=== E2E 测试环境检查 ===")
    print(f"Python 版本：{sys.version}")
    print(f"测试基础 URL: {BASE_URL}")
    print(f"Playwright 可用：{PLAYWRIGHT_AVAILABLE}")

    # 检查后端服务
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        is_healthy = await check_service_health(client)
        print(f"后端服务健康：{is_healthy}")

        if not is_healthy:
            print("⚠️  警告：后端服务不健康，部分测试可能失败")


# ==================== 报告钩子 ====================


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """测试报告钩子"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        print(f"\n❌ 测试失败：{item.name}")
        if call.excinfo:
            print(f"错误信息：{call.excinfo.value}")


# ==================== 测试用例标记 ====================

# 导出标记供测试用例使用
pytest_plugins = [
    "pytest_asyncio",
]


# ==================== 性能测试工具 ====================


class PerformanceTimer:
    """性能计时器"""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        """开始计时"""
        self.start_time = datetime.now()

    def stop(self):
        """停止计时"""
        self.end_time = datetime.now()

    def duration_ms(self) -> float:
        """计算耗时（毫秒）"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() * 1000
        return 0.0


async def measure_api_latency(
    client: httpx.AsyncClient,
    endpoint: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    iterations: int = 10,
) -> Dict[str, float]:
    """测量 API 延迟"""
    latencies = []

    for _ in range(iterations):
        timer = PerformanceTimer()
        timer.start()

        if method == "GET":
            response = await client.get(endpoint)
        else:
            response = await client.post(endpoint, json=payload or {})

        timer.stop()

        if response.status_code == 200:
            latencies.append(timer.duration_ms())

    if latencies:
        return {
            "min": min(latencies),
            "max": max(latencies),
            "avg": sum(latencies) / len(latencies),
            "p95": sorted(latencies)[int(len(latencies) * 0.95)],
        }
    return {"min": 0, "max": 0, "avg": 0, "p95": 0}


# ==================== 断言工具 ====================


def assert_response_success(response: Dict[str, Any]):
    """断言响应成功"""
    assert response["success"] is True, f"响应失败：{response.get('message', '未知错误')}"


def assert_response_has_data(response: Dict[str, Any]):
    """断言响应包含数据"""
    assert "data" in response, "响应缺少 data 字段"


def assert_latency_below_threshold(latency: float, threshold: float = 500.0):
    """断言延迟低于阈值"""
    assert latency < threshold, f"延迟 {latency}ms 超过阈值 {threshold}ms"


# ==================== 导出所有工具 ====================

__all__ = [
    "BASE_URL",
    "API_KEY",
    "TIMEOUT",
    "http_client",
    "api_headers",
    "browser",
    "context",
    "page",
    "check_service_health",
    "create_test_session",
    "send_message",
    "recognize_intent",
    "query_rag",
    "execute_tool",
    "check_escalation",
    "cleanup_test_data",
    "generate_test_user_id",
    "generate_test_session_id",
    "generate_test_agent_id",
    "TEST_SCENARIOS",
    "PerformanceTimer",
    "measure_api_latency",
    "assert_response_success",
    "assert_response_has_data",
    "assert_latency_below_threshold",
]