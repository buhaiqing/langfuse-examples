"""
Tests for centralized logging configuration
"""

import pytest
from core.logging_config import LogCategory, get_logger


class TestLogCategory:
    """Test suite for LogCategory enum"""

    def test_log_category_values(self):
        """Verify all log categories are defined"""
        assert LogCategory.RAG.value == "rag"
        assert LogCategory.INTENT.value == "intent"
        assert LogCategory.DIALOGUE.value == "dialogue"
        assert LogCategory.TOOL.value == "tool"
        assert LogCategory.ESCALATION.value == "escalation"
        assert LogCategory.CORE.value == "core"
        assert LogCategory.API.value == "api"
        assert LogCategory.GENERAL.value == "general"

    def test_log_category_count(self):
        """Verify number of log categories"""
        assert len(LogCategory) == 8


class TestGetLogger:
    """Test suite for get_logger function"""

    def test_get_logger_returns_logger(self):
        """Verify get_logger returns a logger instance"""
        logger = get_logger(LogCategory.RAG)
        assert logger is not None

    def test_get_logger_default_category(self):
        """Verify get_logger works with default category"""
        logger = get_logger()
        assert logger is not None

    def test_get_logger_all_categories(self):
        """Verify get_logger works with all categories"""
        for category in LogCategory:
            logger = get_logger(category)
            assert logger is not None

    def test_category_logger_has_required_methods(self):
        """Verify _CategoryLogger has all required logging methods"""
        logger = get_logger(LogCategory.RAG)
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'critical')


class TestLoggingIntegration:
    """Integration tests for logging with different scenarios"""

    def test_log_with_extra_context(self):
        """Verify logs can include extra context"""
        logger = get_logger(LogCategory.CORE)
        logger.info("Test message", user_id="user123", action="test")

    def test_log_with_session_context(self):
        """Verify logs can include session context"""
        logger = get_logger(LogCategory.GENERAL)
        logger.debug("Processing request", session_id="sess_123", turn=1)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_log_empty_message(self):
        """Verify logging empty message works"""
        logger = get_logger(LogCategory.GENERAL)
        logger.info("")

    def test_log_unicode_message(self):
        """Verify logging unicode message works"""
        logger = get_logger(LogCategory.GENERAL)
        logger.info("测试消息 🎉")

    def test_log_special_characters(self):
        """Verify logging special characters works"""
        logger = get_logger(LogCategory.GENERAL)
        logger.debug("Special: <>&\"'@#$%^&*()")

    def test_log_very_long_message(self):
        """Verify logging very long message works"""
        logger = get_logger(LogCategory.GENERAL)
        long_message = "A" * 10000
        logger.warning(long_message)

    def test_log_with_none_values_in_context(self):
        """Verify logging with None values in context handles gracefully"""
        logger = get_logger(LogCategory.GENERAL)
        logger.info("Test", value=None, name="test")

    def test_log_with_nested_context(self):
        """Verify logging with nested dict context works"""
        logger = get_logger(LogCategory.GENERAL)
        nested_context = {"user": {"id": "123", "name": "Test"}, "action": "login"}
        logger.info("User action", **nested_context)
