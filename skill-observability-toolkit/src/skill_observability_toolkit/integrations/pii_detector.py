"""
PII (Personally Identifiable Information) Detector.

Provides real-time PII detection with support for multiple
data types including phone, email, SSN, credit cards, and ID numbers.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PIIType(Enum):
    """Types of PII that can be detected."""

    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    CHINA_ID = "china_id"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"


@dataclass
class PIIMatch:
    """Matched PII information."""

    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float
    context: str = ""


@dataclass
class PIIDetectionResult:
    """Result of PII detection scan."""

    text: str
    matches: list[PIIMatch] = field(default_factory=list)
    total_detections: int = 0

    @property
    def has_pii(self) -> bool:
        """Check if any PII was detected."""
        return len(self.matches) > 0

    @property
    def pii_types(self) -> list[PIIType]:
        """Get unique PII types detected."""
        return list(set(m.pii_type for m in self.matches))


# Regular expression patterns for PII detection
PII_PATTERNS: dict[PIIType, tuple[re.Pattern, str]] = {
    PIIType.EMAIL: (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "Email address pattern",
    ),
    PIIType.PHONE: (
        re.compile(
            r"(?:(?:\+|00)[17](?: |\-)?|(?:\+|00)[1-9]+(?: |\-)?|(?:\+|00)1\-[1-9]+(?: |\-)?)"
            r"?(?:\d{1,}|\(\d+\))(?:\-|\.| )?(?:\d{1,}|\(\d+\))(?:\-|\.| )?"
            r"(?:\d{1,}|\(\d+\))"
        ),
        "Phone number pattern",
    ),
    PIIType.SSN: (
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "US Social Security Number pattern (XXX-XX-XXXX)",
    ),
    PIIType.CREDIT_CARD: (
        re.compile(r"\b(?:\d{4}[- ]?){3,4}\d{4}\b"),
        "Credit card number pattern",
    ),
    PIIType.CHINA_ID: (
        re.compile(r"\b[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b"),
        "Chinese Resident ID Card pattern",
    ),
    PIIType.IP_ADDRESS: (
        re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        "IPv4 address pattern",
    ),
    PIIType.DATE_OF_BIRTH: (
        re.compile(r"\b(?:0[1-9]|1[0-2])[\/\-](?:0[1-9]|[12]\d|3[01])[\/\-](?:19|20)\d{2}\b"),
        "Date of birth pattern (MM/DD/YYYY)",
    ),
}


class PIIDetector:
    """
    Real-time PII detector for data compliance monitoring.

    Scans text for personally identifiable information using
    configurable pattern matching with confidence scoring.

    Example:
        detector = PIIDetector()
        text = "Contact john@example.com or call 123-456-7890"
        
        result = detector.scan(text)
        if result.has_pii:
            print(f"Found {result.total_detections} PII items")
            for match in result.matches:
                print(f"  - {match.pii_type.value}: {match.value}")
    """

    def __init__(self, confidence_threshold: float = 0.7):
        """
        Initialize the PII detector.

        Args:
            confidence_threshold: Minimum confidence for detection (0.0-1.0)
        """
        self.confidence_threshold = confidence_threshold
        self._scan_count: int = 0
        self._detection_count: int = 0

    def scan(self, text: str, pii_types: list[PIIType] | None = None) -> PIIDetectionResult:
        """
        Scan text for PII.

        Args:
            text: Text to scan
            pii_types: Specific PII types to detect (None = all types)

        Returns:
            PIIDetectionResult with matches
        """
        if pii_types is None:
            pii_types = list(PIIType)

        matches = []
        patterns_to_check = {t: PII_PATTERNS[t] for t in pii_types if t in PII_PATTERNS}

        for pii_type, (pattern, description) in patterns_to_check.items():
            for match in pattern.finditer(text):
                confidence = self._calculate_confidence(text, match, pii_type)

                if confidence >= self.confidence_threshold:
                    context = self._get_context(text, match.start(), match.end())
                    matches.append(
                        PIIMatch(
                            pii_type=pii_type,
                            value=match.group(),
                            start=match.start(),
                            end=match.end(),
                            confidence=confidence,
                            context=context,
                        )
                    )

        self._scan_count += 1
        self._detection_count += len(matches)

        return PIIDetectionResult(
            text=text,
            matches=matches,
            total_detections=len(matches),
        )

    def _calculate_confidence(
        self, text: str, match: re.Match, pii_type: PIIType
    ) -> float:
        """
        Calculate confidence score for a PII match.

        Args:
            text: Source text
            match: Regex match object
            pii_type: Type of PII detected

        Returns:
            Confidence score (0.0-1.0)
        """
        base_confidence = 0.8

        matched_text = match.group()

        # Boost confidence for length validation
        if pii_type == PIIType.EMAIL:
            if 6 <= len(matched_text) <= 50:
                base_confidence += 0.1
            if "." in matched_text.split("@")[1]:
                base_confidence += 0.05

        elif pii_type == PIIType.PHONE:
            digits = re.sub(r"\D", "", matched_text)
            if 10 <= len(digits) <= 15:
                base_confidence += 0.1

        elif pii_type == PIIType.SSN:
            if len(matched_text) == 11 and matched_text.count("-") == 2:
                base_confidence += 0.15

        elif pii_type == PIIType.CREDIT_CARD:
            digits = re.sub(r"\D", "", matched_text)
            if len(digits) in [13, 15, 16] and self._passes_luhn_check(digits):
                base_confidence += 0.15

        elif pii_type == PIIType.CHINA_ID:
            if len(matched_text) == 18:
                base_confidence += 0.1
            if self._validate_china_id(matched_text):
                base_confidence += 0.15

        elif pii_type == PIIType.IP_ADDRESS:
            octets = matched_text.split(".")
            if all(0 <= int(o) <= 255 for o in octets):
                base_confidence += 0.1

        return min(1.0, base_confidence)

    def _get_context(self, text: str, start: int, end: int, context_size: int = 20) -> str:
        """
        Get surrounding context for a match.

        Args:
            text: Source text
            start: Match start position
            end: Match end position
            context_size: Characters to include before/after

        Returns:
            Context string with ellipsis
        """
        ctx_start = max(0, start - context_size)
        ctx_end = min(len(text), end + context_size)

        prefix = "..." if ctx_start > 0 else ""
        suffix = "..." if ctx_end < len(text) else ""

        return prefix + text[ctx_start:ctx_end] + suffix

    def _passes_luhn_check(self, card_number: str) -> bool:
        """
        Validate credit card number using Luhn algorithm.

        Args:
            card_number: Card number digits only

        Returns:
            True if valid
        """
        digits = [int(d) for d in card_number]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]

        total = sum(odd_digits)
        for digit in even_digits:
            doubled = digit * 2
            total += doubled if doubled < 10 else doubled - 9

        return total % 10 == 0

    def _validate_china_id(self, id_number: str) -> bool:
        """
        Validate Chinese ID number checksum.

        Args:
            id_number: 18-character ID number

        Returns:
            True if valid
        """
        if len(id_number) != 18:
            return False

        coefficients = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        checksum_chars = "10X98765432"

        total = sum(int(id_number[i]) * coefficients[i] for i in range(17))
        expected = checksum_chars[total % 11]

        return id_number[17].upper() == expected

    def get_stats(self) -> dict[str, Any]:
        """
        Get detection statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_scans": self._scan_count,
            "total_detections": self._detection_count,
            "average_per_scan": (
                self._detection_count / self._scan_count if self._scan_count > 0 else 0.0
            ),
        }

    def reset_stats(self):
        """Reset detection statistics."""
        self._scan_count = 0
        self._detection_count = 0

    def scan_dict(self, data: dict[str, Any], pii_types: list[PIIType] | None = None) -> dict[str, PIIDetectionResult]:
        """
        Scan dictionary values for PII.

        Args:
            data: Dictionary to scan
            pii_types: Specific PII types to detect

        Returns:
            Dictionary of field names to detection results
        """
        results = {}

        for key, value in data.items():
            if isinstance(value, str):
                results[key] = self.scan(value, pii_types)

        return results

    def scan_list(
        self, data: list[str], pii_types: list[PIIType] | None = None
    ) -> list[PIIDetectionResult]:
        """
        Scan list of strings for PII.

        Args:
            data: List of strings to scan
            pii_types: Specific PII types to detect

        Returns:
            List of detection results
        """
        return [self.scan(text, pii_types) for text in data]
