"""数据脱敏工具 - PII 数据识别与脱敏"""

import hashlib
import re
from typing import Any

# 敏感字段关键词
SENSITIVE_FIELDS = [
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
]


def mask_phone(phone: str) -> str:
    """
    脱敏手机号

    Args:
        phone: 手机号

    Returns:
        脱敏后的手机号 (138****5678)
    """
    if not phone or len(phone) < 7:
        return phone

    # 保留前 3 位和后 4 位
    return f"{phone[:3]}****{phone[-4:]}"


def mask_email(email: str) -> str:
    """
    脱敏邮箱

    Args:
        email: 邮箱地址

    Returns:
        脱敏后的邮箱 (zh***@example.com)
    """
    if not email or "@" not in email:
        return email

    parts = email.split("@")
    username = parts[0]
    domain = parts[1]

    # 用户名保留前 2 位
    if len(username) >= 2:
        masked_username = f"{username[:2]}***"
    else:
        masked_username = f"{username}***"

    return f"{masked_username}@{domain}"


def mask_id_card(id_card: str) -> str:
    """
    脱敏身份证号

    Args:
        id_card: 身份证号

    Returns:
        脱敏后的身份证号 (110101********1234)
    """
    if not id_card or len(id_card) < 10:
        return id_card

    # 保留前 6 位和后 4 位
    return f"{id_card[:6]}********{id_card[-4:]}"


def mask_name(name: str) -> str:
    """
    脱敏姓名

    Args:
        name: 姓名

    Returns:
        脱敏后的姓名 (张** 或 John***)
    """
    if not name:
        return name

    # 中文姓名
    if any("\u4e00" <= char <= "\u9fff" for char in name):
        if len(name) >= 2:
            return f"{name[0]}{'*' * (len(name) - 1)}"
        return name

    # 英文姓名
    if len(name) >= 3:
        return f"{name[:2]}***"
    return name


def mask_credit_card(card_number: str) -> str:
    """
    脱敏银行卡号/信用卡号

    Args:
        card_number: 卡号

    Returns:
        脱敏后的卡号 (**** **** **** 1234)
    """
    if not card_number or len(card_number) < 4:
        return card_number

    # 只保留后 4 位
    return f"**** **** **** {card_number[-4:]}"


def mask_password(password: str) -> str:
    """
    脱敏密码

    Args:
        password: 密码

    Returns:
        固定返回脱敏标识
    """
    return "***"


def mask_api_key(api_key: str) -> str:
    """
    脱敏 API Key

    Args:
        api_key: API Key

    Returns:
        脱敏后的 API Key (sk-***...xxx)
    """
    if not api_key or len(api_key) < 10:
        return "***"

    # 保留前 5 位和后 4 位
    return f"{api_key[:5]}...{api_key[-4:]}"


def mask_address(address: str) -> str:
    """
    脱敏地址

    Args:
        address: 地址

    Returns:
        脱敏后的地址 (北京市朝阳区***)
    """
    if not address or len(address) < 10:
        return address

    # 保留前部分，隐藏后部分
    return f"{address[:6]}***"


def mask_ip_address(ip: str) -> str:
    """
    脱敏 IP 地址

    Args:
        ip: IP 地址

    Returns:
        脱敏后的 IP 地址 (192.168.1.***)
    """
    if not ip or "." not in ip:
        return ip

    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.***"

    return ip


def hash_user_id(user_id: str) -> str:
    """
    哈希用户 ID(用于 Langfuse 追踪)

    Args:
        user_id: 用户 ID

    Returns:
        SHA-256 哈希后的用户 ID
    """
    if not user_id:
        return user_id

    return hashlib.sha256(user_id.encode()).hexdigest()[:16]


def mask_by_field_name(field_name: str, value: Any) -> Any:
    """
    根据字段名自动选择脱敏方式

    Args:
        field_name: 字段名
        value: 字段值

    Returns:
        脱敏后的值
    """
    if not value or not isinstance(value, str):
        return value

    field_lower = field_name.lower()

    if any(kw in field_lower for kw in ["phone", "mobile", "telephone"]):
        return mask_phone(value)
    elif any(kw in field_lower for kw in ["email", "mail"]):
        return mask_email(value)
    elif any(kw in field_lower for kw in ["id_card", "id_number", "identity"]):
        return mask_id_card(value)
    elif any(kw in field_lower for kw in ["name", "username", "user_name"]):
        if "user_id" in field_lower or "id" in field_lower:
            return hash_user_id(value)
        return mask_name(value)
    elif any(kw in field_lower for kw in ["card_number", "credit_card", "bank_account"]):
        return mask_credit_card(value)
    elif any(kw in field_lower for kw in ["password", "secret"]):
        return mask_password(value)
    elif any(kw in field_lower for kw in ["api_key", "access_token", "token"]):
        return mask_api_key(value)
    elif any(kw in field_lower for kw in ["address"]):
        return mask_address(value)
    elif any(kw in field_lower for kw in ["ip_address", "ip"]):
        return mask_ip_address(value)

    return value


def detect_pii_patterns(text: str) -> list[dict[str, Any]]:
    """
    检测文本中的 PII 模式

    Args:
        text: 待检测文本

    Returns:
        检测到的 PII 信息列表
    """
    patterns = [
        ("phone", r"1[3-9]\d{9}"),
        ("email", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        ("id_card", r"\d{17}[\dXx]"),
        ("ip_address", r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
    ]

    results = []
    for pii_type, pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            results.append({"type": pii_type, "value": match})

    return results


def mask_text(text: str) -> str:
    """
    脱敏文本中的 PII 信息

    Args:
        text: 待脱敏文本

    Returns:
        脱敏后的文本
    """
    if not text:
        return text

    # 检测并脱敏手机号
    phone_pattern = r"1[3-9]\d{9}"
    text = re.sub(phone_pattern, lambda m: mask_phone(m.group()), text)

    # 检测并脱敏邮箱
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    text = re.sub(email_pattern, lambda m: mask_email(m.group()), text)

    # 检测并脱敏身份证号
    id_card_pattern = r"\d{17}[\dXx]"
    text = re.sub(id_card_pattern, lambda m: mask_id_card(m.group()), text)

    return text


def mask_dict(data: dict[str, Any], sensitive_fields: list[str] | None = None) -> dict[str, Any]:
    """
    脱敏字典中的敏感数据

    Args:
        data: 待脱敏字典
        sensitive_fields: 额外的敏感字段列表

    Returns:
        脱敏后的字典
    """
    if not data:
        return data

    fields = sensitive_fields or []
    result = {}

    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = mask_dict(value, fields)
        elif isinstance(value, list):
            result[key] = [
                (
                    mask_dict(item, fields)
                    if isinstance(item, dict)
                    else mask_text(item) if isinstance(item, str) else value
                )
                for item in value
            ]
        elif isinstance(value, str):
            # 检查字段名是否敏感
            result[key] = mask_by_field_name(key, value)
        else:
            result[key] = value

    return result


def create_masked_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    创建脱敏后的元数据 (用于 Langfuse 追踪)

    Args:
        metadata: 原始元数据

    Returns:
        脱敏后的元数据
    """
    if not metadata:
        return metadata

    masked = {}
    for key, value in metadata.items():
        if key in ["user_id", "session_id"]:
            # 用户 ID 需要哈希
            masked[key] = hash_user_id(str(value))
        elif isinstance(value, str):
            # 字符串值检测并脱敏 PII
            masked[key] = mask_text(value)
        else:
            masked[key] = value

    return masked
