"""Tests for Schema Validator."""

import pytest
from skill_observability_toolkit.integrations.schema_validator import (
    SchemaValidator,
    ValidationError,
    ValidationResult,
    ValidationStatus,
)


def test_validation_result_is_valid():
    """Test ValidationResult.is_valid property."""
    result = ValidationResult(status=ValidationStatus.VALID)
    assert result.is_valid is True

    result = ValidationResult(status=ValidationStatus.INVALID)
    assert result.is_valid is False


def test_validation_result_coverage():
    """Test ValidationResult.coverage property."""
    result = ValidationResult(status=ValidationStatus.VALID, validated_fields=10, total_fields=10)
    assert result.coverage == 100.0

    result = ValidationResult(status=ValidationStatus.INVALID, validated_fields=8, total_fields=10)
    assert result.coverage == 80.0

    result = ValidationResult(status=ValidationStatus.VALID, total_fields=0)
    assert result.coverage == 100.0


def test_schema_validator_initialization():
    """Test SchemaValidator can be initialized."""
    validator = SchemaValidator()
    assert validator is not None
    assert validator._schema is None


def test_validate_without_schema():
    """Test validation fails when no schema loaded."""
    validator = SchemaValidator()
    result = validator.validate({"name": "John"})

    assert result.status == ValidationStatus.ERROR
    assert len(result.errors) > 0


def test_load_schema():
    """Test loading JSON Schema."""
    validator = SchemaValidator()
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}

    validator.load_schema(schema)
    assert validator._schema == schema


def test_validate_valid_object():
    """Test validating valid object."""
    validator = SchemaValidator()
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
    }
    validator.load_schema(schema)

    result = validator.validate({"name": "John", "age": 30})

    assert result.status == ValidationStatus.VALID
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_validate_invalid_type():
    """Test validation catches wrong type."""
    validator = SchemaValidator()
    schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
    validator.load_schema(schema)

    result = validator.validate({"age": "thirty"})

    assert result.status == ValidationStatus.INVALID
    assert len(result.errors) > 0
    assert result.errors[0].error_type == "type"


def test_validate_required_field_missing():
    """Test validation catches missing required field."""
    validator = SchemaValidator()
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }
    validator.load_schema(schema)

    result = validator.validate({})

    assert result.status == ValidationStatus.INVALID
    assert any(e.error_type == "required" for e in result.errors)


def test_validate_minimum_constraint():
    """Test validation enforces minimum value."""
    validator = SchemaValidator()
    schema = {"type": "number", "minimum": 0}
    validator.load_schema(schema)

    result = validator.validate(-5)

    assert result.status == ValidationStatus.INVALID
    assert any(e.error_type == "minimum" for e in result.errors)


def test_validate_maximum_constraint():
    """Test validation enforces maximum value."""
    validator = SchemaValidator()
    schema = {"type": "number", "maximum": 100}
    validator.load_schema(schema)

    result = validator.validate(150)

    assert result.status == ValidationStatus.INVALID
    assert any(e.error_type == "maximum" for e in result.errors)


def test_validate_string_min_length():
    """Test validation enforces minimum string length."""
    validator = SchemaValidator()
    schema = {"type": "string", "minLength": 3}
    validator.load_schema(schema)

    result = validator.validate("ab")

    assert result.status == ValidationStatus.INVALID
    assert any(e.error_type == "minLength" for e in result.errors)


def test_validate_string_max_length():
    """Test validation enforces maximum string length."""
    validator = SchemaValidator()
    schema = {"type": "string", "maxLength": 5}
    validator.load_schema(schema)

    result = validator.validate("toolong")

    assert result.status == ValidationStatus.INVALID
    assert any(e.error_type == "maxLength" for e in result.errors)


def test_validate_enum_constraint():
    """Test validation enforces enum values."""
    validator = SchemaValidator()
    schema = {"type": "string", "enum": ["red", "green", "blue"]}
    validator.load_schema(schema)

    result = validator.validate("yellow")

    assert result.status == ValidationStatus.INVALID
    assert any(e.error_type == "enum" for e in result.errors)


def test_get_stats():
    """Test getting validation statistics."""
    validator = SchemaValidator()
    schema = {"type": "string"}
    validator.load_schema(schema)

    validator.validate("valid")
    validator.validate("valid")
    validator.validate(123)  # invalid

    stats = validator.get_stats()

    assert stats["total_validations"] == 3
    assert stats["valid_count"] == 2
    assert stats["invalid_count"] == 1
    assert abs(stats["success_rate"] - 66.67) < 0.1


def test_reset_stats():
    """Test resetting statistics."""
    validator = SchemaValidator()
    schema = {"type": "string"}
    validator.load_schema(schema)

    validator.validate("test")
    validator.reset_stats()

    stats = validator.get_stats()
    assert stats["total_validations"] == 0
    assert stats["valid_count"] == 0


def test_validate_json_string_valid():
    """Test validating valid JSON string."""
    validator = SchemaValidator()
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    validator.load_schema(schema)

    result = validator.validate_json_string('{"name": "John"}')

    assert result.status == ValidationStatus.VALID


def test_validate_json_string_invalid():
    """Test validating invalid JSON string."""
    validator = SchemaValidator()
    result = validator.validate_json_string('{"invalid json}')

    assert result.status == ValidationStatus.ERROR
    assert any("_json" in e.field for e in result.errors)


def test_validate_nested_object():
    """Test validating nested object structure."""
    validator = SchemaValidator()
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
                "required": ["name"],
            }
        },
    }
    validator.load_schema(schema)

    result = validator.validate({"user": {"name": "John"}})

    assert result.status == ValidationStatus.VALID


def test_validate_array_type():
    """Test validating array type."""
    validator = SchemaValidator()
    schema = {"type": "array"}
    validator.load_schema(schema)

    result = validator.validate([1, 2, 3])
    assert result.status == ValidationStatus.VALID

    result = validator.validate("not an array")
    assert result.status == ValidationStatus.INVALID


def test_validate_boolean_type():
    """Test validating boolean type."""
    validator = SchemaValidator()
    schema = {"type": "boolean"}
    validator.load_schema(schema)

    result = validator.validate(True)
    assert result.status == ValidationStatus.VALID

    result = validator.validate("true")
    assert result.status == ValidationStatus.INVALID


def test_validate_null_type():
    """Test validating null type."""
    validator = SchemaValidator()
    schema = {"type": "null"}
    validator.load_schema(schema)

    result = validator.validate(None)
    assert result.status == ValidationStatus.VALID

    result = validator.validate("not null")
    assert result.status == ValidationStatus.INVALID
