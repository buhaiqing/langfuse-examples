"""
Schema Validator for data quality monitoring.

Provides JSON Schema validation with detailed error reporting
and real-time validation statistics.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationStatus(Enum):
    """Validation result status."""

    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"


@dataclass
class ValidationError:
    """Details of a validation error."""

    field: str
    message: str
    expected: Any = None
    actual: Any = None
    error_type: str = "validation"


@dataclass
class ValidationResult:
    """Result of schema validation."""

    status: ValidationStatus
    errors: list[ValidationError] = field(default_factory=list)
    validated_fields: int = 0
    total_fields: int = 0

    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.status == ValidationStatus.VALID

    @property
    def coverage(self) -> float:
        """Get validation coverage percentage."""
        if self.total_fields == 0:
            return 100.0
        return (self.validated_fields / self.total_fields) * 100


class SchemaValidator:
    """
    JSON Schema validator for data quality monitoring.

    Validates data against JSON Schema definitions with
    detailed error reporting and statistics tracking.

    Example:
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0}
            },
            "required": ["name"]
        }
        validator.load_schema(schema)
        
        result = validator.validate({"name": "John", "age": 30})
        if result.is_valid:
            print("Validation passed")
    """

    def __init__(self):
        """Initialize the schema validator."""
        self._schema: dict[str, Any] | None = None
        self._validation_count: int = 0
        self._valid_count: int = 0
        self._invalid_count: int = 0

    def load_schema(self, schema: dict[str, Any]):
        """
        Load JSON Schema for validation.

        Args:
            schema: JSON Schema dictionary
        """
        self._schema = schema

    def validate(self, data: Any) -> ValidationResult:
        """
        Validate data against loaded schema.

        Args:
            data: Data to validate

        Returns:
            ValidationResult with status and errors
        """
        if self._schema is None:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                errors=[ValidationError(field="_schema", message="No schema loaded")],
            )

        errors = []
        total_fields = self._count_fields(self._schema)
        validated_fields = 0

        try:
            self._validate_value(data, self._schema, "", errors, validated_fields)
            validated_fields = self._count_validated_fields(errors, total_fields)
        except Exception as e:
            errors.append(ValidationError(field="_system", message=str(e), error_type="system"))

        status = ValidationStatus.VALID if len(errors) == 0 else ValidationStatus.INVALID

        self._validation_count += 1
        if status == ValidationStatus.VALID:
            self._valid_count += 1
        else:
            self._invalid_count += 1

        return ValidationResult(
            status=status,
            errors=errors,
            validated_fields=validated_fields,
            total_fields=total_fields or 1,
        )

    def _validate_value(
        self,
        value: Any,
        schema: dict[str, Any],
        path: str,
        errors: list[ValidationError],
        validated_count: int,
    ):
        """Validate a value against schema recursively."""
        if "type" in schema:
            expected_type = schema["type"]
            if not self._check_type(value, expected_type):
                errors.append(
                    ValidationError(
                        field=path or "root",
                        message=f"Expected type {expected_type}",
                        expected=expected_type,
                        actual=type(value).__name__,
                        error_type="type",
                    )
                )
                return

        if "enum" in schema and value not in schema["enum"]:
            errors.append(
                ValidationError(
                    field=path or "root",
                    message=f"Value must be one of: {schema['enum']}",
                    expected=schema["enum"],
                    actual=value,
                    error_type="enum",
                )
            )

        if isinstance(value, dict) and "properties" in schema:
            required = schema.get("required", [])
            for prop_name in required:
                if prop_name not in value:
                    errors.append(
                        ValidationError(
                            field=f"{path}.{prop_name}" if path else prop_name,
                            message="Required field is missing",
                            error_type="required",
                        )
                    )

            for prop_name, prop_schema in schema.get("properties", {}).items():
                if prop_name in value:
                    prop_path = f"{path}.{prop_name}" if path else prop_name
                    self._validate_value(
                        value[prop_name], prop_schema, prop_path, errors, validated_count
                    )

        if isinstance(value, (int, float)) and "minimum" in schema:
            if value < schema["minimum"]:
                errors.append(
                    ValidationError(
                        field=path or "root",
                        message=f"Value must be >= {schema['minimum']}",
                        expected=f">= {schema['minimum']}",
                        actual=value,
                        error_type="minimum",
                    )
                )

        if isinstance(value, (int, float)) and "maximum" in schema:
            if value > schema["maximum"]:
                errors.append(
                    ValidationError(
                        field=path or "root",
                        message=f"Value must be <= {schema['maximum']}",
                        expected=f"<= {schema['maximum']}",
                        actual=value,
                        error_type="maximum",
                    )
                )

        if isinstance(value, str) and "minLength" in schema:
            if len(value) < schema["minLength"]:
                errors.append(
                    ValidationError(
                        field=path or "root",
                        message=f"String length must be >= {schema['minLength']}",
                        expected=f">= {schema['minLength']} characters",
                        actual=len(value),
                        error_type="minLength",
                    )
                )

        if isinstance(value, str) and "maxLength" in schema:
            if len(value) > schema["maxLength"]:
                errors.append(
                    ValidationError(
                        field=path or "root",
                        message=f"String length must be <= {schema['maxLength']}",
                        expected=f"<= {schema['maxLength']} characters",
                        actual=len(value),
                        error_type="maxLength",
                    )
                )

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected JSON Schema type."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }

        expected_python_type = type_map.get(expected_type)
        if expected_python_type is None:
            return True

        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)

        return isinstance(value, expected_python_type)

    def _count_fields(self, schema: dict[str, Any]) -> int:
        """Count total fields in schema."""
        count = 0
        if "properties" in schema:
            for prop_schema in schema["properties"].values():
                count += 1
                if isinstance(prop_schema, dict):
                    count += self._count_fields(prop_schema)
        return count

    def _count_validated_fields(
        self, errors: list[ValidationError], total_fields: int
    ) -> int:
        """Count successfully validated fields."""
        error_fields = {e.field for e in errors if e.field}
        return max(0, total_fields - len(error_fields))

    def get_stats(self) -> dict[str, Any]:
        """
        Get validation statistics.

        Returns:
            Dictionary with validation stats
        """
        success_rate = (
            (self._valid_count / self._validation_count * 100)
            if self._validation_count > 0
            else 100.0
        )

        return {
            "total_validations": self._validation_count,
            "valid_count": self._valid_count,
            "invalid_count": self._invalid_count,
            "success_rate": success_rate,
        }

    def reset_stats(self):
        """Reset validation statistics."""
        self._validation_count = 0
        self._valid_count = 0
        self._invalid_count = 0

    def validate_json_string(self, json_string: str) -> ValidationResult:
        """
        Validate a JSON string.

        Args:
            json_string: JSON string to validate

        Returns:
            ValidationResult
        """
        try:
            data = json.loads(json_string)
            return self.validate(data)
        except json.JSONDecodeError as e:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                errors=[ValidationError(field="_json", message=f"Invalid JSON: {str(e)}")],
            )
