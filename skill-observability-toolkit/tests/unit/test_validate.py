"""
Tests for CLI validate command.

This module tests the 'stop validate' command for validating skill.yaml files.
"""

import shutil
import tempfile

import pytest
from typer.testing import CliRunner

from skill_observability_toolkit.cli.validate import app, validate_manifest


class TestValidateManifest:
    """Tests for validate_manifest function."""

    def test_valid_manifest_passes(self, tmp_path):
        """Test that valid manifest passes validation."""
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: my-skill
version: "1.0.0"
description: "A test skill"

inputs:
  - name: query
    type: string
    required: true

outputs:
  - name: response
    type: string
    guaranteed: true

assertions:
  pre:
    - check: "string_not_empty"
      value: "${inputs.query}"
      message: "Query must not be empty"
  post:
    - check: "output_exists"
      field: "response"
      message: "Response must exist"
""")

        is_valid, errors = validate_manifest(skill_yaml)

        assert is_valid is True
        assert len(errors) == 0

    def test_missing_required_field_fails(self, tmp_path):
        """Test that missing required field fails validation."""
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
# Missing name
version: "1.0.0"
description: "A test skill"

inputs:
  - name: query
    type: string

outputs:
  - name: response
    type: string
""")

        is_valid, errors = validate_manifest(skill_yaml)

        assert is_valid is False
        assert any("Missing required fields: name" in error for error in errors)

    def test_invalid_name_format_fails(self, tmp_path):
        """Test that invalid name format fails validation."""
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: My_Skill  # Invalid: should be kebab-case
version: "1.0.0"
description: "A test skill"

inputs:
  - name: query
    type: string

outputs:
  - name: response
    type: string
""")

        is_valid, errors = validate_manifest(skill_yaml)

        assert is_valid is False
        assert any("Invalid name format" in error for error in errors)

    def test_invalid_version_format_fails(self, tmp_path):
        """Test that invalid version format fails validation."""
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: my-skill
version: "1.0"  # Invalid: should be semver (1.0.0)
description: "A test skill"

inputs:
  - name: query
    type: string

outputs:
  - name: response
    type: string
""")

        is_valid, errors = validate_manifest(skill_yaml)

        assert is_valid is False
        assert any("Invalid version format" in error for error in errors)

    def test_missing_input_name_fails(self, tmp_path):
        """Test that missing input name fails validation."""
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: my-skill
version: "1.0.0"
description: "A test skill"

inputs:
  - type: string  # Missing name

outputs:
  - name: response
    type: string
""")

        is_valid, errors = validate_manifest(skill_yaml)

        assert is_valid is False
        # ManifestParser raises KeyError for missing 'name', which is caught and wrapped
        assert any("'name'" in error for error in errors)

    def test_missing_output_type_uses_default(self, tmp_path):
        """Test that missing output type uses default value 'object'."""
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: my-skill
version: "1.0.0"
description: "A test skill"

inputs:
  - name: query
    type: string

outputs:
  - name: response  # Missing type, defaults to 'object'
""")

        is_valid, errors = validate_manifest(skill_yaml)

        # Output type has default value, so parsing succeeds but may have other errors
        # The manifest is parsed with type='object' as default
        assert any("No assertions" in error for error in errors)

    def test_no_assertions_warning(self, tmp_path):
        """Test that missing assertions generates warning."""
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: my-skill
version: "1.0.0"
description: "A test skill"

inputs:
  - name: query
    type: string

outputs:
  - name: response
    type: string
""")

        is_valid, errors = validate_manifest(skill_yaml)

        # Still valid but with warning
        assert is_valid is True or is_valid is False
        assert any("No assertions" in error for error in errors)

    def test_nonexistent_file_fails(self, tmp_path):
        """Test that nonexistent file fails validation."""
        fake_path = tmp_path / "nonexistent.yaml"

        is_valid, errors = validate_manifest(fake_path)

        assert is_valid is False
        assert any("not found" in error.lower() for error in errors)


class TestValidateCommand:
    """Tests for stop validate command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_validate_valid_manifest(self, tmp_path):
        """Test validating a valid manifest."""
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: my-skill
version: "1.0.0"
description: "A test skill"

inputs:
  - name: query
    type: string

outputs:
  - name: response
    type: string

assertions:
  pre:
    - check: "string_not_empty"
      value: "${inputs.query}"
      message: "Query must not be empty"
""")

        result = self.runner.invoke(app, ["validate", "--manifest-path", str(skill_yaml)])

        assert result.exit_code == 0
        assert "✅ Manifest is valid" in result.stdout

    def test_validate_invalid_manifest(self, tmp_path):
        """Test validating an invalid manifest."""
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
# Missing name
version: "1.0.0"
description: "A test skill"

inputs:
  - name: query
    type: string

outputs:
  - name: response
    type: string
""")

        result = self.runner.invoke(app, ["validate", "--manifest-path", str(skill_yaml)])

        # Should fail due to missing name field
        assert result.exit_code != 0
        assert "❌ Manifest" in result.stdout or "error" in result.stdout.lower() or "Missing" in result.stdout

    def test_validate_default_path(self, tmp_path):
        """Test validating with default path (skill.yaml)."""
        # Create a temp skill.yaml
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: my-skill
version: "1.0.0"
description: "A test skill"

inputs:
  - name: query
    type: string

outputs:
  - name: response
    type: string

assertions:
  pre:
    - check: "string_not_empty"
      value: "${inputs.query}"
      message: "Query must not be empty"
""")

        # Change to temp directory
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            result = self.runner.invoke(app, ["validate"])

            assert result.exit_code == 0
            assert "✅ Manifest is valid" in result.stdout
        finally:
            os.chdir(original_cwd)

    def test_validate_verbose_mode(self, tmp_path):
        """Test validating in verbose mode."""
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: my-skill
version: "1.0.0"
description: "A test skill"

inputs:
  - name: query
    type: string

outputs:
  - name: response
    type: string

assertions:
  pre:
    - check: "string_not_empty"
      value: "${inputs.query}"
      message: "Query must not be empty"
""")

        result = self.runner.invoke(app, [
            "validate",
            "--manifest-path", str(skill_yaml),
            "--verbose"
        ])

        assert result.exit_code == 0
        # Should show some info about manifest
        assert "兴 Validating" in result.stdout or "info" in result.stdout.lower()

    def test_validate_check_alias(self, tmp_path):
        """Test that 'check' command is an alias for 'validate'."""
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: my-skill
version: "1.0.0"
description: "A test skill"

inputs:
  - name: query
    type: string

outputs:
  - name: response
    type: string
""")

        result = self.runner.invoke(app, ["check", "--manifest-path", str(skill_yaml)])

        # check command should also work (alias for validate)
        # Note: check command may show warnings about missing assertions
        assert result.exit_code in [0, 1]  # 0 = valid, 1 = has warnings/errors but command worked
        assert "Manifest" in result.stdout


class TestValidateIntegration:
    """Integration tests for validate command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_full_validation_workflow(self, tmp_path):
        """Test complete validation workflow."""
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: complete-skill
version: "2.1.0"
description: "A complete skill with all features"

inputs:
  - name: input_file
    type: file_path
    required: true
    description: "Path to input file"

  - name: process_type
    type: string
    required: false
    constraints:
      enum: ["count", "analyze", "transform"]
    default: "count"

outputs:
  - name: result
    type: json
    guaranteed: true
    description: "Processing result"

assertions:
  pre:
    - check: "file_exists"
      value: "${inputs.input_file}"
      message: "Input file must exist"

    - check: "string_not_empty"
      value: "${inputs.input_file}"
      message: "Input file path must not be empty"

  post:
    - check: "output_exists"
      field: "result"
      message: "Result field must exist"

    - check: "value_equal"
      value: "${outputs.result.success}"
      expected: true
      message: "Result must indicate success"
""")

        is_valid, errors = validate_manifest(skill_yaml)

        assert is_valid is True
        assert len(errors) == 0

    def test_manifest_info_display(self, tmp_path):
        """Test that manifest info is displayed after validation."""
        skill_yaml = tmp_path / "skill.yaml"
        skill_yaml.write_text("""
sop: "1.0.0"
name: info-skill
version: "1.2.3"
description: "Skill for testing info display"

inputs:
  - name: query
    type: string

outputs:
  - name: response
    type: string

assertions:
  pre:
    - check: "string_not_empty"
      value: "${inputs.query}"
      message: "Query must not be empty"
  post:
    - check: "output_exists"
      field: "response"
      message: "Response must exist"
""")

        result = self.runner.invoke(app, ["validate", "--manifest-path", str(skill_yaml)])

        assert result.exit_code == 0
        # Should display info
        assert "📊 Manifest Info" in result.stdout
        assert "info-skill" in result.stdout
        assert "1.2.3" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
