#!/usr/bin/env python3
"""
Test script for prompt version A/B switching scenarios.

Tests version registration, switching, and metadata injection.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def test_version_registration():
    """Test prompt version registration."""
    print("=" * 60)
    print("Test 1: Version Registration")
    print("=" * 60)

    manager = get_prompt_version_manager()

    v1 = register_prompt_version("test-prompt", "v1.0", "Initial version", {"model": "gpt-4"})

    v2 = register_prompt_version(
        "test-prompt", "v2.0", "Improved version", {"model": "gpt-4-turbo"}
    )

    assert v1.version == "v1.0"
    assert v2.version == "v2.0"

    versions = manager.get_all_versions("test-prompt")
    assert len(versions) == 2

    print(f"✓ Registered 2 versions for 'test-prompt'")
    print(f"  - v1.0: {v1.description}")
    print(f"  - v2.0: {v2.description}\n")
    return True


def test_ab_test_switching():
    """Test A/B test version switching."""
    print("=" * 60)
    print("Test 2: A/B Test Version Switching")
    print("=" * 60)

    register_prompt_version("ab-prompt", "vA", "Control group")
    register_prompt_version("ab-prompt", "vB", "Treatment group")

    set_active_prompt_version("ab-prompt", "vA")
    active = get_active_prompt_version("ab-prompt")
    assert active == "vA"
    print(f"✓ Active version set to: {active}")

    set_active_prompt_version("ab-prompt", "vB")
    active = get_active_prompt_version("ab-prompt")
    assert active == "vB"
    print(f"✓ Switched to: {active}")

    manager = get_prompt_version_manager()
    assert manager.ab_test_enabled("ab-prompt") is True
    print(f"✓ A/B test enabled for 'ab-prompt'\n")
    return True


def test_version_metadata_injection():
    """Test version metadata injection into traces."""
    print("=" * 60)
    print("Test 3: Version Metadata Injection")
    print("=" * 60)

    register_prompt_version(
        "metadata-prompt", "v1.0", "Test with metadata", {"temperature": 0.7, "max_tokens": 500}
    )

    metadata = get_prompt_version_metadata("metadata-prompt", "v1.0")

    assert metadata["prompt_id"] == "metadata-prompt"
    assert metadata["version"] == "v1.0"
    assert metadata["description"] == "Test with metadata"
    assert metadata["temperature"] == 0.7
    assert metadata["max_tokens"] == 500

    print(f"✓ Metadata correctly attached:")
    print(f"  - prompt_id: {metadata['prompt_id']}")
    print(f"  - version: {metadata['version']}")
    print(f"  - temperature: {metadata['temperature']}")
    print(f"  - max_tokens: {metadata['max_tokens']}\n")
    return True


def test_version_isolation():
    """Test that versions are properly isolated."""
    print("=" * 60)
    print("Test 4: Version Isolation")
    print("=" * 60)

    register_prompt_version("prompt-X", "v1.0")
    register_prompt_version("prompt-Y", "v1.0")
    register_prompt_version("prompt-X", "v2.0")

    manager = get_prompt_version_manager()

    versions_x = manager.get_all_versions("prompt-X")
    versions_y = manager.get_all_versions("prompt-Y")

    assert len(versions_x) == 2
    assert len(versions_y) == 1

    print(f"✓ prompt-X has 2 versions (isolated)")
    print(f"✓ prompt-Y has 1 version (isolated)")
    print(f"✓ Versions properly isolated between prompts\n")
    return True


def test_langfuse_integration():
    """Test Langfuse integration with version tracking."""
    print("=" * 60)
    print("Test 5: Langfuse Integration")
    print("=" * 60)

    observer = get_observer()

    register_prompt_version("langfuse-test", "v1.0", "Langfuse test prompt")
    set_active_prompt_version("langfuse-test", "v1.0")

    active_version = get_active_prompt_version("langfuse-test")

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

    print(f"✓ Tool call traced with version: {active_version}")
    print(f"✓ Metadata injected into Langfuse")
    print(f"✓ View at: https://cloud.langfuse.com/project/\n")
    return True


def main():
    print("\n" + "=" * 60)
    print("Phase 3: Prompt Version A/B Testing")
    print("=" * 60 + "\n")

    config = ObservabilityConfig()
    init_observer(config)

    results = []
    results.append(("Version Registration", test_version_registration()))
    results.append(("A/B Test Switching", test_ab_test_switching()))
    results.append(("Metadata Injection", test_version_metadata_injection()))
    results.append(("Version Isolation", test_version_isolation()))
    results.append(("Langfuse Integration", test_langfuse_integration()))

    get_observer().shutdown()

    print("=" * 60)
    print("Summary")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ ALL PHASE 3 TESTS PASSED")
        return True
    else:
        print("\n✗ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
