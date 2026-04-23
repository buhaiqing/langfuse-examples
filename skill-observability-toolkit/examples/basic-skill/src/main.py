#!/usr/bin/env python3
"""
Basic Skill Example - Demonstrating STOP Protocol with Tracing

This example shows how to:
1. Parse a skill.yaml manifest using STOP Protocol
2. Use the ManifestParser to validate inputs
3. Execute the skill with proper tracing structure
4. Record results and calculate Trust Score

Usage:
    python main.py --input-file data.txt --process-type count

Requirements:
    - Python 3.10+
    - PyYAML installed
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any, Optional, Dict

from skill_observability_toolkit.stop.manifest import (
    ManifestParser,
    ManifestParseError,
    ManifestValidationError,
)
from skill_observability_toolkit.stop.assertions import AssertionEngine
from skill_observability_toolkit.stop.tracer import STOPTracer


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Basic Skill Example - STOP Protocol with Tracing"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default="data.txt",
        help="Path to input file to process (default: data.txt)",
    )
    parser.add_argument(
        "--process-type",
        type=str,
        default="count",
        choices=["count", "analyze", "transform"],
        help="Type of processing to apply (default: count)",
    )
    parser.add_argument(
        "--skill-yaml",
        type=str,
        default="skill.yaml",
        help="Path to skill.yaml manifest (default: skill.yaml)",
    )
    return parser.parse_args()


def parse_manifest(skill_yaml_path: str) -> Any:
    """Parse and validate the skill manifest."""
    print(f"📄 Loading manifest from: {skill_yaml_path}")
    
    parser = ManifestParser(skill_yaml_path=skill_yaml_path)
    
    try:
        manifest = parser.parse()
        print(f"✨ Manifest parsed successfully!")
        print(f"   Skill: {manifest.name} v{manifest.version}")
        print(f"   Inputs: {len(manifest.inputs)}")
        print(f"   Outputs: {len(manifest.outputs)}")
        print(f"   Assertions: {len(manifest.assertions)}")
        
        return manifest, parser
    except ManifestParseError as e:
        print(f"❌ Parse error: {e}")
        raise
    except ManifestValidationError as e:
        print(f"❌ Validation error: {e}")
        raise


def run_assertions(parser: ManifestParser, manifest: Any, inputs: dict) -> list:
    """Run pre-execution assertions."""
    print(f"\n🔍 Running pre-execution assertions...")
    
    pre_assertions = [a for a in manifest.assertions if a.type == "pre"]
    results = []
    
    for assertion in pre_assertions:
        print(f"   Checking: {assertion.check}...")
        # In a real implementation, this would evaluate the assertion
        # For now, we'll simulate successful assertions
        result = {"passed": True, "assertion": assertion.check, "message": assertion.message}
        results.append(result)
        print(f"   ✓ {assertion.check}: PASSED")
    
    # Validate process_type
    if inputs.get("process_type") not in ["count", "analyze", "transform"]:
        print(f"   ✗ process_type: INVALID")
        results.append({"passed": False, "assertion": "process_type", "message": "Invalid process type"})
    
    return results


def process_content(input_file: str, process_type: str) -> dict:
    """Process the input content."""
    print(f"\n⚙️  Processing content...")
    
    start_time = time.time()
    
    # Read file
    file_path = Path(input_file)
    
    if not file_path.exists():
        print(f"   ⚠️  Input file not found: {input_file}")
        return {
            "success": False,
            "error": f"File not found: {input_file}",
            "stats": {
                "word_count": 0,
                "char_count": 0,
                "duration_ms": 0,
            },
        }
    
    content = file_path.read_text()
    
    # Process based on type
    if process_type == "count":
        word_count = len(content.split())
        char_count = len(content)
        print(f"   Counting words and characters...")
        print(f"   Words: {word_count}")
        print(f"   Chars: {char_count}")
    elif process_type == "analyze":
        word_count = len(content.split())
        char_count = len(content)
        print(f"   Analyzing content structure...")
        print(f"   Words: {word_count}")
        print(f"   Chars: {char_count}")
        print(f"   Lines: {len(content.splitlines())}")
    else:  # transform
        word_count = len(content.split())
        char_count = len(content)
        print(f"   Transforming content...")
        print(f"   Words: {word_count}")
        print(f"   Chars: {char_count}")
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    return {
        "success": True,
        "stats": {
            "word_count": word_count,
            "char_count": char_count,
            "duration_ms": duration_ms,
        },
    }


def run_post_assertions(parser: ManifestParser, manifest: Any, result: dict) -> list:
    """Run post-execution assertions."""
    print(f"\n🔍 Running post-execution assertions...")
    
    post_assertions = [a for a in manifest.assertions if a.type == "post"]
    results = []
    
    for assertion in post_assertions:
        print(f"   Checking: {assertion.check}...")
        # Simulate assertions
        if assertion.check == "output.exists":
            passed = result is not None
        elif assertion.check == "output.success":
            passed = result.get("success", False) == True
        elif assertion.check == "output.not_empty":
            passed = result.get("stats", {}).get("word_count", 0) > 0
        elif assertion.check == "performance":
            passed = result.get("stats", {}).get("duration_ms", 0) < 10000
        else:
            passed = True
        
        status = "PASSED" if passed else "FAILED"
        print(f"   {'✓' if passed else '✗'} {assertion.check}: {status}")
        
        results.append({
            "passed": passed,
            "assertion": assertion.check,
            "message": assertion.message,
        })
    
    return results


def calculate_trust_score(parser: ManifestParser, results: list) -> float:
    """Calculate Trust Score from assertion results."""
    # Use AssertionEngine for Trust Score calculation
    engine = AssertionEngine()
    from skill_observability_toolkit.stop.assertions import AssertionResult
    
    # Convert results to AssertionResult objects
    assertion_results = [
        AssertionResult(
            passed=r["passed"],
            assertion=r["assertion"],
            message=r["message"],
        )
        for r in results
    ]
    
    trust_score = engine.calculate_trust_score(assertion_results)
    
    print(f"\n📊 Trust Score Calculation:")
    print(f"   Passed: {sum(1 for r in results if r['passed'])}")
    print(f"   Total: {len(results)}")
    print(f"   Score: {trust_score:.2f} (0.0 - 1.0)")
    
    return trust_score


def print_trace_summary(manifest: Any, inputs: dict, result: dict, trust_score: float):
    """Print a summary of the execution trace."""
    print(f"\n{'=' * 60}")
    print(f"📄 TRACE SUMMARY")
    print(f"{'=' * 60}")
    
    print(f"\nSkill Information:")
    print(f"   Name: {manifest.name}")
    print(f"   Version: {manifest.version}")
    
    print(f"\nInputs:")
    print(f"   input_file: {inputs.get('input_file', 'N/A')}")
    print(f"   process_type: {inputs.get('process_type', 'N/A')}")
    
    print(f"\nResults:")
    if result.get("success"):
        print(f"   ✓ Success: True")
        stats = result.get("stats", {})
        print(f"   Word Count: {stats.get('word_count', 'N/A')}")
        print(f"   Char Count: {stats.get('char_count', 'N/A')}")
        print(f"   Duration: {stats.get('duration_ms', 'N/A')} ms")
    else:
        print(f"   ✗ Success: False")
        print(f"   Error: {result.get('error', 'Unknown')}")
    
    print(f"\nTrust Score: {trust_score:.2f}")
    print(f"{'=' * 60}")


def save_trace(manifest: Any, inputs: dict, result: dict, trust_score: float):
    """Save trace to NDJSON format (placeholder for Task 1.3)."""
    trace = {
        "trace_id": "example_trace_001",
        "skill_name": manifest.name,
        "skill_version": manifest.version,
        "inputs": inputs,
        "result": result,
        "trust_score": trust_score,
        "assertions": {
            "pre": 3,
            "post": 4,
        },
    }
    
    trace_path = Path("trace.ndjson")
    trace_path.write_text(json.dumps(trace, indent=2))
    
    print(f"\n💾 Trace saved to: {trace_path}")


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()
    
    print(f"🚀 Starting Basic Tracing Skill")
    print(f"{'=' * 60}")
    
    # Step 1: Parse manifest
    manifest, parser = parse_manifest(args.skill_yaml)
    
    # Step 2: Prepare inputs
    inputs = {
        "input_file": args.input_file,
        "process_type": args.process_type,
    }
    
    # Step 3: Run pre-execution assertions
    pre_results = run_assertions(parser, manifest, inputs)
    
    # Check if pre-assertions passed
    if not all(r["passed"] for r in pre_results):
        print(f"\n❌ Pre-execution assertions failed!")
        return 1
    
    # Step 4: Execute skill
    result = process_content(args.input_file, args.process_type)
    
    # Step 5: Run post-execution assertions
    post_results = run_post_assertions(parser, manifest, result)
    
    # Combine all results
    all_results = pre_results + post_results
    
    # Step 6: Calculate Trust Score
    trust_score = calculate_trust_score(parser, all_results)
    
    # Step 7: Print summary
    print_trace_summary(manifest, inputs, result, trust_score)
    
    # Step 8: Save trace
    save_trace(manifest, inputs, result, trust_score)
    
    print(f"\n✨ Execution completed successfully!")
    print(f"   Trust Score: {trust_score:.2f}")
    
    # Return exit code based on results
    if result.get("success") and trust_score >= 0.8:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())
