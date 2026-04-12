#!/usr/bin/env python3
"""
Script to add pytest markers to integration test files.

This script converts old-style test scripts to pytest format with markers.
"""

import os
import re
from pathlib import Path


def add_marker_to_file(file_path: str) -> bool:
    """Add @pytest.mark.integration marker to a test file."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already has pytest markers
    if '@pytest.mark.integration' in content or '@pytest.mark.slow' in content:
        print(f"  ⏭️  Skipped (already has markers): {os.path.basename(file_path)}")
        return False
    
    # Check if it's a pytest file (has import pytest)
    if 'import pytest' not in content:
        print(f"  ⚠️  Not a pytest file: {os.path.basename(file_path)}")
        return False
    
    # Add marker to test functions
    # Pattern 1: def test_xxx( at start of line
    pattern = r'^(\s*)def (test_\w+)\('
    replacement = r'\1@pytest.mark.integration\n\1def \2('
    
    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  ✅ Added markers: {os.path.basename(file_path)}")
        return True
    else:
        print(f"  ❌ No changes: {os.path.basename(file_path)}")
        return False


def main():
    """Main function to process all integration test files."""
    # Get the project root directory (parent of scripts/)
    project_root = Path(__file__).parent.parent
    integration_dir = project_root / 'tests' / 'integration'
    
    if not integration_dir.exists():
        print(f"❌ Integration tests directory not found: {integration_dir}")
        return
    
    print("=" * 60)
    print("Adding pytest markers to integration tests")
    print("=" * 60)
    print()
    
    test_files = list(integration_dir.glob('test_*.py'))
    
    if not test_files:
        print("No test files found!")
        return
    
    print(f"Found {len(test_files)} test files:\n")
    
    modified_count = 0
    for test_file in sorted(test_files):
        if add_marker_to_file(str(test_file)):
            modified_count += 1
    
    print()
    print("=" * 60)
    print(f"Summary: {modified_count}/{len(test_files)} files modified")
    print("=" * 60)


if __name__ == '__main__':
    main()
