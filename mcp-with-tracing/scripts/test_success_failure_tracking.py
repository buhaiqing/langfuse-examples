#!/usr/bin/env python3
"""
Test success/failure tracking for tool executions.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from src.observability.config import ObservabilityConfig
from src.observability.langfuse_client import init_observer, get_observer

def test_success_tracking():
    """Test successful tool execution tracking."""
    print("=" * 60)
    print("Test 1: Success Tracking")
    print("=" * 60)
    
    observer = get_observer()
    session_id = f"success-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    try:
        with observer.trace_tool_call(
            tool_name="calculate",
            input_args={"operation": "add", "a": 5, "b": 3},
            session_id=session_id,
            user_id="test-user",
            prompt_version="v1.0",
        ) as observation:
            if observation:
                result = 5 + 3
                observation.update(output={"result": result})
        
        observer.flush()
        print("✓ Success tracking test passed\n")
        return True
        
    except Exception as e:
        print(f"✗ Success tracking test failed: {e}\n")
        return False

def test_failure_tracking():
    """Test failed tool execution tracking."""
    print("=" * 60)
    print("Test 2: Failure Tracking")
    print("=" * 60)
    
    observer = get_observer()
    session_id = f"failure-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    try:
        with observer.trace_tool_call(
            tool_name="divide",
            input_args={"operation": "divide", "a": 10, "b": 0},
            session_id=session_id,
            user_id="test-user",
            prompt_version="v1.0",
        ) as observation:
            if observation:
                result = 10 / 0  # This will raise ZeroDivisionError
                observation.update(output={"result": result})
        
        observer.flush()
        print("✗ Failure tracking test failed: Expected exception not raised\n")
        return False
        
    except ZeroDivisionError as e:
        observer.flush()
        print(f"✓ Failure tracking test passed (caught: {e})\n")
        return True
        
    except Exception as e:
        observer.flush()
        print(f"✗ Failure tracking test failed (unexpected error: {e})\n")
        return False

def test_error_handling():
    """Test error message capture."""
    print("=" * 60)
    print("Test 3: Error Message Capture")
    print("=" * 60)
    
    observer = get_observer()
    session_id = f"error-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    try:
        with observer.trace_tool_call(
            tool_name="invalid_operation",
            input_args={"operation": "unknown", "a": 1},
            session_id=session_id,
            user_id="test-user",
        ) as observation:
            if observation:
                raise ValueError("Unknown operation: unknown")
        
        observer.flush()
        print("✗ Error handling test failed: Expected exception not raised\n")
        return False
        
    except ValueError as e:
        observer.flush()
        print(f"✓ Error handling test passed (caught: {e})\n")
        return True
        
    except Exception as e:
        observer.flush()
        print(f"✗ Error handling test failed (unexpected error: {e})\n")
        return False

def main():
    print("\n" + "=" * 60)
    print("Success/Failure Tracking Tests")
    print("=" * 60 + "\n")
    
    config = ObservabilityConfig()
    if not config.is_configured():
        print("ERROR: Langfuse not configured")
        return False
    
    init_observer(config)
    
    results = []
    results.append(("Success Tracking", test_success_tracking()))
    results.append(("Failure Tracking", test_failure_tracking()))
    results.append(("Error Message Capture", test_error_handling()))
    
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
        print("\n✓ ALL TESTS PASSED")
        return True
    else:
        print("\n✗ SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
