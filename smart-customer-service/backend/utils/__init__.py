"""通用工具模块"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """获取当前 UTC 时间（timezone-aware）

    替代已废弃的 datetime.utcnow()，返回带时区信息的 datetime 对象。
    Python 3.12 中 datetime.utcnow() 已标记为废弃。
    """
    return datetime.now(timezone.utc)
