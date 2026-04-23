"""
CLI: Initialize Skill Project.

This module provides the 'stop init' command to create a new Skill project.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(name="init", help="Initialize a new Skill project.")


def create_skill_structure(project_dir: Path) -> None:
    """Create the default Skill project structure."""
    # Create directories
    dirs = [
        "src",
        "tests",
        "examples",
        ".sop/logs",
    ]
    
    for dir_name in dirs:
        (project_dir / dir_name).mkdir(parents=True, exist_ok=True)


def create_pyproject_toml(project_dir: Path) -> None:
    """Create pyproject.toml file."""
    content = """[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "my-skill"
version = "0.1.0"
description = "A Skill implementation with STOP Protocol"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "langfuse>=2.0.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0",
    "ruff>=0.0.292",
    "mypy>=1.0",
]

[tool.black]
line-length = 100
target-version = ['py310', 'py311', 'py312']

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "W", "F", "I", "B", "C4", "UP"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
check_untyped_defs = true
no_implicit_optional = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --no-cov"
"""
    
    (project_dir / "pyproject.toml").write_text(content)


def create_skill_yaml(project_dir: Path) -> None:
    """Create skill.yaml manifest file."""
    content = """# Skill manifest for STOP Protocol
# Reference: https://agentskills.io/docs/skill-manifest

sop: "1.0.0"
name: my-skill
version: "0.1.0"
description: "My first Skill implementation"

inputs:
  - name: query
    type: string
    required: true
    description: "User query or input"

outputs:
  - name: response
    type: string
    description: "Generated response"
    guaranteed: true

tools_used:
  - read_file
  - web_search
  - code_execution

side_effects:
  - type: filesystem
    access: read
    paths:
      - "src/data"
    description: "Read reference data"

observability:
  level: "L2"
  langfuse_integration: true
  metrics_enabled: true

assertions:
  pre:
    - check: "string_not_empty"
      value: "${inputs.query}"
      message: "Query must not be empty"
  
  post:
    - check: "output_exists"
      field: "response"
      message: "Response field must exist"
    
    - check: "string_not_empty"
      value: "${outputs.response}"
      message: "Response must not be empty"
"""
    
    (project_dir / "skill.yaml").write_text(content)


def create_main_py(project_dir: Path) -> None:
    """Create main.py entry point."""
    content = '''"""Skill entry point."""

from skill_observability_toolkit import trace_skill_execution, trace_tool_call


@trace_skill_execution(skill_name="my-skill", version="0.1.0")
def execute_skill(query: str) -> dict:
    """Execute the skill with tracing."""
    # Your skill logic here
    result = {
        "query": query,
        "response": f"Response to: {query}",
    }
    
    return result


@trace_tool_call(tool_name="dummy_tool")
def dummy_tool(input_data: str) -> str:
    """Dummy tool for demonstration."""
    return f"Result: {input_data}"


if __name__ == "__main__":
    # Example usage
    result = execute_skill("What is AI?")
    print(result)
'''
    
    (project_dir / "src" / "main.py").write_text(content)


def create_readme_md(project_dir: Path) -> None:
    """Create README.md file."""
    content = """# My Skill

A Skill implementation using STOP Protocol.

## Installation

```bash
pip install -e .
```

## Usage

```python
from main import execute_skill

result = execute_skill("Your query here")
print(result)
```

## Testing

```bash
pytest
```

## References

- [STOP Protocol](https://agentskills.io/docs)
"""
    
    (project_dir / "README.md").write_text(content)


@app.command()
def init(
    project_name: str = typer.Argument(..., help="Name of the project"),
    output_dir: str = typer.Option(".", help="Output directory"),
):
    """Initialize a new Skill project."""
    project_dir = Path(output_dir) / project_name
    
    if project_dir.exists():
        print(f"❌ Project directory already exists: {project_dir}")
        raise typer.Exit(code=1)
    
    # Create structure
    create_skill_structure(project_dir)
    
    # Create files
    create_pyproject_toml(project_dir)
    create_skill_yaml(project_dir)
    create_main_py(project_dir)
    create_readme_md(project_dir)
    
    print(f"✅ Skill project initialized: {project_dir}")
    print(f"📁 Project structure created")
    print(f"📄 skill.yaml manifest created")
    print(f"📝 main.py entry point created")
    print(f"📚 README.md created")
    print(f"\nNext steps:")
    print(f"  cd {project_name}")
    print(f"  pip install -e .")
    print(f"  typer run src/main.py")


if __name__ == "__main__":
    app()
