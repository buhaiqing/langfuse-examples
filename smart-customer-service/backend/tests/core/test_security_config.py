"""安全与配置测试

测试:
- service_api_keys 类型一致性（P0-4 修复验证）
- datetime.utcnow() 替换（P0-5 修复验证）
- API Key 验证逻辑
"""

import os
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from utils import utcnow


class TestUtcnow:
    """utcnow 工具函数测试"""

    def test_returns_timezone_aware_datetime(self):
        """返回带时区信息的 datetime"""
        result = utcnow()
        assert result.tzinfo is not None

    def test_returns_utc_timezone(self):
        """返回 UTC 时区"""
        result = utcnow()
        assert result.tzinfo == timezone.utc

    def test_close_to_now(self):
        """返回时间接近当前时间"""
        result = utcnow()
        now = datetime.now(timezone.utc)
        delta = abs((now - result).total_seconds())
        assert delta < 2

    def test_not_using_deprecated_utcnow(self):
        """验证不使用废弃的 datetime.utcnow()"""
        import ast

        import utils

        source = open(utils.__file__).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Call, ast.Attribute)):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    is_utcnow = node.func.attr == "utcnow"
                    is_datetime = (
                        isinstance(node.func.value, ast.Name) and node.func.value.id == "datetime"
                    )
                    if is_utcnow and is_datetime:
                        pytest.fail("代码中不应使用 datetime.utcnow()，应使用 utcnow()")


class TestServiceApiKeys:
    """service_api_keys 类型一致性测试"""

    def test_api_keys_parsed_as_list(self):
        """API Keys 应被解析为列表"""
        with patch.dict(os.environ, {"SERVICE_API_KEYS": "sk-key1,sk-key2,sk-key3"}):
            from core.config import Settings

            s = Settings()
            result = s.service_api_keys
            assert isinstance(result, list)
            assert len(result) == 3
            assert "sk-key1" in result

    def test_api_keys_single_value(self):
        """单个 API Key 也应为列表"""
        with patch.dict(os.environ, {"SERVICE_API_KEYS": "sk-singlekey12345"}):
            from core.config import Settings

            s = Settings()
            result = s.service_api_keys
            assert isinstance(result, list)
            assert len(result) == 1

    def test_api_keys_empty_string(self):
        """空字符串应返回空列表"""
        with patch.dict(os.environ, {"SERVICE_API_KEYS": ""}):
            from core.config import Settings

            s = Settings()
            result = s.service_api_keys
            assert isinstance(result, list)
            assert len(result) == 0

    def test_api_keys_strips_whitespace(self):
        """API Keys 应去除空白字符"""
        with patch.dict(os.environ, {"SERVICE_API_KEYS": "sk-key1 , sk-key2 , sk-key3"}):
            from core.config import Settings

            s = Settings()
            result = s.service_api_keys
            assert isinstance(result, list)
            for key in result:
                assert key == key.strip()


class TestSecurityModule:
    """安全模块测试"""

    def test_verify_service_api_key_valid(self):
        """有效 API Key 验证通过"""
        with patch.dict(os.environ, {"SERVICE_API_KEYS": "sk-test1234567890,sk-test0987654321"}):
            from core.security import verify_service_api_key

            result = verify_service_api_key("sk-test1234567890")
            assert result is True

    def test_verify_service_api_key_invalid(self):
        """无效 API Key 验证失败"""
        with patch.dict(os.environ, {"SERVICE_API_KEYS": "sk-test1234567890"}):
            from core.security import verify_service_api_key

            result = verify_service_api_key("sk-invalid-key")
            assert result is False

    def test_verify_service_api_key_empty_keys(self):
        """空 API Keys 配置时验证失败"""
        with patch.dict(os.environ, {"SERVICE_API_KEYS": ""}):
            from core.security import verify_service_api_key

            result = verify_service_api_key("sk-any-key")
            assert result is False
