"""
Unit tests for ManifestParser.
"""


import pytest

from skill_observability_toolkit.stop.manifest import (
    Assertion,
    ManifestError,
    ManifestParseError,
    ManifestParser,
    ManifestValidationError,
    SkillInput,
    SkillManifest,
    SkillOutput,
    ToolReference,
    TrustScoreConfig,
)


class TestManifestParserInit:
    """Tests for ManifestParser initialization."""

    def test_init_with_no_arguments(self):
        """Initialize parser with no arguments."""
        parser = ManifestParser()
        assert parser.skill_yaml_path is None
        assert parser.manifest is None
        assert parser.errors == []
        assert parser.warnings == []

    def test_init_with_skill_yaml_path(self):
        """Initialize parser with skill_yaml_path."""
        parser = ManifestParser(skill_yaml_path="tests/fixtures/valid_skill.yaml")
        assert parser.skill_yaml_path == "tests/fixtures/valid_skill.yaml"
        assert parser.manifest is None


class TestManifestParserParse:
    """Tests for ManifestParser.parse()."""

    def test_parse_valid_skill_manifest(self, valid_skill_path: str):
        """Parse a valid skill manifest."""
        parser = ManifestParser(skill_yaml_path=valid_skill_path)
        manifest = parser.parse()

        assert isinstance(manifest, SkillManifest)
        assert manifest.name == "api-expert-skill"
        assert manifest.version == "1.0.0"
        assert len(manifest.inputs) == 1
        assert len(manifest.outputs) == 1
        assert manifest.trust_score.enabled is True

    def test_parse_content_directly(self, valid_skill_content: str):
        """Parse YAML content directly."""
        parser = ManifestParser()
        manifest = parser.parse(content=valid_skill_content)

        assert isinstance(manifest, SkillManifest)
        assert manifest.name == "api-expert-skill"

    def test_parse_no_content_or_path(self):
        """Parse with no content or path raises error."""
        parser = ManifestParser()

        with pytest.raises(ManifestParseError, match="No content or skill_yaml_path"):
            parser.parse()

    def test_parse_invalid_yaml(self):
        """Parse invalid YAML raises error."""
        parser = ManifestParser()
        invalid_yaml = """
        name: test
        version: 1.0
        this: is: invalid: yaml
        """

        with pytest.raises(ManifestParseError, match="Failed to parse YAML"):
            parser.parse(content=invalid_yaml)

    def test_parse_missing_required_field(self):
        """Parse with missing required field raises error."""
        parser = ManifestParser()
        incomplete = """
        name: test-skill
        version: 1.0.0
        description: Missing SOP
        """

        with pytest.raises(ManifestParseError, match="Missing required fields: sop"):
            parser.parse(content=incomplete)

    def test_parse_invalid_data_type(self):
        """Parse with invalid data types."""
        parser = ManifestParser()
        invalid_types = """
        name: test
        version: 123  # Should be string
        sop: |
          Test
        """

        # Should not raise immediately during parsing, but during validation
        manifest = parser.parse(content=invalid_types)
        assert manifest is not None

    def test_parse_duplicate_input_names(self, duplicate_inputs_content: str):
        """Parse with duplicate input names."""
        parser = ManifestParser()

        with pytest.raises(ManifestValidationError, match="Input parameter names must be unique"):
            parser.parse(content=duplicate_inputs_content)


class TestManifestParserValidate:
    """Tests for ManifestParser.validate()."""

    def test_validate_valid_manifest(self, valid_manifest: SkillManifest):
        """Validate a valid manifest."""
        parser = ManifestParser()
        errors = parser.validate(valid_manifest)

        assert errors == []

    def test_validate_empty_name(self, valid_manifest: SkillManifest):
        """Validate manifest with empty name."""
        valid_manifest.name = ""
        parser = ManifestParser()

        errors = parser.validate(valid_manifest)
        assert any("Skill name cannot be empty" in e for e in errors)

    def test_validate_empty_version(self, valid_manifest: SkillManifest):
        """Validate manifest with empty version."""
        valid_manifest.version = ""
        parser = ManifestParser()

        errors = parser.validate(valid_manifest)
        assert any("Skill version cannot be empty" in e for e in errors)

    def test_validate_duplicate_input_names(self, valid_manifest: SkillManifest):
        """Validate manifest with duplicate input names."""
        valid_manifest.inputs = [
            SkillInput(name="data", type="string", description="First"),
            SkillInput(name="data", type="object", description="Second"),
        ]
        parser = ManifestParser()

        errors = parser.validate(valid_manifest)
        assert any("Input parameter names must be unique" in e for e in errors)

    def test_validate_duplicate_output_names(self, valid_manifest: SkillManifest):
        """Validate manifest with duplicate output names."""
        valid_manifest.outputs = [
            SkillOutput(name="result", type="string", description="First"),
            SkillOutput(name="result", type="object", description="Second"),
        ]
        parser = ManifestParser()

        errors = parser.validate(valid_manifest)
        assert any("Output parameter names must be unique" in e for e in errors)

    def test_validate_duplicate_tool_names(self, valid_manifest: SkillManifest):
        """Validate manifest with duplicate tool names."""
        valid_manifest.tools_used = [
            ToolReference(name="tool1", version="1.0", description="First"),
            ToolReference(name="tool1", version="2.0", description="Second"),
        ]
        parser = ManifestParser()

        errors = parser.validate(valid_manifest)
        assert any("Tool names must be unique" in e for e in errors)

    def test_validate_empty_assertion_check(self, valid_manifest: SkillManifest):
        """Validate manifest with empty assertion check."""
        valid_manifest.assertions = [
            Assertion(check="", message="Test"),
        ]
        parser = ManifestParser()

        errors = parser.validate(valid_manifest)
        assert any("Assertion 'check' field is required" in e for e in errors)

    def test_validate_empty_assertion_message(self, valid_manifest: SkillManifest):
        """Validate manifest with empty assertion message."""
        valid_manifest.assertions = [
            Assertion(check="file_exists", message=""),
        ]
        parser = ManifestParser()

        errors = parser.validate(valid_manifest)
        assert any("Assertion 'message' field is required" in e for e in errors)

    def test_validate_invalid_assertion_type(self, valid_manifest: SkillManifest):
        """Validate manifest with invalid assertion type."""
        valid_manifest.assertions = [
            Assertion(check="file_exists", message="Test", type="invalid"),
        ]
        parser = ManifestParser()

        errors = parser.validate(valid_manifest)
        assert any("Assertion type must be 'pre' or 'post'" in e for e in errors)


class TestManifestParserTrustScore:
    """Tests for ManifestParser.add_trust_score()."""

    def test_add_trust_score_all_passed(self):
        """Calculate trust score when all assertions pass."""
        parser = ManifestParser()

        results = [
            {"passed": True},
            {"passed": True},
            {"passed": True},
        ]

        score = parser.add_trust_score(results)
        assert score == 1.0

    def test_add_trust_score_partial_passed(self):
        """Calculate trust score with partial passes."""
        parser = ManifestParser()

        results = [
            {"passed": True},
            {"passed": True},
            {"passed": False},
        ]

        score = parser.add_trust_score(results)
        assert score == 2.0 / 3.0

    def test_add_trust_score_none_passed(self):
        """Calculate trust score when none pass."""
        parser = ManifestParser()

        results = [
            {"passed": False},
            {"passed": False},
        ]

        score = parser.add_trust_score(results)
        assert score == 0.0

    def test_add_trust_score_empty(self):
        """Calculate trust score with no results."""
        parser = ManifestParser()

        score = parser.add_trust_score([])
        assert score == 1.0  # No assertions = perfect trust


class TestDataClasses:
    """Tests for dataclass models."""

    def test_skill_input_to_dict(self):
        """SkillInput.to_dict() conversion."""
        inp = SkillInput(
            name="test_input",
            type="string",
            description="Test",
            required=True,
            default="default_value",
        )

        result = inp.to_dict()

        assert result["name"] == "test_input"
        assert result["type"] == "string"
        assert result["description"] == "Test"
        assert result["required"] is True
        assert result["default"] == "default_value"

    def test_skill_output_to_dict(self):
        """SkillOutput.to_dict() conversion."""
        out = SkillOutput(
            name="test_output",
            type="object",
            description="Test",
            properties={"field1": "string", "field2": "integer"},
        )

        result = out.to_dict()

        assert result["name"] == "test_output"
        assert result["type"] == "object"
        assert result["properties"] == {"field1": "string", "field2": "integer"}

    def test_tool_reference_to_dict(self):
        """ToolReference.to_dict() conversion."""
        tool = ToolReference(
            name="test_tool",
            version="2.0",
            description="Test tool",
        )

        result = tool.to_dict()

        assert result["name"] == "test_tool"
        assert result["version"] == "2.0"
        assert result["description"] == "Test tool"

    def test_assertion_to_dict(self):
        """Assertion.to_dict() conversion."""
        assertion = Assertion(
            check="file_exists",
            path="${inputs.data}",
            condition="len(${inputs.data}) > 0",
            message="Data must exist",
            type="pre",
        )

        result = assertion.to_dict()

        assert result["check"] == "file_exists"
        assert result["path"] == "${inputs.data}"
        assert result["condition"] == "len(${inputs.data}) > 0"
        assert result["message"] == "Data must exist"
        assert result["type"] == "pre"

    def test_trust_score_config_to_dict(self):
        """TrustScoreConfig.to_dict() conversion."""
        config = TrustScoreConfig(
            enabled=True,
            history_window=60,
            min_pass_rate=0.9,
        )

        result = config.to_dict()

        assert result["enabled"] is True
        assert result["history_window"] == 60
        assert result["min_pass_rate"] == 0.9

    def test_skill_manifest_to_dict(self, valid_manifest: SkillManifest):
        """SkillManifest.to_dict() conversion."""
        result = valid_manifest.to_dict()

        assert result["name"] == valid_manifest.name
        assert result["version"] == valid_manifest.version
        assert isinstance(result["inputs"], list)
        assert isinstance(result["outputs"], list)
        assert isinstance(result["tools_used"], list)
        assert isinstance(result["assertions"], list)
        assert isinstance(result["trust_score"], dict)
        assert isinstance(result["metadata"], dict)


class TestExceptionClasses:
    """Tests for exception classes."""

    def test_manifest_error_is_exception(self):
        """ManifestError inherits from Exception."""
        with pytest.raises(Exception):
            raise ManifestError("Test error")

    def test_manifest_parse_error_inherits_manifest_error(self):
        """ManifestParseError inherits from ManifestError."""
        with pytest.raises(ManifestError):
            raise ManifestParseError("Parse error")

    def test_manifest_validation_error_inherits_manifest_error(self):
        """ManifestValidationError inherits from ManifestError."""
        with pytest.raises(ManifestError):
            raise ManifestValidationError("Validation error")


# Fixtures

@pytest.fixture
def valid_skill_path(tmp_path) -> str:
    """Create a valid skill manifest file."""
    content = """
sop: "1.0.0"
name: api-expert-skill
version: "1.0.0"
description: API expert skill for testing

inputs:
  - name: query
    type: string
    description: User query
    required: true

outputs:
  - name: response
    type: string
    description: API response

assertions:
  pre:
    - check: string_not_empty
      message: Input query must not be empty
  post:
    - check: output_exists
      message: Response must be generated

trust_score:
  enabled: true
"""
    yaml_file = tmp_path / "skill.yaml"
    yaml_file.write_text(content)
    return str(yaml_file)


@pytest.fixture
def valid_skill_content() -> str:
    """Valid skill YAML content for testing."""
    return """
sop: "1.0.0"
name: api-expert-skill
version: "1.0.0"
description: API expert skill for testing

inputs:
  - name: query
    type: string
    description: User query
    required: true

outputs:
  - name: response
    type: string
    description: API response

assertions:
  pre:
    - check: string_not_empty
      message: Input query must not be empty
  post:
    - check: output_exists
      message: Response must be generated

trust_score:
  enabled: true
"""
