"""
Integration tests for prompt version A/B switching scenarios.

Tests version registration, switching, and metadata injection.
"""

import pytest
from src.observability.config import ObservabilityConfig
from src.observability.prompt_versioning import (
    PromptVersionManager,
    register_prompt_version,
    set_active_prompt_version,
    get_active_prompt_version,
    get_prompt_version_metadata,
    get_prompt_version_manager,
)
from src.observability.langfuse_client import init_observer, get_observer
from src.observability.session import clear_session


@pytest.mark.integration
class TestPromptVersioning:
    """Integration tests for prompt version management."""

    def test_version_registration(self):
        """Test prompt version registration."""
        manager = get_prompt_version_manager()

        v1 = register_prompt_version(
            "test-prompt", "v1.0", "Initial version", {"model": "gpt-4"}
        )

        v2 = register_prompt_version(
            "test-prompt", "v2.0", "Improved version", {"model": "gpt-4-turbo"}
        )

        assert v1.version == "v1.0"
        assert v2.version == "v2.0"

        versions = manager.get_all_versions("test-prompt")
        assert len(versions) == 2

    def test_ab_test_switching(self):
        """Test A/B test version switching."""
        register_prompt_version("ab-prompt", "vA", "Control group")
        register_prompt_version("ab-prompt", "vB", "Treatment group")

        set_active_prompt_version("ab-prompt", "vA")
        active = get_active_prompt_version("ab-prompt")
        assert active == "vA"

        set_active_prompt_version("ab-prompt", "vB")
        active = get_active_prompt_version("ab-prompt")
        assert active == "vB"

        manager = get_prompt_version_manager()
        assert manager.ab_test_enabled("ab-prompt") is True

    def test_version_metadata_injection(self):
        """Test version metadata injection into traces."""
        register_prompt_version(
            "metadata-prompt",
            "v1.0",
            "Test with metadata",
            {"temperature": 0.7, "max_tokens": 500},
        )

        metadata = get_prompt_version_metadata("metadata-prompt", "v1.0")

        assert metadata["prompt_id"] == "metadata-prompt"
        assert metadata["version"] == "v1.0"
        assert metadata["description"] == "Test with metadata"
        assert metadata["temperature"] == 0.7
        assert metadata["max_tokens"] == 500

    def test_version_isolation(self):
        """Test that versions are properly isolated."""
        register_prompt_version("prompt-X", "v1.0")
        register_prompt_version("prompt-Y", "v1.0")
        register_prompt_version("prompt-X", "v2.0")

        manager = get_prompt_version_manager()

        versions_x = manager.get_all_versions("prompt-X")
        versions_y = manager.get_all_versions("prompt-Y")

        assert len(versions_x) == 2
        assert len(versions_y) == 1

    def test_langfuse_integration(self):
        """Test Langfuse integration with version tracking."""
        observer = get_observer()

        register_prompt_version("langfuse-test", "v1.0", "Langfuse test prompt")
        set_active_prompt_version("langfuse-test", "v1.0")

        active_version = get_active_prompt_version("langfuse-test")

        try:
            with observer.trace_tool_call(
                tool_name="versioned_tool",
                input_args={"test": "version-tracking"},
                prompt_version=active_version,
            ) as obs:
                if obs:
                    obs.update(
                        output="Test output",
                        metadata={
                            "prompt_id": "langfuse-test",
                            "prompt_version": active_version,
                        },
                    )

            observer.flush()

        except Exception as e:
            pytest.fail(f"Failed to trace with version: {e}")
