"""Langfuse 客户端测试

测试:
- 客户端初始化逻辑（测试环境自动 Mock）
- 重复代码块修复验证
- trace_id 上下文管理
- DummySpan 降级行为
- 评分常量定义

注意：conftest.py mock 了 core.langfuse_client 模块，
本测试使用 importlib 直接加载源文件进行测试。
"""

import importlib.util
import inspect
import os
from unittest.mock import patch


def _load_module_from_file(module_name, file_path):
    """直接从文件加载模块，绕过 sys.modules 中的 mock"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_backend_root = os.path.join(os.path.dirname(__file__), "..", "..")
_langfuse_client_path = os.path.join(_backend_root, "core", "langfuse_client.py")


class TestLangfuseClientInit:
    """客户端初始化测试"""

    def test_testing_environment_detection(self):
        """测试环境检测"""
        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}):
            mod = _load_module_from_file("langfuse_client_test", _langfuse_client_path)
            assert mod.LangfuseClient._is_testing_environment() is True

    def test_production_environment_detection(self):
        """生产环境检测"""
        original = os.environ.get("PYTEST_CURRENT_TEST")
        os.environ.pop("PYTEST_CURRENT_TEST", None)
        try:
            with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
                mod = _load_module_from_file("langfuse_client_test2", _langfuse_client_path)
                assert mod.LangfuseClient._is_testing_environment() is False
        finally:
            if original:
                os.environ["PYTEST_CURRENT_TEST"] = original

    def test_can_initialize_real_client_checks_config(self):
        """检查是否具备初始化真实客户端的条件"""
        mod = _load_module_from_file("langfuse_client_test3", _langfuse_client_path)
        with (
            patch.object(mod.settings, "langfuse_enabled", True),
            patch.object(mod.settings, "langfuse_public_key", "pk-test"),
            patch.object(mod.settings, "langfuse_secret_key", "sk-test"),
        ):
            assert mod.LangfuseClient._can_initialize_real_client() is True

    def test_cannot_initialize_without_keys(self):
        """缺少密钥时不能初始化真实客户端"""
        mod = _load_module_from_file("langfuse_client_test4", _langfuse_client_path)
        with (
            patch.object(mod.settings, "langfuse_enabled", True),
            patch.object(mod.settings, "langfuse_public_key", ""),
            patch.object(mod.settings, "langfuse_secret_key", ""),
        ):
            assert mod.LangfuseClient._can_initialize_real_client() is False

    def test_no_duplicate_code_blocks_in_init(self):
        """验证初始化逻辑无重复代码块（P0-1 修复验证）"""
        mod = _load_module_from_file("langfuse_client_test5", _langfuse_client_path)
        source = inspect.getsource(mod.LangfuseClient.__init__)
        init_lines = source.split("\n")

        mock_setup_count = 0
        for line in init_lines:
            if "_setup_mock_client" in line.strip():
                mock_setup_count += 1

        assert (
            mock_setup_count == 3
        ), f"_setup_mock_client 应在3个分支中各调用一次，实际调用 {mock_setup_count} 次"

    def test_setup_mock_client_creates_mock(self):
        """_setup_mock_client 创建 Mock 客户端"""
        mod = _load_module_from_file("langfuse_client_test6", _langfuse_client_path)
        client = mod.LangfuseClient.__new__(mod.LangfuseClient)
        client._mock_enabled = False
        client.client = None
        client._setup_mock_client()

        assert client._mock_enabled is True
        assert client.client is not None
        assert hasattr(client.client, "trace")
        assert hasattr(client.client, "flush")


class TestTraceIdContext:
    """trace_id 上下文管理测试"""

    def test_set_and_get_trace_id(self):
        """设置和获取 trace_id"""
        mod = _load_module_from_file("langfuse_client_test7", _langfuse_client_path)
        token = mod._trace_id_var.set("trace-123")
        try:
            assert mod.get_current_trace_id() == "trace-123"
        finally:
            mod._trace_id_var.reset(token)

    def test_default_trace_id_is_none(self):
        """默认 trace_id 为 None"""
        mod = _load_module_from_file("langfuse_client_test8", _langfuse_client_path)
        token = mod._trace_id_var.set(None)
        try:
            assert mod.get_current_trace_id() is None
        finally:
            mod._trace_id_var.reset(token)


class TestDummySpan:
    """DummySpan 测试"""

    def test_end_does_not_raise(self):
        """DummySpan.end 不抛异常"""
        mod = _load_module_from_file("langfuse_client_test9", _langfuse_client_path)
        span = mod.DummySpan()
        span.end()

    def test_score_does_not_raise(self):
        """DummySpan.score 不抛异常"""
        mod = _load_module_from_file("langfuse_client_test10", _langfuse_client_path)
        span = mod.DummySpan()
        span.score()

    def test_context_manager(self):
        """DummySpan 可作为上下文管理器"""
        mod = _load_module_from_file("langfuse_client_test11", _langfuse_client_path)
        with mod.DummySpan() as span:
            assert span is not None


class TestScoresConstants:
    """评分常量测试"""

    def test_score_names_in_source(self):
        """验证评分名称在源码中定义"""
        with open(_langfuse_client_path) as f:
            source = f.read()
        assert "intent_confidence" in source
        assert "retrieval_relevance" in source
        assert "issue_resolved" in source
        assert "user_satisfaction" in source
        assert "failure_type" in source
