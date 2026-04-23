"""Test fixtures for skill-observability-toolkit."""

import pytest
from pathlib import Path


@pytest.fixture
def manifest_content():
    """Default manifest content for testing."""
    return """
name: test-skill
version: 1.0.0
sop: Test SOP for validation
description: Test skill manifest
"""


@pytest.fixture
def valid_manifest_yaml(tmp_path):
    """Create a valid skill.yaml file."""
    content = """
name: api-expert-skill
version: 1.0.0
description: API expert skill for testing
sop: |
  Step 1: Analyze input
  Step 2: Process request
  Step 3: Return response

inputs:
  - name: query
    type: string
    description: User query
    required: true

outputs:
  - name: response
    type: string
    description: API response

trust_score:
  enabled: true
  history_window: 30
  min_pass_rate: 0.8
"""
    yaml_file = tmp_path / "skill.yaml"
    yaml_file.write_text(content)
    return str(yaml_file)
