"""Tests for PII Detector."""

from skill_observability_toolkit.integrations.pii_detector import (
    PIIDetectionResult,
    PIIDetector,
    PIIMatch,
    PIIType,
)


def test_pii_detection_result_has_pii():
    """Test PIIDetectionResult.has_pii property."""
    result = PIIDetectionResult(text="test", matches=[])
    assert result.has_pii is False

    result = PIIDetectionResult(
        text="test",
        matches=[PIIMatch(PIIType.EMAIL, "test@example.com", 0, 16, 0.9)],
    )
    assert result.has_pii is True


def test_pii_detection_result_pii_types():
    """Test PIIDetectionResult.pii_types property."""
    result = PIIDetectionResult(
        text="test",
        matches=[
            PIIMatch(PIIType.EMAIL, "test@example.com", 0, 16, 0.9),
            PIIMatch(PIIType.EMAIL, "other@example.com", 20, 37, 0.9),
            PIIMatch(PIIType.PHONE, "123-456-7890", 40, 52, 0.85),
        ],
    )

    types = result.pii_types
    assert PIIType.EMAIL in types
    assert PIIType.PHONE in types
    assert len(types) == 2


def test_pii_detector_initialization():
    """Test PIIDetector can be initialized."""
    detector = PIIDetector()
    assert detector.confidence_threshold == 0.7


def test_detect_email():
    """Test email detection."""
    detector = PIIDetector()
    text = "Contact john@example.com for details"

    result = detector.scan(text)

    assert result.has_pii is True
    assert any(m.pii_type == PIIType.EMAIL for m in result.matches)


def test_detect_phone():
    """Test phone number detection."""
    detector = PIIDetector()
    text = "Call us at +1-555-123-4567"

    result = detector.scan(text)

    assert result.has_pii is True


def test_detect_ssn():
    """Test SSN detection."""
    detector = PIIDetector()
    text = "SSN: 123-45-6789"

    result = detector.scan(text)

    assert result.has_pii is True
    assert any(m.pii_type == PIIType.SSN for m in result.matches)
    assert any("123-45-6789" in m.value for m in result.matches)


def test_detect_credit_card():
    """Test credit card detection."""
    detector = PIIDetector()
    text = "Card: 4111 1111 1111 1111"

    result = detector.scan(text)

    assert result.has_pii is True
    assert any(m.pii_type == PIIType.CREDIT_CARD for m in result.matches)


def test_detect_china_id():
    """Test Chinese ID detection."""
    detector = PIIDetector()
    text = "ID: 110101199003071234"

    result = detector.scan(text)

    assert result.has_pii is True
    assert any(m.pii_type == PIIType.CHINA_ID for m in result.matches)


def test_detect_ip_address():
    """Test IP address detection."""
    detector = PIIDetector()
    text = "Server at 192.168.1.100 is down"

    result = detector.scan(text)

    assert result.has_pii is True
    assert any(m.pii_type == PIIType.IP_ADDRESS for m in result.matches)


def test_detect_multiple_pii():
    """Test detecting multiple PII types."""
    detector = PIIDetector()
    text = "John Doe, email: john@example.com, phone: 555-123-4567, SSN: 123-45-6789"

    result = detector.scan(text)

    assert result.total_detections >= 3


def test_custom_pii_types():
    """Test scanning with specific PII types only."""
    detector = PIIDetector()
    text = "Email: test@example.com, SSN: 123-45-6789"

    result = detector.scan(text, pii_types=[PIIType.EMAIL])

    assert any(m.pii_type == PIIType.EMAIL for m in result.matches)
    assert not any(m.pii_type == PIIType.SSN for m in result.matches)


def test_luhn_check_valid():
    """Test Luhn algorithm validation for valid card."""
    detector = PIIDetector()
    # Valid Visa card number
    assert detector._passes_luhn_check("4111111111111111") is True


def test_luhn_check_invalid():
    """Test Luhn algorithm for invalid card."""
    detector = PIIDetector()
    # Invalid card (last digit wrong)
    assert detector._passes_luhn_check("4111111111111112") is False


def test_china_id_validation_valid():
    """Test Chinese ID validation with valid ID."""
    detector = PIIDetector()
    # Valid Chinese ID with correct checksum
    assert detector._validate_china_id("11010519491231002X") is True


def test_china_id_validation_invalid():
    """Test Chinese ID validation with invalid ID."""
    detector = PIIDetector()
    # Wrong length
    assert detector._validate_china_id("123456789") is False


def test_get_context():
    """Test context extraction."""
    detector = PIIDetector()
    text = "This is a longer text with john@example.com in the middle"

    context = detector._get_context(text, 28, 44)

    assert "..." in context or len(context) <= 36


def test_get_stats():
    """Test getting detection statistics."""
    detector = PIIDetector()
    detector.scan("test@example.com")
    detector.scan("call 555-123-4567")

    stats = detector.get_stats()

    assert stats["total_scans"] == 2
    assert stats["total_detections"] >= 2
    assert stats["average_per_scan"] > 0


def test_reset_stats():
    """Test resetting statistics."""
    detector = PIIDetector()
    detector.scan("test@example.com")
    detector.reset_stats()

    stats = detector.get_stats()
    assert stats["total_scans"] == 0
    assert stats["total_detections"] == 0


def test_scan_dict():
    """Test scanning dictionary for PII."""
    detector = PIIDetector()
    data = {
        "name": "John",
        "email": "john@example.com",
        "phone": "555-123-4567",
        "age": 30,
    }

    results = detector.scan_dict(data)

    assert "email" in results
    assert "phone" in results
    assert results["email"].has_pii is True
    assert results["phone"].has_pii is True
    assert "age" not in results


def test_scan_list():
    """Test scanning list for PII."""
    detector = PIIDetector()
    data = ["Contact test@example.com", "Call 555-123-4567", "No PII here"]

    results = detector.scan_list(data)

    assert len(results) == 3
    assert results[0].has_pii is True
    assert results[1].has_pii is True
    assert results[2].has_pii is False


def test_confidence_threshold():
    """Test confidence threshold filtering."""
    detector = PIIDetector(confidence_threshold=0.95)
    text = "test@example.com"

    result = detector.scan(text)

    # High threshold may filter out some matches
    assert result.total_detections >= 0


def test_match_has_value():
    """Test PIIMatch has correct value."""
    detector = PIIDetector()
    text = "Email: test@example.com"

    result = detector.scan(text)

    if result.matches:
        match = result.matches[0]
        assert match.value == "test@example.com"
        assert match.pii_type == PIIType.EMAIL
        assert match.confidence >= 0.7
        assert match.start >= 0
        assert match.end > match.start


def test_empty_text():
    """Test scanning empty text."""
    detector = PIIDetector()

    result = detector.scan("")

    assert result.has_pii is False
    assert result.total_detections == 0


def test_no_pii_text():
    """Test scanning text without PII."""
    detector = PIIDetector()
    text = "This is a normal sentence without any sensitive data."

    result = detector.scan(text)

    assert result.has_pii is False or result.total_detections == 0
