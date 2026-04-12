"""
Centralized logging configuration for the customer service system.
Provides structured logging with different levels and categories for easy problem diagnosis.
"""

import logging
import sys
from enum import Enum
from typing import Optional

from config.settings import ENVIRONMENT


class LogCategory(str, Enum):
    """Log categories for different system components"""
    RAG = "rag"
    INTENT = "intent"
    DIALOGUE = "dialogue"
    TOOL = "tool"
    ESCALATION = "escalation"
    CORE = "core"
    API = "api"
    GENERAL = "general"


class LogLevel(str, Enum):
    """Log level definitions"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CentralizedLogger:
    """Centralized logger with category support - singleton pattern"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not CentralizedLogger._initialized:
            self._setup_logging()
            CentralizedLogger._initialized = True

    def _setup_logging(self):
        """Setup centralized logging with handlers and formatters"""
        self.logger = logging.getLogger("customer_service")
        self.logger.setLevel(self._get_level())

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(category)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _get_level(self) -> int:
        """Determine logging level based on environment"""
        if ENVIRONMENT == "production":
            return logging.INFO
        elif ENVIRONMENT == "development":
            return logging.DEBUG
        return logging.INFO

    def _log(self, level: int, category: str, message: str, **kwargs):
        """Internal log method with extra context"""
        extra = {"category": category}
        if kwargs:
            extra["context"] = kwargs
        self.logger.log(level, message, extra=extra)

    def debug(self, category: LogCategory, message: str, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, category.value, message, **kwargs)

    def info(self, category: LogCategory, message: str, **kwargs):
        """Log info message"""
        self._log(logging.INFO, category.value, message, **kwargs)

    def warning(self, category: LogCategory, message: str, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, category.value, message, **kwargs)

    def error(self, category: LogCategory, message: str, **kwargs):
        """Log error message"""
        self._log(logging.ERROR, category.value, message, **kwargs)

    def critical(self, category: LogCategory, message: str, **kwargs):
        """Log critical message"""
        self._log(logging.CRITICAL, category.value, message, **kwargs)


# Global singleton instance
_logger = CentralizedLogger()


class _CategoryLogger:
    """A logger wrapper that pre-sets the category for all log calls"""

    def __init__(self, category: LogCategory):
        self._category = category

    def _log(self, level: int, message: str, **kwargs):
        """Internal log method with pre-set category"""
        extra = {"category": self._category.value}
        if kwargs:
            extra["context"] = kwargs
        _logger.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log(logging.CRITICAL, message, **kwargs)


def get_logger(category: LogCategory = LogCategory.GENERAL) -> _CategoryLogger:
    """
    Get the centralized logger instance with pre-set category.

    Args:
        category: Log category (used as prefix in log messages)

    Returns:
        _CategoryLogger instance with category pre-set
    """
    return _CategoryLogger(category)


def log_exception(category: LogCategory, message: str, exc: Exception, **kwargs):
    """
    Log an exception with full traceback context.

    Args:
        category: Log category
        message: Error description
        exc: Exception object
        **kwargs: Additional context
    """
    _CategoryLogger(category).error(
        f"{message}: {str(exc)}",
        exception_type=type(exc).__name__,
        exception_module=type(exc).__module__,
        **kwargs
    )


def log_function_entry(category: LogCategory, func_name: str, **kwargs):
    """Log function entry point"""
    _CategoryLogger(category).debug(f"Entering function: {func_name}", **kwargs)


def log_function_exit(category: LogCategory, func_name: str, execution_time_ms: float, **kwargs):
    """Log function exit point"""
    _CategoryLogger(category).debug(
        f"Exiting function: {func_name}",
        execution_time_ms=round(execution_time_ms, 2),
        **kwargs
    )


def log_api_call(category: LogCategory, endpoint: str, method: str, status_code: Optional[int] = None, **kwargs):
    """
    Log API call details.

    Args:
        category: Log category
        endpoint: API endpoint
        method: HTTP method
        status_code: Response status code
        **kwargs: Additional context
    """
    logger = _CategoryLogger(category)
    if status_code:
        if status_code >= 500:
            logger.error(f"API call failed: {method} {endpoint}", status_code=status_code, **kwargs)
        elif status_code >= 400:
            logger.warning(f"API call error: {method} {endpoint}", status_code=status_code, **kwargs)
        else:
            logger.info(f"API call success: {method} {endpoint}", status_code=status_code, **kwargs)
    else:
        logger.debug(f"API call: {method} {endpoint}", **kwargs)


# Export all utilities
__all__ = [
    "LogCategory",
    "LogLevel",
    "CentralizedLogger",
    "_CategoryLogger",
    "get_logger",
    "log_exception",
    "log_function_entry",
    "log_function_exit",
    "log_api_call",
    "_logger",
]