"""
Pytest 配置和 fixtures
"""

import sys
from pathlib import Path

backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))

import os  # noqa: E402

os.environ["ENVIRONMENT"] = "testing"
os.environ["LOG_LEVEL"] = "DEBUG"

os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "test_public_key")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "test_secret_key")
os.environ.setdefault("LANGFUSE_HOST", "http://localhost:3000")

os.environ.setdefault("OPENAI_API_KEY", "test_api_key")

os.environ.setdefault("JWT_SECRET_KEY", "test_jwt_secret_key_for_testing_purposes_only")

os.environ.setdefault("SERVICE_API_KEYS", "sk-test1234567890,sk-test0987654321")

from unittest.mock import MagicMock  # noqa: E402

mock_langfuse_client_module = MagicMock()
mock_langfuse_obj = MagicMock()
mock_langfuse_obj.trace = MagicMock(return_value=MagicMock(id="mock-trace-id"))
mock_langfuse_obj.start_as_current_span = MagicMock()
mock_langfuse_obj.start_as_current_observation = MagicMock()

mock_instance = MagicMock()
mock_instance.client = mock_langfuse_obj
mock_instance.is_enabled = MagicMock(return_value=True)
mock_instance.is_mock = MagicMock(return_value=True)
mock_instance.trace = mock_langfuse_obj.trace
mock_instance.flush = MagicMock()
mock_instance.shutdown = MagicMock()

mock_langfuse_client_module.langfuse_client = mock_instance
mock_langfuse_client_module.LangfuseClient = MagicMock
mock_langfuse_client_module.trace_customer_service = MagicMock()
mock_langfuse_client_module.score_trace = MagicMock()
mock_langfuse_client_module.Scores = MagicMock()
mock_langfuse_client_module.DummySpan = MagicMock()
mock_langfuse_client_module.create_span = MagicMock()
mock_langfuse_client_module.get_current_trace_id = MagicMock(return_value=None)
mock_langfuse_client_module.get_current_span = MagicMock(return_value=None)
mock_langfuse_client_module.set_current_trace_id = MagicMock()
mock_langfuse_client_module._trace_id_var = MagicMock()

sys.modules["core.langfuse_client"] = mock_langfuse_client_module
