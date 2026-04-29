"""
Unit tests for data masking utilities.

Tests cover phone, email, ID card, name masking,
nested data structures, and user ID hashing.
"""

from src.observability.data_masking import (
    hash_user_id,
    mask_sensitive_data,
    sanitize_for_logging,
)


class TestMaskSensitiveData:
    """Test mask_sensitive_data function."""

    def test_mask_phone_number(self):
        """Test phone number masking: 138****5678."""
        data = {"phone": "13812345678"}
        result = mask_sensitive_data(data)
        assert result["phone"] == "138****5678"

    def test_mask_mobile_number(self):
        """Test mobile number masking."""
        data = {"mobile": "13987654321"}
        result = mask_sensitive_data(data)
        assert result["mobile"] == "139****4321"

    def test_mask_short_phone(self):
        """Test short phone number masking."""
        data = {"phone": "123"}
        result = mask_sensitive_data(data)
        assert result["phone"] == "***"

    def test_mask_email(self):
        """Test email masking: zh***@example.com."""
        data = {"email": "zhangsan@example.com"}
        result = mask_sensitive_data(data)
        assert result["email"] == "zh***@example.com"

    def test_mask_short_email(self):
        """Test short email masking."""
        data = {"email": "ab@test.com"}
        result = mask_sensitive_data(data)
        assert result["email"] == "***@test.com"

    def test_mask_email_without_at(self):
        """Test invalid email masking."""
        data = {"email": "invalid-email"}
        result = mask_sensitive_data(data)
        assert result["email"] == "***@***"

    def test_mask_id_card(self):
        """Test ID card masking: 110101********1234."""
        data = {"id_card": "110101199001011234"}
        result = mask_sensitive_data(data)
        assert result["id_card"] == "110101********1234"

    def test_mask_short_id_card(self):
        """Test short ID card masking."""
        data = {"id_number": "12345"}
        result = mask_sensitive_data(data)
        assert result["id_number"] == "***"

    def test_mask_name_chinese(self):
        """Test Chinese name masking: 张*."""
        data = {"name": "张三"}
        result = mask_sensitive_data(data)
        assert result["name"] == "张*"

    def test_mask_name_english(self):
        """Test English name masking: John***."""
        data = {"username": "JohnDoe"}
        result = mask_sensitive_data(data)
        assert result["username"] == "J******"

    def test_mask_single_char_name(self):
        """Test single character name masking."""
        data = {"user_name": "A"}
        result = mask_sensitive_data(data)
        assert result["user_name"] == "*"

    def test_mask_password(self):
        """Test password removal."""
        data = {"password": "secret123"}
        result = mask_sensitive_data(data)
        assert result["password"] == "***REMOVED***"

    def test_mask_api_key(self):
        """Test API key removal."""
        data = {"api_key": "sk-1234567890"}
        result = mask_sensitive_data(data)
        assert result["api_key"] == "***REMOVED***"

    def test_mask_secret_token(self):
        """Test secret token removal."""
        data = {"secret_token": "token_value"}
        result = mask_sensitive_data(data)
        assert result["secret_token"] == "***REMOVED***"

    def test_mask_credit_card(self):
        """Test credit card removal."""
        data = {"credit_card": "4111111111111111"}
        result = mask_sensitive_data(data)
        assert result["credit_card"] == "***REMOVED***"

    def test_mask_bank_account(self):
        """Test bank account removal."""
        data = {"bank_account": "6222021234567890"}
        result = mask_sensitive_data(data)
        assert result["bank_account"] == "***REMOVED***"

    def test_mask_address(self):
        """Test address masking."""
        data = {"address": "北京市朝阳区建国路88号"}
        result = mask_sensitive_data(data)
        assert result["address"] == "北京市朝****路88号"

    def test_mask_ip_address(self):
        """Test IP address masking."""
        data = {"ip_address": "192.168.1.100"}
        result = mask_sensitive_data(data)
        assert result["ip_address"] == "192.****.100"

    def test_non_sensitive_fields_unchanged(self):
        """Test non-sensitive fields are not masked."""
        data = {
            "user_id": "user_123",
            "session_id": "session_456",
            "query": "How to reset password?",
        }
        result = mask_sensitive_data(data)
        assert result["user_id"] == "user_123"
        assert result["session_id"] == "session_456"
        assert result["query"] == "How to reset password?"

    def test_nested_dict_masking(self):
        """Test nested dictionary masking."""
        data = {
            "user": {
                "name": "张三",
                "phone": "13812345678",
                "email": "zhangsan@example.com",
            },
            "metadata": {
                "api_key": "sk-secret",
                "version": "v1.0",
            },
        }
        result = mask_sensitive_data(data)
        assert result["user"]["name"] == "张*"
        assert result["user"]["phone"] == "138****5678"
        assert result["user"]["email"] == "zh***@example.com"
        assert result["metadata"]["api_key"] == "***REMOVED***"
        assert result["metadata"]["version"] == "v1.0"

    def test_list_masking(self):
        """Test list masking."""
        data = {
            "users": [
                {"name": "张三", "phone": "13812345678"},
                {"name": "李四", "phone": "13987654321"},
            ]
        }
        result = mask_sensitive_data(data)
        assert result["users"][0]["name"] == "张*"
        assert result["users"][0]["phone"] == "138****5678"
        assert result["users"][1]["name"] == "李*"
        assert result["users"][1]["phone"] == "139****4321"

    def test_mixed_types_in_dict(self):
        """Test dict with mixed value types."""
        data = {
            "phone": "13812345678",
            "age": 25,
            "active": True,
            "score": None,
        }
        result = mask_sensitive_data(data)
        assert result["phone"] == "138****5678"
        assert result["age"] == "***MASKED***"
        assert result["active"] == "***MASKED***"
        assert result["score"] == "***MASKED***"

    def test_empty_dict(self):
        """Test empty dict."""
        data = {}
        result = mask_sensitive_data(data)
        assert result == {}

    def test_empty_list(self):
        """Test empty list."""
        data = {"items": []}
        result = mask_sensitive_data(data)
        assert result["items"] == []

    def test_top_level_string_unchanged(self):
        """Test top-level string is unchanged."""
        data = "This is a test string"
        result = mask_sensitive_data(data)
        assert result == "This is a test string"

    def test_primitive_types_unchanged(self):
        """Test primitive types are unchanged."""
        assert mask_sensitive_data(42) == 42
        assert mask_sensitive_data(3.14) == 3.14
        assert mask_sensitive_data(True) is True
        assert mask_sensitive_data(None) is None


class TestHashUserId:
    """Test hash_user_id function."""

    def test_hash_consistency(self):
        """Test that same input produces same hash."""
        user_id = "user_12345"
        hash1 = hash_user_id(user_id)
        hash2 = hash_user_id(user_id)
        assert hash1 == hash2

    def test_hash_length(self):
        """Test hash length is 16 characters."""
        hash_value = hash_user_id("test_user")
        assert len(hash_value) == 16

    def test_hash_is_hexadecimal(self):
        """Test hash contains only hex characters."""
        hash_value = hash_user_id("test_user")
        # Should only contain 0-9 and a-f
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_different_inputs_different_hashes(self):
        """Test different inputs produce different hashes."""
        hash1 = hash_user_id("user_1")
        hash2 = hash_user_id("user_2")
        assert hash1 != hash2

    def test_hash_is_deterministic(self):
        """Test hash is deterministic across calls."""
        user_id = "consistent_user"
        hashes = [hash_user_id(user_id) for _ in range(10)]
        assert len(set(hashes)) == 1  # All hashes should be identical


class TestSanitizeForLogging:
    """Test sanitize_for_logging function."""

    def test_sensitive_fields_sanitized(self):
        """Test sensitive fields are replaced with ***SANITIZED***."""
        data = {
            "phone": "13812345678",
            "email": "test@example.com",
            "password": "secret",
        }
        result = sanitize_for_logging(data)
        assert result["phone"] == "***SANITIZED***"
        assert result["email"] == "***SANITIZED***"
        assert result["password"] == "***SANITIZED***"

    def test_non_sensitive_fields_preserved(self):
        """Test non-sensitive fields are preserved."""
        data = {
            "user_id": "user_123",
            "query": "test query",
            "count": 10,
        }
        result = sanitize_for_logging(data)
        assert result["user_id"] == "user_123"
        assert result["query"] == "test query"
        assert result["count"] == 10

    def test_non_dict_input(self):
        """Test non-dict input is returned as-is."""
        assert sanitize_for_logging("string") == "string"
        assert sanitize_for_logging(123) == 123
        assert sanitize_for_logging([1, 2, 3]) == [1, 2, 3]
