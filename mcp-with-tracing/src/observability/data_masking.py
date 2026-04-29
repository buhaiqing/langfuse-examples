"""
Data masking utilities for protecting sensitive information.

Provides global masking functions for Langfuse client to automatically
sanitize PII (Personally Identifiable Information) before sending
traces to Langfuse servers.
"""

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Sensitive field patterns (case-insensitive matching)
SENSITIVE_PATTERNS = {
    # Phone numbers
    "phone",
    "mobile",
    "telephone",
    "phone_number",
    "mobile_number",
    # Email addresses
    "email",
    "mail",
    "email_address",
    # Identity cards
    "id_card",
    "id_number",
    "identity",
    "national_id",
    # Names
    "name",
    "username",
    "user_name",
    "full_name",
    "contact_name",
    # Financial information
    "card_number",
    "credit_card",
    "bank_account",
    "account_number",
    # Secrets and tokens
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "access_key",
    "secret_key",
    "private_key",
    "auth_token",
    # Addresses
    "address",
    "ip_address",
    "ip",
    "location",
}


def mask_sensitive_data(data: Any) -> Any:
    """
    Recursively mask sensitive data in dictionaries and lists.

    This function is designed to be used as the `mask=` parameter
    when initializing the Langfuse client. It will be called automatically
    on all input/output data before sending to Langfuse.

    Args:
        data: Input data (dict, list, str, or other types).

    Returns:
        Masked data with sensitive information replaced.

    Example:
        >>> mask_sensitive_data({"phone": "13812345678", "name": "张三"})
        {'phone': '138****5678', 'name': '张*'}
    """
    if isinstance(data, dict):
        return {key: _mask_value(key, value) for key, value in data.items()}
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    # Top-level strings and other primitives are returned as-is
    return data


def _mask_value(field_name: str, value: Any) -> Any:
    """
    Mask a value based on its field name.

    Args:
        field_name: The dictionary key or field name.
        value: The value to potentially mask.

    Returns:
        Masked value if field is sensitive, original value otherwise.
    """
    # Recursively handle nested dicts and lists
    if isinstance(value, dict):
        return {k: _mask_value(k, v) for k, v in value.items()}
    elif isinstance(value, list):
        return [mask_sensitive_data(item) for item in value]

    # Non-string values are masked completely
    if not isinstance(value, str):
        return "***MASKED***"

    field_lower = field_name.lower()

    # Check if field matches any sensitive pattern
    is_sensitive = any(pattern in field_lower for pattern in SENSITIVE_PATTERNS)

    if not is_sensitive:
        return value

    # Apply field-specific masking
    return _mask_by_field_type(field_lower, value)


def _mask_by_field_type(field_name: str, value: str) -> str:
    """
    Apply masking strategy based on field type.

    Args:
        field_name: Lowercase field name.
        value: String value to mask.

    Returns:
        Masked string.
    """
    # Phone numbers: 138****5678
    if any(p in field_name for p in ["phone", "mobile", "telephone"]):
        if len(value) >= 7:
            return value[:3] + "****" + value[-4:]
        return "***"

    # Email addresses: zh***@example.com
    if any(p in field_name for p in ["email", "mail"]):
        if "@" in value:
            parts = value.split("@")
            if len(parts[0]) > 2:
                return parts[0][:2] + "***@" + parts[1]
            return "***@" + parts[1]
        return "***@***"

    # ID cards: 110101********1234
    if any(p in field_name for p in ["id_card", "id_number", "identity"]):
        if len(value) >= 10:
            return value[:6] + "********" + value[-4:]
        return "***"

    # Names: 张* or John***
    if any(p in field_name for p in ["name", "username", "user_name"]):
        if len(value) > 1:
            return value[0] + "*" * (len(value) - 1)
        return "*"

    # Financial information: completely hide
    if any(p in field_name for p in ["card", "bank", "account"]):
        return "***REMOVED***"

    # Passwords, secrets, tokens: completely remove
    if any(p in field_name for p in ["password", "secret", "token", "key"]):
        return "***REMOVED***"

    # Addresses and IPs: partial mask
    if any(p in field_name for p in ["address", "ip"]):
        if len(value) > 8:
            return value[:4] + "****" + value[-4:]
        return "***"

    # Default: complete mask for unknown sensitive fields
    return "***MASKED***"


def hash_user_id(user_id: str) -> str:
    """
    Create a one-way hash for user ID to protect privacy.

    Uses SHA-256 hashing with a truncated output (16 characters)
    to maintain consistency for tracking while protecting PII.

    Args:
        user_id: Original user identifier.

    Returns:
        Hashed user ID (16-character hex string).

    Example:
        >>> hash_user_id("user_12345")
        'a1b2c3d4e5f6g7h8'
    """
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]


def sanitize_for_logging(data: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize data for safe logging (less aggressive than mask_sensitive_data).

    This function is suitable for application logs where some data visibility
    is needed for debugging, but sensitive fields should still be protected.

    Args:
        data: Dictionary to sanitize.

    Returns:
        Sanitized dictionary safe for logging.
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in SENSITIVE_PATTERNS):
            sanitized[key] = "***SANITIZED***"
        else:
            sanitized[key] = value

    return sanitized
