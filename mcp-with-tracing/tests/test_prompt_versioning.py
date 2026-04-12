"""
Tests for prompt versioning.
"""

import pytest

from src.observability.prompt_versioning import (
    PromptVersionManager,
    get_prompt_version_manager,
    register_prompt_version,
    set_active_prompt_version,
    get_active_prompt_version,
    get_prompt_version_metadata,
)


class TestPromptVersionManager:
    """Tests for PromptVersionManager class."""

    def setup_method(self):
        """Create fresh manager for each test."""
        self.manager = PromptVersionManager()

    def test_register_version(self):
        """Test version registration."""
        version = self.manager.register_version(
            prompt_id="test-prompt",
            version="v1.0",
            description="Initial version",
            metadata={"author": "test"},
        )

        assert version.prompt_id == "test-prompt"
        assert version.version == "v1.0"
        assert version.description == "Initial version"
        assert version.metadata["author"] == "test"

    def test_register_multiple_versions(self):
        """Test registering multiple versions."""
        self.manager.register_version("prompt-1", "v1.0")
        self.manager.register_version("prompt-1", "v2.0")
        self.manager.register_version("prompt-1", "v3.0")

        versions = self.manager.get_all_versions("prompt-1")
        assert len(versions) == 3

    def test_get_version_exists(self):
        """Test getting existing version."""
        self.manager.register_version("prompt-1", "v1.0", "First")

        version = self.manager.get_version("prompt-1", "v1.0")
        assert version is not None
        assert version.description == "First"

    def test_get_version_not_exists(self):
        """Test getting non-existing version."""
        version = self.manager.get_version("prompt-1", "v1.0")
        assert version is None

    def test_set_active_version(self):
        """Test setting active version."""
        self.manager.register_version("prompt-1", "v1.0")
        self.manager.register_version("prompt-1", "v2.0")

        result = self.manager.set_active_version("prompt-1", "v2.0")
        assert result is True
        assert self.manager.get_active_version("prompt-1") == "v2.0"

    def test_set_active_version_not_exists(self):
        """Test setting non-existing active version."""
        result = self.manager.set_active_version("prompt-1", "v99.0")
        assert result is False

    def test_get_all_versions(self):
        """Test getting all versions."""
        self.manager.register_version("prompt-1", "v1.0")
        self.manager.register_version("prompt-1", "v2.0")

        versions = self.manager.get_all_versions("prompt-1")
        assert len(versions) == 2
        assert versions[0].version == "v1.0"
        assert versions[1].version == "v2.0"

    def test_list_prompts(self):
        """Test listing all prompts."""
        self.manager.register_version("prompt-1", "v1.0")
        self.manager.register_version("prompt-2", "v1.0")
        self.manager.register_version("prompt-3", "v1.0")

        prompts = self.manager.list_prompts()
        assert len(prompts) == 3
        assert "prompt-1" in prompts
        assert "prompt-2" in prompts
        assert "prompt-3" in prompts

    def test_ab_test_enabled(self):
        """Test A/B test detection."""
        self.manager.register_version("prompt-1", "v1.0")
        assert self.manager.ab_test_enabled("prompt-1") is False

        self.manager.register_version("prompt-1", "v2.0")
        assert self.manager.ab_test_enabled("prompt-1") is True

    def test_get_version_metadata(self):
        """Test getting version metadata."""
        self.manager.register_version(
            "prompt-1",
            "v1.0",
            "Test version",
            {"key": "value"},
        )

        metadata = self.manager.get_version_metadata("prompt-1", "v1.0")
        assert metadata["prompt_id"] == "prompt-1"
        assert metadata["version"] == "v1.0"
        assert metadata["description"] == "Test version"
        assert metadata["key"] == "value"


class TestGlobalPromptVersionManager:
    """Tests for global prompt version manager functions."""

    def test_get_prompt_version_manager_singleton(self):
        """Test that get_prompt_version_manager returns same instance."""
        manager1 = get_prompt_version_manager()
        manager2 = get_prompt_version_manager()
        assert manager1 is manager2

    def test_register_prompt_version(self):
        """Test register_prompt_version function."""
        version = register_prompt_version(
            "test-global",
            "v1.0",
            "Global test",
        )
        assert version.prompt_id == "test-global"
        assert version.version == "v1.0"

    def test_set_active_prompt_version(self):
        """Test set_active_prompt_version function."""
        register_prompt_version("test-active", "v1.0")
        register_prompt_version("test-active", "v2.0")

        result = set_active_prompt_version("test-active", "v2.0")
        assert result is True
        assert get_active_prompt_version("test-active") == "v2.0"

    def test_get_prompt_version_metadata(self):
        """Test get_prompt_version_metadata function."""
        register_prompt_version(
            "test-meta",
            "v1.0",
            "Metadata test",
            {"env": "test"},
        )

        metadata = get_prompt_version_metadata("test-meta", "v1.0")
        assert metadata["prompt_id"] == "test-meta"
        assert metadata["version"] == "v1.0"
