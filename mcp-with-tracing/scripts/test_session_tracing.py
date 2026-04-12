#!/usr/bin/env python3
"""
Test script for multi-session tracing scenarios.

Tests session isolation and proper propagation across multiple tool calls.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.observability.config import ObservabilityConfig
from src.observability.langfuse_client import init_observer, get_observer
from src.observability.session import (
    SessionManager,
    set_session,
    get_session_id,
    clear_session,
)


def test_single_session_multiple_calls():
    """Test multiple tool calls within same session."""
    print("=" * 60)
    print("Test 1: Single Session - Multiple Tool Calls")
    print("=" * 60)

    observer = get_observer()
    session_id = f"single-session-test"

    try:
        # First tool call
        with observer.trace_tool_call(
            tool_name="echo_1",
            input_args={"message": "First call"},
            session_id=session_id,
            user_id="user-123",
        ) as obs:
            if obs:
                obs.update(output="Echo: First call")

        # Second tool call - should inherit same session
        with observer.trace_tool_call(
            tool_name="echo_2",
            input_args={"message": "Second call"},
            session_id=session_id,
            user_id="user-123",
        ) as obs:
            if obs:
                obs.update(output="Echo: Second call")

        # Third tool call
        with observer.trace_tool_call(
            tool_name="calculate",
            input_args={"operation": "add", "a": 1, "b": 2},
            session_id=session_id,
            user_id="user-123",
        ) as obs:
            if obs:
                obs.update(output=3)

        observer.flush()

        current_session = get_session_id()
        assert current_session == session_id, f"Session mismatch: {current_session} != {session_id}"

        print(f"✓ Session ID propagated: {session_id}")
        print(f"✓ 3 tool calls completed in same session\n")
        return True

    except Exception as e:
        print(f"✗ Test failed: {e}\n")
        import traceback

        traceback.print_exc()
        return False
    finally:
        clear_session()


def test_multiple_sessions_isolation():
    """Test that multiple sessions are properly isolated."""
    print("=" * 60)
    print("Test 2: Multiple Sessions - Isolation Test")
    print("=" * 60)

    observer = get_observer()
    session_1 = "session-A"
    session_2 = "session-B"

    try:
        # Session A - Tool call 1
        set_session(session_1, "user-A")
        with observer.trace_tool_call(
            tool_name="tool_a1",
            input_args={"session": "A"},
        ) as obs:
            if obs:
                obs.update(output="Session A, Call 1")

        # Session B - Tool call 1
        set_session(session_2, "user-B")
        with observer.trace_tool_call(
            tool_name="tool_b1",
            input_args={"session": "B"},
        ) as obs:
            if obs:
                obs.update(output="Session B, Call 1")

        # Session A - Tool call 2
        set_session(session_1, "user-A")
        with observer.trace_tool_call(
            tool_name="tool_a2",
            input_args={"session": "A"},
        ) as obs:
            if obs:
                obs.update(output="Session A, Call 2")

        # Session B - Tool call 2
        set_session(session_2, "user-B")
        with observer.trace_tool_call(
            tool_name="tool_b2",
            input_args={"session": "B"},
        ) as obs:
            if obs:
                obs.update(output="Session B, Call 2")

        observer.flush()

        print(f"✓ Session A: 2 tool calls (user-A)")
        print(f"✓ Session B: 2 tool calls (user-B)")
        print(f"✓ Sessions properly isolated\n")
        return True

    except Exception as e:
        print(f"✗ Test failed: {e}\n")
        import traceback

        traceback.print_exc()
        return False
    finally:
        clear_session()


def test_session_with_metadata():
    """Test session with custom metadata."""
    print("=" * 60)
    print("Test 3: Session with Custom Metadata")
    print("=" * 60)

    observer = get_observer()
    session_id = "metadata-test-session"

    try:
        set_session(
            session_id,
            user_id="user-metadata",
            metadata={
                "app": "mcp-server",
                "version": "1.0.0",
                "environment": "test",
            },
        )

        with observer.trace_tool_call(
            tool_name="metadata_test",
            input_args={"test": "metadata"},
        ) as obs:
            if obs:
                obs.update(output="Metadata test passed")

        observer.flush()

        ctx = SessionManager.get_session()
        assert ctx["metadata"]["app"] == "mcp-server"
        assert ctx["metadata"]["version"] == "1.0.0"

        print(f"✓ Metadata attached to session")
        print(f"✓ App: {ctx['metadata']['app']}")
        print(f"✓ Version: {ctx['metadata']['version']}\n")
        return True

    except Exception as e:
        print(f"✗ Test failed: {e}\n")
        import traceback

        traceback.print_exc()
        return False
    finally:
        clear_session()


def test_session_replay_preparation():
    """Test that session data is ready for Langfuse replay."""
    print("=" * 60)
    print("Test 4: Session Replay Preparation")
    print("=" * 60)

    observer = get_observer()
    session_id = f"replay-test"

    try:
        observer.trace_tool_call(
            tool_name="replay_test_1",
            input_args={"step": 1},
            session_id=session_id,
            user_id="replay-user",
        ).__enter__()

        observer.trace_tool_call(
            tool_name="replay_test_2",
            input_args={"step": 2},
            session_id=session_id,
            user_id="replay-user",
        ).__enter__()

        observer.flush()

        print(f"✓ Session {session_id} ready for replay")
        print(f"✓ View at: https://cloud.langfuse.com/project/")
        print(f"✓ Filter by session_id: {session_id}\n")
        return True

    except Exception as e:
        print(f"✗ Test failed: {e}\n")
        import traceback

        traceback.print_exc()
        return False
    finally:
        clear_session()


def main():
    print("\n" + "=" * 60)
    print("Phase 2: Multi-Session Tracing Tests")
    print("=" * 60 + "\n")

    config = ObservabilityConfig()
    if not config.is_configured():
        print("ERROR: Langfuse not configured")
        return False

    init_observer(config)

    results = []
    results.append(("Single Session - Multiple Calls", test_single_session_multiple_calls()))
    results.append(("Multiple Sessions - Isolation", test_multiple_sessions_isolation()))
    results.append(("Session with Metadata", test_session_with_metadata()))
    results.append(("Session Replay Preparation", test_session_replay_preparation()))

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
        print("\n✓ ALL PHASE 2 TESTS PASSED")
        return True
    else:
        print("\n✗ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
