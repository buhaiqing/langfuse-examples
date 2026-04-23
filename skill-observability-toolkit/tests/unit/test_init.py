"""
Tests for CLI init command.

This module tests the 'stop init' command for creating new Skill projects.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from typer.testing import CliRunner

from skill_observability_toolkit.cli.init import app


class TestInitCommand:
    """Tests for stop init command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.test_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_init_creates_project_structure(self):
        """Test that init creates the correct project structure."""
        project_name = "test-skill"
        project_dir = Path(self.test_dir) / project_name
        
        result = self.runner.invoke(app, [project_name, "--output-dir", self.test_dir])
        
        assert result.exit_code == 0
        assert f"✅ Skill project initialized: {project_dir}" in result.stdout
        
        # Check structure
        assert (project_dir / "src").exists()
        assert (project_dir / "tests").exists()
        assert (project_dir / "examples").exists()
        assert (project_dir / ".sop/logs").exists()
    
    def test_init_creates_pyproject_toml(self):
        """Test that init creates pyproject.toml."""
        project_name = "test-skill"
        project_dir = Path(self.test_dir) / project_name
        
        self.runner.invoke(app, [project_name, "--output-dir", self.test_dir])
        
        pyproject_path = project_dir / "pyproject.toml"
        assert pyproject_path.exists()
        
        content = pyproject_path.read_text()
        assert "[build-system]" in content
        assert 'name = "my-skill"' in content
        assert "langfuse>=2.0.0" in content
        assert "pytest>=7.0" in content
    
    def test_init_creates_skill_yaml(self):
        """Test that init creates skill.yaml manifest."""
        project_name = "test-skill"
        project_dir = Path(self.test_dir) / project_name
        
        self.runner.invoke(app, [project_name, "--output-dir", self.test_dir])
        
        skill_yaml_path = project_dir / "skill.yaml"
        assert skill_yaml_path.exists()
        
        content = skill_yaml_path.read_text()
        assert "sop: \"1.0.0\"" in content
        assert "name: my-skill" in content
        assert "version: \"0.1.0\"" in content
        assert "pre:" in content  # Assertions
        assert "post:" in content
    
    def test_init_creates_main_py(self):
        """Test that init creates main.py entry point."""
        project_name = "test-skill"
        project_dir = Path(self.test_dir) / project_name
        
        self.runner.invoke(app, [project_name, "--output-dir", self.test_dir])
        
        main_py_path = project_dir / "src" / "main.py"
        assert main_py_path.exists()
        
        content = main_py_path.read_text()
        assert "from skill_observability_toolkit" in content
        assert "trace_skill_execution" in content
        assert "def execute_skill" in content
    
    def test_init_creates_readme(self):
        """Test that init creates README.md."""
        project_name = "test-skill"
        project_dir = Path(self.test_dir) / project_name
        
        self.runner.invoke(app, [project_name, "--output-dir", self.test_dir])
        
        readme_path = project_dir / "README.md"
        assert readme_path.exists()
        
        content = readme_path.read_text()
        assert "# My Skill" in content
    
    def test_init_fails_when_directory_exists(self):
        """Test that init fails when directory already exists."""
        project_name = "test-skill"
        project_dir = Path(self.test_dir) / project_name
        project_dir.mkdir()
        
        result = self.runner.invoke(app, [project_name, "--output-dir", self.test_dir])
        
        assert result.exit_code == 1
        assert "already exists" in result.stdout.lower()
    
    def test_init_with_custom_name(self):
        """Test initialization with custom project name."""
        project_name = "my-cool-skill"
        project_dir = Path(self.test_dir) / project_name
        
        result = self.runner.invoke(app, [project_name, "--output-dir", self.test_dir])
        
        assert result.exit_code == 0
        assert f"✅ Skill project initialized: {project_dir}" in result.stdout
    
    def test_init_output_contains_next_steps(self):
        """Test that init输出contains next steps."""
        project_name = "test-skill"
        
        result = self.runner.invoke(app, [project_name, "--output-dir", self.test_dir])
        
        assert "Next steps:" in result.stdout
        assert "cd" in result.stdout
        assert "pip install" in result.stdout


class TestInitIntegration:
    """Integration tests for init command."""
    
    def test_full_project_creation(self):
        """Test complete project creation."""
        project_name = "full-skill-test"
        project_dir = Path(self.test_dir) / project_name
        
        result = self.runner.invoke(app, [project_name, "--output-dir", self.test_dir])
        
        assert result.exit_code == 0
        
        # Check all expected files exist
        expected_files = [
            project_dir / "pyproject.toml",
            project_dir / "skill.yaml",
            project_dir / "README.md",
            project_dir / "src" / "main.py",
        ]
        
        for file_path in expected_files:
            assert file_path.exists(), f"Missing file: {file_path}"
        
        # Check directories
        expected_dirs = [
            project_dir / "src",
            project_dir / "tests",
            project_dir / "examples",
            project_dir / ".sop",
        ]
        
        for dir_path in expected_dirs:
            assert dir_path.is_dir(), f"Missing directory: {dir_path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
