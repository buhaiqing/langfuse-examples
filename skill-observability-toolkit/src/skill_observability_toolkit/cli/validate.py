"""
CLI: Validate Skill Manifest.

This module provides the 'stop validate' command to validate skill.yaml files.
"""

import sys
from pathlib import Path

import typer

from skill_observability_toolkit.stop.manifest import ManifestParser

app = typer.Typer(name="validate", help="Validate a Skill manifest.")


def validate_manifest(manifest_path: Path) -> tuple[bool, list[str]]:
    """
    Validate a skill.yaml manifest file.

    Args:
        manifest_path: Path to skill.yaml

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Check file exists
    if not manifest_path.exists():
        return False, [f"Manifest file not found: {manifest_path}"]

    # Parse manifest
    parser = ManifestParser()

    try:
        manifest = parser.load(str(manifest_path))
    except Exception as e:
        return False, [f"Failed to parse manifest: {e}"]

    # Validate required fields
    required_fields = ["sop", "name", "version", "description", "inputs", "outputs"]

    for field in required_fields:
        if not getattr(manifest, field, None):
            errors.append(f"Missing required field: {field}")

    # Validate name format (kebab-case)
    if manifest.name:
        import re
        if not re.match(r'^[a-z]+(-[a-z]+)*$', manifest.name):
            errors.append(
                f"Invalid name format: '{manifest.name}'. "
                f"Must be kebab-case (e.g., 'my-skill')"
            )

    # Validate version format (semver)
    if manifest.version:
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', manifest.version):
            errors.append(
                f"Invalid version format: '{manifest.version}'. "
                f"Must be semver (e.g., '1.0.0')"
            )

    # Validate inputs
    if manifest.inputs:
        for i, input_field in enumerate(manifest.inputs):
            if not input_field.name:
                errors.append(f"Input {i}: Missing 'name' field")

            if not input_field.type:
                errors.append(f"Input {i}: Missing 'type' field")

            # Check required inputs have constraints
            if input_field.required and not input_field.constraints:
                errors.append(
                    f"Required input '{input_field.name}' should have constraints"
                )

    # Validate outputs
    if manifest.outputs:
        for i, output_field in enumerate(manifest.outputs):
            if not output_field.name:
                errors.append(f"Output {i}: Missing 'name' field")

            if not output_field.type:
                errors.append(f"Output {i}: Missing 'type' field")

    # Check for assertions (recommended)
    if not manifest.assertions:
        errors.append(
            "No assertions defined. "
            "Recommended: Define pre/post assertions for quality validation"
        )

    is_valid = len(errors) == 0
    return is_valid, errors


@app.command()
def validate(
    manifest_path: str = typer.Option("skill.yaml", help="Path to skill.yaml"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """
    Validate a Skill manifest file.

    Checks:
    - Required fields present
    - Name format (kebab-case)
    - Version format (semver)
    - Input/output definitions
    - Assertions (recommended)
    """
    path = Path(manifest_path)

    if verbose:
        print(f"ℹ️  Validating: {path}")

    is_valid, errors = validate_manifest(path)

    if is_valid:
        print("✅ Manifest is valid!")

        # Load and display basic info
        parser = ManifestParser()
        try:
            manifest = parser.load(str(path))
            print("\n📊 Manifest Info:")
            print(f"   Name: {manifest.name}")
            print(f"   Version: {manifest.version}")
            print(f"   Description: {manifest.description}")

            if manifest.assertions:
                print(f"   Assertions: {len(manifest.assertions.get('pre', []))} pre, "
                      f"{len(manifest.assertions.get('post', []))} post")

        except Exception as e:
            if verbose:
                print(f"⚠️  Could not load manifest info: {e}")

        return 0

    else:
        print(f"❌ Manifest has {len(errors)} error(s):\n")

        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")

        if verbose:
            print(f"\n   Full manifest path: {path.absolute()}")

        return 1


@app.command()
def check(
    manifest_path: str = typer.Option("skill.yaml", help="Path to skill.yaml"),
):
    """
    Alias for 'validate' command.
    """
    return validate(manifest_path=manifest_path)


if __name__ == "__main__":
    result = app()
    sys.exit(result if isinstance(result, int) else 0)
