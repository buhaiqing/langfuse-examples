"""
数据格式化工具

提供通用的数据格式化函数。
"""
from datetime import datetime


def format_timestamp(ts: float | str) -> str:
    """
    格式化时间戳为可读字符串。

    Args:
        ts: 时间戳（浮点数）或 ISO 字符串

    Returns:
        格式化后的时间字符串
    """
    try:
        if isinstance(ts, str):
            dt = datetime.fromisoformat(ts)
        else:
            dt = datetime.fromtimestamp(ts)

        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    格式化百分比。

    Args:
        value: 0-1 范围的值
        decimals: 小数位数

    Returns:
        百分比字符串（如 "95.50%"）
    """
    return f"{value * 100:.{decimals}f}%"


def format_latency(ms: float) -> str:
    """
    格式化延迟时间。

    Args:
        ms: 毫秒数

    Returns:
        格式化后的延迟字符串
    """
    if ms < 1000:
        return f"{ms:.0f}ms"
    else:
        return f"{ms / 1000:.2f}s"


def format_qps(qps: float) -> str:
    """
    格式化请求率。

    Args:
        qps: 每秒请求数

    Returns:
        格式化后的请求率字符串
    """
    return f"{qps:.2f}/s"


def format_severity(severity: str) -> str:
    """
    格式化告警严重性为表情符号。

    Args:
        severity: 严重性级别（info/warning/critical）

    Returns:
        表情符号 + 文本
    """
    severity_map = {
        "info": "ℹ️ INFO",
        "warning": "⚠️ WARNING",
        "critical": "🚨 CRITICAL",
    }
    return severity_map.get(severity.lower(), severity)


def format_status(status: str) -> str:
    """
    格式化状态为表情符号。

    Args:
        status: 状态字符串

    Returns:
        表情符号 + 文本
    """
    status_map = {
        "healthy": "🟢 Healthy",
        "degraded": "🟡 Degraded",
        "error": "🔴 Error",
        "connected": "🟢 Connected",
        "disconnected": "🔴 Disconnected",
        "running": "🟢 Running",
        "stopped": "🔴 Stopped",
    }
    return status_map.get(status.lower(), status)
