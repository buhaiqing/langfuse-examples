#!/usr/bin/env python3
"""
Query script for prompt version comparison.

Compares different prompt versions by analyzing traces in Langfuse.

Usage:
    python scripts/query_prompt_versions.py list <prompt_id>
    python scripts/query_prompt_versions.py compare <prompt_id> <version_a> <version_b>
    python scripts/query_prompt_versions.py performance <prompt_id> <version>
    python scripts/query_prompt_versions.py  # List all prompts
"""

import sys
import os
from datetime import datetime, timedelta
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.observability.prompt_versioning import get_prompt_version_manager


def query_versions_by_prompt(prompt_id: str):
    """Query all versions for a specific prompt."""
    manager = get_prompt_version_manager()

    versions = manager.get_all_versions(prompt_id)
    active_version = manager.get_active_version(prompt_id)

    print(f"\nPrompt: {prompt_id}")
    print(f"Active Version: {active_version}")
    print(f"Total Versions: {len(versions)}")
    print("-" * 60)

    for v in versions:
        is_active = "✓" if v.version == active_version else " "
        print(
            f"{is_active} {v.version:10} | Created: {v.created_at[:19]} | {v.description or 'No description'}"
        )


def compare_versions(prompt_id: str, version_a: str, version_b: str):
    """Compare two prompt versions (A/B test)."""
    manager = get_prompt_version_manager()

    version_a_data = manager.get_version(prompt_id, version_a)
    version_b_data = manager.get_version(prompt_id, version_b)

    if not version_a_data or not version_b_data:
        print(f"Error: One or both versions not found")
        return

    print(f"\nA/B Test Comparison: {prompt_id}")
    print("=" * 60)

    print(f"\nVersion A: {version_a}")
    print(f"  Description: {version_a_data.description or 'N/A'}")
    print(f"  Created: {version_a_data.created_at[:19]}")
    print(f"  Metadata: {version_a_data.metadata}")

    print(f"\nVersion B: {version_b}")
    print(f"  Description: {version_b_data.description or 'N/A'}")
    print(f"  Created: {version_b_data.created_at[:19]}")
    print(f"  Metadata: {version_b_data.metadata}")

    print("\n" + "=" * 60)
    print("Note: View actual performance metrics in Langfuse dashboard")
    print(f"Filter: prompt_id={prompt_id} AND version IN ({version_a}, {version_b})")


def list_all_prompts():
    """List all registered prompts with their versions."""
    manager = get_prompt_version_manager()

    prompts = manager.list_prompts()

    print("\nRegistered Prompts")
    print("=" * 60)

    for prompt_id in sorted(prompts):
        versions = manager.get_all_versions(prompt_id)
        active = manager.get_active_version(prompt_id)
        ab_test = "AB" if manager.ab_test_enabled(prompt_id) else "  "

        print(f"\n{ab_test} {prompt_id}")
        print(f"    Active: {active}")
        print(f"    Versions: {len(versions)}")


def get_version_performance(prompt_id: str, version: str):
    """Get performance metrics for a specific version."""
    print(f"\nPerformance for {prompt_id}@{version}")
    print("=" * 60)

    metadata = get_prompt_version_manager().get_version_metadata(prompt_id, version)

    print(f"Prompt ID: {metadata.get('prompt_id', 'N/A')}")
    print(f"Version: {metadata.get('version', 'N/A')}")
    print(f"Description: {metadata.get('description', 'N/A')}")

    print("\nQuery Langfuse for metrics:")
    print(f"  Filter: metadata.prompt_id={prompt_id} AND metadata.version={version}")
    print(f"  Metrics to check:")
    print(f"    - Success rate")
    print(f"    - P95 latency")
    print(f"    - User acceptance rate")
    print(f"    - Token usage")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Query and compare prompt versions in Langfuse",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list customer-support-prompt
  %(prog)s compare customer-support-prompt v1.0 v2.0
  %(prog)s performance customer-support-prompt v1.0
  %(prog)s  # List all prompts
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List versions for a prompt")
    list_parser.add_argument("prompt_id", help="Prompt ID to list versions for")
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two versions (A/B test)")
    compare_parser.add_argument("prompt_id", help="Prompt ID")
    compare_parser.add_argument("version_a", help="Version A (control)")
    compare_parser.add_argument("version_b", help="Version B (treatment)")
    
    # Performance command
    perf_parser = subparsers.add_parser("performance", help="Get version performance metrics")
    perf_parser.add_argument("prompt_id", help="Prompt ID")
    perf_parser.add_argument("version", help="Version to get performance for")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("Prompt Version Query Tool")
    print("=" * 60)

    manager = get_prompt_version_manager()

    if len(manager.list_prompts()) == 0:
        print("\nNo prompts registered yet.")
        print("\nUsage:")
        print("  from src.observability.prompt_versioning import register_prompt_version")
        print("  register_prompt_version('my-prompt', 'v1.0', 'Initial version')")
        return 0
    
    # Execute command
    if args.command == "list":
        query_versions_by_prompt(args.prompt_id)
    elif args.command == "compare":
        compare_versions(args.prompt_id, args.version_a, args.version_b)
    elif args.command == "performance":
        get_version_performance(args.prompt_id, args.version)
    else:
        # No command specified, list all prompts
        list_all_prompts()
        
        print("\n\nQuery Examples:")
        print("-" * 60)
        print("1. List versions for a prompt:")
        print("   python scripts/query_prompt_versions.py list <prompt_id>")
        print("\n2. Compare two versions (A/B test):")
        print("   python scripts/query_prompt_versions.py compare <prompt_id> <v1> <v2>")
        print("\n3. Get version performance:")
        print("   python scripts/query_prompt_versions.py performance <prompt_id> <version>")

    return 0


if __name__ == "__main__":
    sys.exit(main())
