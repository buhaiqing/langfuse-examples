"""Test fixtures for skill-observability-toolkit."""


import pytest


@pytest.fixture
def manifest_content():
    """Default manifest content for testing."""
    return """
name: api-expert-skill
version: 1.0.0
sop: Test SOP for validation
description: Test skill manifest
"""


@pytest.fixture
def valid_skill_content():
    """Valid skill YAML content for parse tests."""
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
      path: inputs.query
  post:
    - check: output_exists
      message: Response must be generated
      path: outputs.response

trust_score:
  enabled: true
  history_window: 30
  min_pass_rate: 0.8
"""


@pytest.fixture
def valid_skill_path(tmp_path):
    """Create a valid skill.yaml file."""
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


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test to avoid state pollution."""
    # Reset config singleton
    import skill_observability_toolkit.config as config_module
    from skill_observability_toolkit.langfuse_integration.client import LangfuseClient
    config_module._config = None

    # Reset LangfuseClient singleton
    LangfuseClient._instance = None
    LangfuseClient._langfuse = None

    yield

    # Clean up after test
    config_module._config = None
    LangfuseClient._instance = None
    LangfuseClient._langfuse = None


@pytest.fixture
def valid_manifest(valid_skill_content):
    """Parse valid skill content and return SkillManifest."""
    from skill_observability_toolkit.stop.manifest import ManifestParser
    parser = ManifestParser()
    return parser.parse(content=valid_skill_content)


@pytest.fixture
def duplicate_inputs_content():
    """YAML with duplicate input names for testing."""
    return """
sop: "1.0.0"
name: test-skill
version: "1.0.0"
description: Test skill

inputs:
  - name: data
    type: string
    description: First input
  - name: data
    type: object
    description: Duplicate name

outputs:
  - name: result
    type: string
    description: Output
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
