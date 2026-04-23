"""
Unified Labels System.

This module provides a unified label schema and management system
for consistent labeling across CI → Skill → MCP layers.
"""

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LabelType(Enum):
    """Label type classification."""
    SYSTEM = "system"      # System-generated labels (e.g., trace_id)
    USER = "user"          # User-defined labels
    METRIC = "metric"      # Metric labels (e.g., duration_ms)
    ENVIRONMENT = "env"    # Environment labels (e.g., environment=production)


class LabelValidationLevel(Enum):
    """Label validation strictness."""
    STRICT = "strict"       # Validate all fields
    PERMISSIVE = "permissive"  # Allow optional fields


@dataclass
class LabelSchema:
    """Label schema definition."""
    name: str
    label_type: LabelType
    description: str = ""
    required: bool = False
    pattern: str | None = None
    allowed_values: list[str] | None = None
    max_length: int = 255
    examples: list[str] = field(default_factory=list)

    def validate(self, value: str, level: LabelValidationLevel = LabelValidationLevel.STRICT) -> bool:
        """
        Validate label value against schema.

        Args:
            value: Label value to validate
            level: Validation strictness

        Returns:
            True if valid, False otherwise
        """
        # Check max length
        if len(value) > self.max_length:
            return False

        # Check pattern if defined
        if self.pattern:
            if not re.match(self.pattern, value):
                return False

        # Check allowed values if defined
        if self.allowed_values:
            if value not in self.allowed_values:
                return False

        # Check required
        if self.required and not value:
            return False

        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "label_type": self.label_type.value,
            "description": self.description,
            "required": self.required,
            "pattern": self.pattern,
            "allowed_values": self.allowed_values,
            "max_length": self.max_length,
            "examples": self.examples,
        }


@dataclass
class UnifiedLabel:
    """A unified label instance."""
    key: str
    value: str
    label_type: LabelType = LabelType.USER
    description: str = ""
    meta: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "key": self.key,
            "value": self.value,
            "type": self.label_type.value,
        }

        if self.description:
            result["description"] = self.description

        if self.meta:
            result["meta"] = self.meta

        return result


class LabelManager:
    """
    Manager for unified labels.

    Provides functionality to:
    - Register label schemas
    - Validate labels
    - Apply labels to traces/spans
    - Generate label consistency reports
    """

    # Default label schemas
    DEFAULT_SCHEMAS: dict[str, LabelSchema] = {
        "service": LabelSchema(
            name="service",
            label_type=LabelType.SYSTEM,
            description="Service name",
            required=True,
            pattern=r'^[a-z][a-z0-9-]*[a-z0-9]$',
            max_length=64,
            examples=["auth-service", "payment-gateway"],
        ),
        "version": LabelSchema(
            name="version",
            label_type=LabelType.SYSTEM,
            description="Service version",
            required=True,
            pattern=r'^\d+\.\d+\.\d+$',
            max_length=20,
            examples=["1.0.0", "2.3.1"],
        ),
        "environment": LabelSchema(
            name="environment",
            label_type=LabelType.ENVIRONMENT,
            description="Deployment environment",
            required=True,
            allowed_values=["development", "staging", "production"],
            examples=["production"],
        ),
        "team": LabelSchema(
            name="team",
            label_type=LabelType.USER,
            description="Owning team",
            required=False,
            max_length=64,
            examples=["platform", "backend", "data"],
        ),
        "priority": LabelSchema(
            name="priority",
            label_type=LabelType.METRIC,
            description="Priority level",
            required=False,
            allowed_values=["low", "medium", "high", "critical"],
            examples=["high"],
        ),
        "region": LabelSchema(
            name="region",
            label_type=LabelType.ENVIRONMENT,
            description="Deployment region",
            required=False,
            pattern=r'^[a-z]{2}-[a-z]+-\d+$',
            max_length=32,
            examples=["us-east-1", "eu-west-2"],
        ),
    }

    def __init__(self):
        """Initialize the label manager."""
        self._schemas: dict[str, LabelSchema] = self.DEFAULT_SCHEMAS.copy()
        self._labels: dict[str, UnifiedLabel] = {}
        self._validation_errors: list[str] = []

    def register_schema(self, schema: LabelSchema) -> "LabelManager":
        """
        Register a new label schema.

        Args:
            schema: Label schema to register

        Returns:
            Self for method chaining
        """
        self._schemas[schema.name] = schema
        return self

    def unregister_schema(self, name: str) -> "LabelManager":
        """
        Remove a label schema.

        Args:
            name: Name of schema to remove

        Returns:
            Self for method chaining
        """
        if name in self._schemas:
            del self._schemas[name]
        return self

    def validate_label(self, key: str, value: str) -> bool:
        """
        Validate a label against its schema.

        Args:
            key: Label key
            value: Label value

        Returns:
            True if valid
        """
        schema = self._schemas.get(key)

        if not schema:
            # No schema defined, allow but log warning
            return True

        is_valid = schema.validate(value)

        if not is_valid:
            self._validation_errors.append(
                f"Label '{key}={value}' validation failed"
            )

        return is_valid

    def add_label(
        self,
        key: str,
        value: str,
        label_type: LabelType = LabelType.USER,
        description: str = "",
        meta: dict[str, str] | None = None,
    ) -> bool:
        """
        Add a label.

        Args:
            key: Label key
            value: Label value
            label_type: Label type
            description: Label description
            meta: Additional metadata

        Returns:
            True if added successfully
        """
        # Validate
        if not self.validate_label(key, value):
            return False

        # Add label
        self._labels[key] = UnifiedLabel(
            key=key,
            value=value,
            label_type=label_type,
            description=description,
            meta=meta or {},
        )

        return True

    def remove_label(self, key: str) -> bool:
        """
        Remove a label.

        Args:
            key: Label key

        Returns:
            True if removed
        """
        if key in self._labels:
            del self._labels[key]
            return True
        return False

    def get_label(self, key: str) -> UnifiedLabel | None:
        """
        Get a label by key.

        Args:
            key: Label key

        Returns:
            Label or None
        """
        return self._labels.get(key)

    def get_all_labels(self) -> dict[str, UnifiedLabel]:
        """
        Get all labels.

        Returns:
            Dictionary of all labels
        """
        return self._labels.copy()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert all labels to dictionary.

        Returns:
            Dictionary with all labels
        """
        return {
            key: label.to_dict()
            for key, label in self._labels.items()
        }

    def apply_to_trace(self, trace_id: str, labels: dict[str, str] | None = None) -> bool:
        """
        Apply labels to a trace.

        Args:
            trace_id: Trace ID to apply labels to
            labels: Labels to apply

        Returns:
            True if applied successfully
        """
        # TODO: Implement trace label application
        return True

    def apply_to_span(self, trace_id: str, span_id: str, labels: dict[str, str] | None = None) -> bool:
        """
        Apply labels to a span.

        Args:
            trace_id: Trace ID
            span_id: Span ID
            labels: Labels to apply

        Returns:
            True if applied successfully
        """
        # TODO: Implement span label application
        return True

    def get_validation_errors(self) -> list[str]:
        """Get validation errors."""
        return self._validation_errors.copy()

    def clear_validation_errors(self):
        """Clear validation errors."""
        self._validation_errors = []

    def generate_consistency_report(self) -> dict[str, Any]:
        """
        Generate a label consistency report.

        Returns:
            Report dictionary
        """
        report = {
            "total_labels": len(self._labels),
            "label_types": {},
            "validation_errors": len(self._validation_errors),
        }

        # Count by type
        for label in self._labels.values():
            label_type = label.label_type.value
            report["label_types"][label_type] = report["label_types"].get(label_type, 0) + 1

        return report


# Global label manager instance
_label_manager = LabelManager()


def register_schema(schema: LabelSchema) -> LabelManager:
    """Register a label schema (convenience function)."""
    return _label_manager.register_schema(schema)


def validate_label(key: str, value: str) -> bool:
    """Validate a label (convenience function)."""
    return _label_manager.validate_label(key, value)


def add_label(
    key: str,
    value: str,
    label_type: LabelType = LabelType.USER,
    description: str = "",
) -> bool:
    """Add a label (convenience function)."""
    return _label_manager.add_label(key, value, label_type, description)


def get_all_labels() -> dict[str, UnifiedLabel]:
    """Get all labels (convenience function)."""
    return _label_manager.get_all_labels()


def generate_consistency_report() -> dict[str, Any]:
    """Generate consistency report (convenience function)."""
    return _label_manager.generate_consistency_report()


def get_common_labels() -> dict[str, str]:
    """Get commonly used labels."""
    return {
        "service": os.getenv("SERVICE_NAME", "unknown"),
        "version": os.getenv("SERVICE_VERSION", "0.0.0"),
        "environment": os.getenv("ENVIRONMENT", "development"),
    }
