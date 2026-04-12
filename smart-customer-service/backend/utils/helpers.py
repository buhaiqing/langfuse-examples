"""
General utility helper functions
"""

import hashlib
import time
from typing import Any


def generate_session_id(prefix: str = "session") -> str:
    """Generate a unique session ID"""
    timestamp = int(time.time() * 1000)
    random_part = hashlib.md5(str(timestamp).encode()).hexdigest()[:8]
    return f"{prefix}_{random_part}"


def format_duration(milliseconds: float) -> str:
    """Format duration in human-readable format"""
    if milliseconds < 1000:
        return f"{milliseconds:.0f}ms"
    elif milliseconds < 60000:
        return f"{milliseconds / 1000:.2f}s"
    else:
        minutes = milliseconds / 60000
        return f"{minutes:.2f}min"


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def safe_get(dictionary: dict, key: str, default: Any = None) -> Any:
    """Safely get value from dictionary with default"""
    try:
        return dictionary.get(key, default)
    except (AttributeError, TypeError):
        return default


def mask_email(email: str) -> str:
    """Mask email address for display"""
    if not email or "@" not in email:
        return "***"

    parts = email.split("@")
    if len(parts) != 2:
        return "***"

    username = parts[0]
    domain = parts[1]

    if len(username) > 2:
        masked_username = username[:2] + "***"
    else:
        masked_username = "**"

    return f"{masked_username}@{domain}"


def calculate_success_rate(success_count: int, total_count: int) -> float:
    """Calculate success rate as a percentage"""
    if total_count == 0:
        return 0.0
    return round(success_count / total_count, 2)


def is_valid_uuid(uuid_string: str) -> bool:
    """Check if string is a valid UUID format"""
    import re

    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    return bool(re.match(uuid_pattern, uuid_string, re.IGNORECASE))


# Export
__all__ = [
    "generate_session_id",
    "format_duration",
    "truncate_text",
    "safe_get",
    "mask_email",
    "calculate_success_rate",
    "is_valid_uuid",
]
