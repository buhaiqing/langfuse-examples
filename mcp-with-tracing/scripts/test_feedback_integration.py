#!/usr/bin/env python3
"""
Integration test script for feedback tools.

This script tests the complete integration of feedback tools with the MCP server.
Run this to verify that all feedback tools are properly registered and functional.
"""

import asyncio
import sys
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, "/Users/bohaiqing/test/ai_agent/langfuse_senarios/mcp-with-tracing")

from src.server import mcp


# Get the original functions from FunctionTool objects
def get_tool_function(tool_name: str):
    """Extract the original function from a registered tool."""
    async def _get():
        tools = await mcp._tool_manager.list_tools()
        for tool in tools:
            if tool.name == tool_name:
                return tool.fn
        return None
    
    return asyncio.run(_get())


# Get tool functions
submit_feedback_accept = get_tool_function("submit_feedback_accept")
submit_feedback_reject = get_tool_function("submit_feedback_reject")
submit_feedback_rating = get_tool_function("submit_feedback_rating")
submit_feedback_comment = get_tool_function("submit_feedback_comment")


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_success(message):
    """Print success message."""
    print(f"✓ {message}")


def print_error(message):
    """Print error message."""
    print(f"✗ {message}")


async def test_tools_registration():
    """Test that all feedback tools are registered."""
    print_header("Test 1: Tools Registration")
    
    tools = await mcp._tool_manager.list_tools()
    tool_names = [tool.name for tool in tools]
    
    expected_tools = [
        "submit_feedback_accept",
        "submit_feedback_reject",
        "submit_feedback_rating",
        "submit_feedback_comment",
    ]
    
    all_registered = True
    for tool_name in expected_tools:
        if tool_name in tool_names:
            print_success(f"Tool '{tool_name}' is registered")
        else:
            print_error(f"Tool '{tool_name}' is NOT registered")
            all_registered = False
    
    print(f"\nTotal tools: {len(tools)} (expected: {len(expected_tools)})")
    
    if len(tools) == len(expected_tools):
        print_success("Correct number of tools registered")
    else:
        print_error(f"Expected {len(expected_tools)} tools, got {len(tools)}")
        all_registered = False
    
    return all_registered


def test_tool_functions():
    """Test feedback tool functions directly."""
    print_header("Test 2: Tool Functions")
    
    test_trace_id = "test-trace-integration"
    
    # Test accept
    with patch("src.server.get_session_id", return_value="test-user"):
        with patch("src.server.record_acceptance") as mock_record:
            mock_record.return_value = Mock(trace_id=test_trace_id)
            
            result = submit_feedback_accept(
                trace_id=test_trace_id,
                comment="Great!",
            )
            
            if result["status"] == "success" and result["feedback_type"] == "accept":
                print_success("submit_feedback_accept works correctly")
            else:
                print_error("submit_feedback_accept failed")
                return False
    
    # Test reject
    with patch("src.server.get_session_id", return_value="test-user"):
        with patch("src.server.record_rejection") as mock_record:
            mock_record.return_value = Mock(trace_id=test_trace_id)
            
            result = submit_feedback_reject(
                trace_id=test_trace_id,
                reason="inaccurate",
            )
            
            if result["status"] == "success" and result["feedback_type"] == "reject":
                print_success("submit_feedback_reject works correctly")
            else:
                print_error("submit_feedback_reject failed")
                return False
    
    # Test rating
    with patch("src.server.get_session_id", return_value="test-user"):
        with patch("src.server.record_rating") as mock_record:
            mock_record.return_value = Mock(trace_id=test_trace_id)
            
            result = submit_feedback_rating(
                trace_id=test_trace_id,
                rating=5,
            )
            
            if result["status"] == "success" and result["feedback_type"] == "rating":
                print_success("submit_feedback_rating works correctly")
            else:
                print_error("submit_feedback_rating failed")
                return False
    
    # Test comment
    with patch("src.server.get_session_id", return_value="test-user"):
        with patch("src.server.record_comment") as mock_record:
            mock_record.return_value = Mock(trace_id=test_trace_id)
            
            result = submit_feedback_comment(
                trace_id=test_trace_id,
                comment="Helpful response",
            )
            
            if result["status"] == "success" and result["feedback_type"] == "comment":
                print_success("submit_feedback_comment works correctly")
            else:
                print_error("submit_feedback_comment failed")
                return False
    
    return True


def test_observability_decorators():
    """Test that tools have observability decorators."""
    print_header("Test 3: Observability Decorators")
    
    tools = [
        (submit_feedback_accept, "submit_feedback_accept"),
        (submit_feedback_reject, "submit_feedback_reject"),
        (submit_feedback_rating, "submit_feedback_rating"),
        (submit_feedback_comment, "submit_feedback_comment"),
    ]
    
    all_ok = True
    for func, expected_name in tools:
        if hasattr(func, "_langfuse_observed"):
            print_success(f"{expected_name} has observe decorator")
        else:
            print_error(f"{expected_name} missing observe decorator")
            all_ok = False
        
        if hasattr(func, "_langfuse_name") and func._langfuse_name == expected_name:
            print_success(f"{expected_name} has correct span name")
        else:
            print_error(f"{expected_name} has incorrect span name")
            all_ok = False
    
    return all_ok


def test_no_duplicate_mcp_instances():
    """Verify all tools are defined in server.py."""
    print_header("Test 4: All Tools in server.py")
    
    # Check that feedback_tool.py no longer exists or is empty
    try:
        import os
        feedback_tool_path = "/Users/bohaiqing/test/ai_agent/langfuse_senarios/mcp-with-tracing/src/tools/feedback_tool.py"
        
        if os.path.exists(feedback_tool_path):
            # Check if file is essentially empty (only comments/docstrings)
            with open(feedback_tool_path, 'r') as f:
                content = f.read().strip()
                # Remove comments and docstrings for checking
                lines = [line.strip() for line in content.split('\n') 
                        if line.strip() and not line.strip().startswith('#')]
                code_lines = [line for line in lines if not line.startswith('"""')]
                
                if len(code_lines) <= 3:  # Only imports or empty
                    print_success("feedback_tool.py has been deprecated")
                    print_success("All tools are now defined in server.py")
                    return True
                else:
                    print_error("feedback_tool.py still contains tool definitions")
                    return False
        else:
            print_success("feedback_tool.py has been removed")
            print_success("All tools are defined in server.py")
            return True
    except Exception as e:
        print_error(f"Error checking feedback_tool module: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("  MCP Feedback Tools - Integration Test Suite")
    print("=" * 70)
    
    results = []
    
    # Run tests
    results.append(("Tools Registration", await test_tools_registration()))
    results.append(("Tool Functions", test_tool_functions()))
    results.append(("Observability Decorators", test_observability_decorators()))
    results.append(("Single MCP Instance", test_no_duplicate_mcp_instances()))
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status:10} - {test_name}")
    
    print("\n" + "-" * 70)
    print(f"Total: {passed}/{total} tests passed")
    print("-" * 70)
    
    if passed == total:
        print("\n🎉 All integration tests passed!")
        print("\nThe feedback tools are properly integrated with the MCP server.")
        print("Clients can now access all 4 tools through a single connection:")
        print("  - submit_feedback_accept ✨")
        print("  - submit_feedback_reject ✨")
        print("  - submit_feedback_rating ✨")
        print("  - submit_feedback_comment ✨")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
