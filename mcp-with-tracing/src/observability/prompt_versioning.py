"""
Prompt versioning management for MCP Langfuse Observability.

Provides prompt version registration, tracking, and comparison.
"""

import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class PromptVersion:
    """Represents a prompt version."""

    prompt_id: str
    version: str
    description: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


class PromptVersionManager:
    """
    Manages prompt versions and A/B testing.

    Handles version registration, active version tracking,
    and version comparison metadata.
    """

    def __init__(self):
        self._versions: dict[str, list[PromptVersion]] = {}
        self._active_versions: dict[str, str] = {}

    def register_version(
        self,
        prompt_id: str,
        version: str,
        description: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> PromptVersion:
        """
        Register a new prompt version.

        Args:
            prompt_id: Unique prompt identifier.
            version: Version string (e.g., "v1.0", "v2.0").
            description: Optional version description.
            metadata: Optional additional metadata.

        Returns:
            Created PromptVersion instance.
        """
        prompt_version = PromptVersion(
            prompt_id=prompt_id,
            version=version,
            description=description,
            metadata=metadata or {},
        )

        if prompt_id not in self._versions:
            self._versions[prompt_id] = []

        self._versions[prompt_id].append(prompt_version)

        if prompt_id not in self._active_versions:
            self._active_versions[prompt_id] = version

        logger.info("Registered prompt version: %s@%s", prompt_id, version)
        return prompt_version

    def get_version(self, prompt_id: str, version: str) -> Optional[PromptVersion]:
        """
        Get a specific prompt version.

        Args:
            prompt_id: Prompt identifier.
            version: Version string.

        Returns:
            PromptVersion if found, None otherwise.
        """
        if prompt_id not in self._versions:
            return None

        for v in self._versions[prompt_id]:
            if v.version == version:
                return v

        return None

    def get_all_versions(self, prompt_id: str) -> list[PromptVersion]:
        """Get all versions for a prompt."""
        return self._versions.get(prompt_id, [])

    def set_active_version(self, prompt_id: str, version: str) -> bool:
        """
        Set the active version for a prompt.

        Args:
            prompt_id: Prompt identifier.
            version: Version to activate.

        Returns:
            True if version exists and was set, False otherwise.
        """
        if prompt_id not in self._versions:
            return False

        for v in self._versions[prompt_id]:
            if v.version == version:
                self._active_versions[prompt_id] = version
                logger.info("Set active prompt version: %s@%s", prompt_id, version)
                return True

        return False

    def get_active_version(self, prompt_id: str) -> Optional[str]:
        """Get the active version for a prompt."""
        return self._active_versions.get(prompt_id)

    def get_version_metadata(self, prompt_id: str, version: str) -> dict[str, Any]:
        """Get metadata for a specific version."""
        prompt_version = self.get_version(prompt_id, version)
        if prompt_version:
            return {
                "prompt_id": prompt_id,
                "version": version,
                "description": prompt_version.description,
                **prompt_version.metadata,
            }
        return {}

    def list_prompts(self) -> list[str]:
        """List all registered prompt IDs."""
        return list(self._versions.keys())

    def ab_test_enabled(self, prompt_id: str) -> bool:
        """Check if A/B test is enabled for a prompt."""
        return len(self._versions.get(prompt_id, [])) > 1


_prompt_version_manager: Optional[PromptVersionManager] = None


def get_prompt_version_manager() -> PromptVersionManager:
    """Get or create the global prompt version manager."""
    global _prompt_version_manager
    if _prompt_version_manager is None:
        _prompt_version_manager = PromptVersionManager()
    return _prompt_version_manager


def register_prompt_version(
    prompt_id: str,
    version: str,
    description: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> PromptVersion:
    """Register a new prompt version."""
    return get_prompt_version_manager().register_version(prompt_id, version, description, metadata)


def set_active_prompt_version(prompt_id: str, version: str) -> bool:
    """Set active version for a prompt."""
    return get_prompt_version_manager().set_active_version(prompt_id, version)


def get_active_prompt_version(prompt_id: str) -> Optional[str]:
    """Get active version for a prompt."""
    return get_prompt_version_manager().get_active_version(prompt_id)


def get_prompt_version_metadata(prompt_id: str, version: str) -> dict[str, Any]:
    """Get metadata for a prompt version."""
    return get_prompt_version_manager().get_version_metadata(prompt_id, version)
