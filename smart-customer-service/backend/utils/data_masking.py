"""
Sensitive data masking utilities for privacy protection
"""

import hashlib
import re
from typing import Any


def mask_sensitive_data(data: Any) -> Any:
    """
    Global masking function for sensitive data.
    Langfuse will automatically call this function before sending data.

    Args:
        data: Input data (dict, str, list, or other types)

    Returns:
        Masked data with sensitive information hidden
    """
    if isinstance(data, dict):
        return _mask_dict(data)
    elif isinstance(data, str):
        return _mask_string(data)
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    else:
        return data


def _mask_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Mask sensitive fields in dictionary"""
    masked = data.copy()

    # Define sensitive field patterns
    sensitive_fields = {
        "phone",
        "mobile",
        "telephone",
        "email",
        "mail",
        "id_card",
        "id_number",
        "identity",
        "name",
        "username",
        "user_name",
        "card_number",
        "credit_card",
        "bank_account",
        "password",
        "secret",
        "token",
        "api_key",
        "access_token",
        "address",
        "ip_address",
        "ip",
    }

    for key in list(masked.keys()):
        # Check if key matches sensitive patterns
        if key.lower() in sensitive_fields:
            masked[key] = _mask_value_by_type(key, masked[key])
        # Also check for partial matches
        elif any(
            pattern in key.lower()
            for pattern in ["phone", "email", "id_card", "password", "secret", "token"]
        ):
            masked[key] = "***MASKED***"

    return masked


def _mask_value_by_type(field_name: str, value: Any) -> Any:
    """Mask value based on field type"""
    if not isinstance(value, str):
        return "***MASKED***"

    field_lower = field_name.lower()

    # Phone number masking: 138****5678
    if field_lower in ["phone", "mobile", "telephone"]:
        if len(value) >= 7:
            return value[:3] + "****" + value[-4:]
        return "***"

    # Email masking: zh***@example.com
    if field_lower in ["email", "mail"]:
        parts = value.split("@")
        if len(parts) == 2 and len(parts[0]) > 2:
            return parts[0][:2] + "***@" + parts[1]
        return "***@***"

    # ID card masking: 110101********1234
    if field_lower in ["id_card", "id_number", "identity"]:
        if len(value) >= 10:
            return value[:6] + "********" + value[-4:]
        return "***"

    # Name masking: 张*
    if field_lower in ["name", "username", "user_name"]:
        if len(value) > 1:
            return value[0] + "*" * (len(value) - 1)
        return "*"

    # Bank card masking
    if field_lower in ["card_number", "credit_card", "bank_account"]:
        card = value.replace(" ", "")
        if len(card) >= 8:
            return "**** **** **** " + card[-4:]
        return "****"

    # IP address masking
    if field_lower in ["ip_address", "ip"]:
        parts = value.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.***.**"

    # Password/secret/token - completely hide
    if any(pattern in field_lower for pattern in ["password", "secret", "token", "key"]):
        return "***REMOVED***"

    return "***MASKED***"


def _mask_string(data: str) -> str:
    """Mask sensitive patterns in string using regex"""
    # Mask phone numbers (Chinese format)
    data = re.sub(r"1[3-9]\d{9}", lambda m: m.group()[:3] + "****", data)

    # Mask email addresses
    data = re.sub(r"(\w{2})\w*@(\w+\.\w+)", r"\1***@\2", data)

    # Mask ID cards (18 digits)
    data = re.sub(r"(\d{6})\d{8}(\d{4})", r"\1********\2", data)

    return data


def hash_user_id(user_id: str) -> str:
    """
    Create one-way hash for user IDs to protect privacy
    while maintaining consistency for tracking

    Args:
        user_id: Original user ID

    Returns:
        Hashed user ID (SHA-256)
    """
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]


def sanitize_for_logging(data: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize data specifically for logging purposes.
    More aggressive than standard masking.

    Args:
        data: Dictionary containing potentially sensitive data

    Returns:
        Sanitized dictionary safe for logging
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        # Skip highly sensitive fields entirely
        if key.lower() in ["password", "secret", "token", "api_key", "access_token"]:
            continue

        # Apply standard masking
        sanitized[key] = mask_sensitive_data(value)

    return sanitized
