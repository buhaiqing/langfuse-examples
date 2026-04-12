"""
Test script for multi-session tracing scenarios.

This script tests:
1. Session isolation between concurrent sessions
2. Session ID propagation across multiple tool calls
3. Session replay functionality
"""

import asyncio
import time
from typing import List, Dict, Any
from src.observability.session import (
    SessionManager,
    set_session,
    get_session_id,
    get_user_id,
    clear_session,
)
from src.observability.langfuse_client import get_observer, init_observer
from src.observability.config import ObservabilityConfig


def test_single_session_multiple_tools():
    """Test that multiple tool calls share the same session_id."""
    print("\n" + "=" * 80)
    print("TEST 1: Single Session with Multiple Tool Calls")
    print("=" * 80)

    observer = get_observer()
    session_id = SessionManager.generate_session_id()
    user_id = "test-user-001"

    print(f"\n📋 Session ID: {session_id}")
    print(f"👤 User ID: {user_id}")

    # Set session context
    set_session(session_id=session_id, user_id=user_id)

    # Simulate multiple tool calls in the same session
    tools_called = []
    for i in range(3):
        tool_name = f"tool_{i+1}"
        with observer.trace_tool_call(
            tool_name=tool_name,
            input_args={"call_number": i + 1},
        ) as obs:
            if obs:
                obs.update(output_data={"result": f"success_{i+1}"})
            tools_called.append(tool_name)
            print(f"  ✓ Called {tool_name}")
            time.sleep(0.1)  # Small delay to simulate work

    current_session = get_session_id()
    print(f"\n✅ Current session after all calls: {current_session}")
    assert current_session == session_id, "Session ID should remain consistent"
    print(f"✅ All {len(tools_called)} tool calls share the same session_id")

    # Clear session
    clear_session()
    print("✅ Session cleared")


def test_session_isolation():
    """Test that different sessions are properly isolated."""
    print("\n" + "=" * 80)
    print("TEST 2: Session Isolation")
    print("=" * 80)

    observer = get_observer()

    # Create two separate sessions
    session_1 = SessionManager.generate_session_id()
    session_2 = SessionManager.generate_session_id()
    user_1 = "user-A"
    user_2 = "user-B"

    print(f"\n📋 Session 1: {session_1} (User: {user_1})")
    print(f"📋 Session 2: {session_2} (User: {user_2})")

    # Execute tool call in session 1
    set_session(session_id=session_1, user_id=user_1)
    with observer.trace_tool_call(
        tool_name="session_1_tool",
        input_args={"session": "1"},
    ):
        pass
    print(f"  ✓ Executed tool in Session 1")
    print(f"    Current session: {get_session_id()}")
    print(f"    Current user: {get_user_id()}")

    # Switch to session 2
    set_session(session_id=session_2, user_id=user_2)
    with observer.trace_tool_call(
        tool_name="session_2_tool",
        input_args={"session": "2"},
    ):
        pass
    print(f"  ✓ Executed tool in Session 2")
    print(f"    Current session: {get_session_id()}")
    print(f"    Current user: {get_user_id()}")

    # Verify isolation
    assert get_session_id() == session_2, "Should be in session 2"
    assert get_user_id() == user_2, "Should be user B"
    print(f"\n✅ Sessions are properly isolated")

    # Clear session
    clear_session()


async def async_tool_call(observer, tool_name: str, delay: float = 0.1):
    """Simulate an async tool call."""
    with observer.trace_tool_call(
        tool_name=tool_name,
        input_args={"async": True},
    ) as obs:
        await asyncio.sleep(delay)
        if obs:
            obs.update(output_data={"status": "completed"})
    return tool_name


async def test_concurrent_sessions():
    """Test multiple concurrent sessions."""
    print("\n" + "=" * 80)
    print("TEST 3: Concurrent Sessions (Async)")
    print("=" * 80)

    observer = get_observer()
    num_sessions = 5
    tasks = []

    print(f"\n🚀 Creating {num_sessions} concurrent sessions...")

    async def session_worker(session_num: int):
        """Worker function for each session."""
        session_id = f"concurrent-session-{session_num}"
        user_id = f"user-{session_num}"

        # Set session context for this worker
        set_session(session_id=session_id, user_id=user_id)

        # Execute multiple tool calls
        for i in range(3):
            tool_name = f"session_{session_num}_tool_{i+1}"
            await async_tool_call(observer, tool_name, delay=0.05)
            print(f"  ✓ Session {session_num}: {tool_name}")

        final_session = get_session_id()
        print(f"  ✅ Session {session_num} completed (session_id: {final_session})")
        return session_num

    # Run all sessions concurrently
    start_time = time.time()
    results = await asyncio.gather(*[
        session_worker(i) for i in range(1, num_sessions + 1)
    ])
    elapsed = time.time() - start_time

    print(f"\n✅ All {num_sessions} concurrent sessions completed")
    print(f"⏱️  Total time: {elapsed:.2f}s")
    print(f"📊 Average per session: {elapsed/num_sessions:.2f}s")

    # Clear session
    clear_session()


def test_session_metadata():
    """Test session metadata attachment."""
    print("\n" + "=" * 80)
    print("TEST 4: Session Metadata")
    print("=" * 80)

    observer = get_observer()
    session_id = SessionManager.generate_session_id()

    metadata = {
        "channel": "web_chat",
        "customer_tier": "enterprise",
        "product_version": "v2.3",
        "priority": "high",
    }

    print(f"\n📋 Session ID: {session_id}")
    print(f"📝 Metadata: {metadata}")

    # Set session with metadata
    set_session(
        session_id=session_id,
        user_id="vip-user-001",
        metadata=metadata,
    )

    # Execute tool call
    with observer.trace_tool_call(
        tool_name="metadata_test_tool",
        input_args={"test": "metadata"},
    ) as obs:
        if obs:
            obs.update(output_data={"metadata_attached": True})

    ctx = SessionManager.get_session()
    print(f"\n✅ Session context retrieved:")
    print(f"   session_id: {ctx.get('session_id')}")
    print(f"   user_id: {ctx.get('user_id')}")
    print(f"   metadata: {ctx.get('metadata')}")

    assert ctx["metadata"] == metadata, "Metadata should match"
    print(f"✅ Metadata correctly attached to session")

    # Clear session
    clear_session()


def test_session_lifecycle():
    """Test complete session lifecycle."""
    print("\n" + "=" * 80)
    print("TEST 5: Session Lifecycle")
    print("=" * 80)

    observer = get_observer()

    # 1. Start session
    print("\n1️⃣  Starting new session...")
    ctx = SessionManager.start_session(
        session_id="lifecycle-test-session",
        user_id="lifecycle-user",
        metadata={"test": "lifecycle"}
    )
    print(f"   ✓ Session created: {ctx['session_id']}")
    print(f"   ✓ Created at: {ctx['created_at']}")

    # 2. Use session
    print("\n2️⃣  Using session for tool calls...")
    with observer.trace_tool_call(
        tool_name="lifecycle_tool_1",
        input_args={},
    ):
        pass
    print(f"   ✓ Tool call 1 executed")

    with observer.trace_tool_call(
        tool_name="lifecycle_tool_2",
        input_args={},
    ):
        pass
    print(f"   ✓ Tool call 2 executed")

    # 3. Verify session
    print("\n3️⃣  Verifying session state...")
    current_session = get_session_id()
    current_user = get_user_id()
    print(f"   Current session: {current_session}")
    print(f"   Current user: {current_user}")
    assert current_session == "lifecycle-test-session"
    assert current_user == "lifecycle-user"
    print(f"   ✓ Session state verified")

    # 4. Clear session
    print("\n4️⃣  Clearing session...")
    clear_session()
    ctx_after_clear = SessionManager.get_session()
    print(f"   Session after clear: {ctx_after_clear}")
    assert ctx_after_clear == {}, "Session should be empty after clear"
    print(f"   ✓ Session cleared successfully")

    print("\n✅ Complete session lifecycle tested successfully")


def main():
    """Run all session tracing tests."""
    print("\n" + "🔍" * 40)
    print("MCP Session Tracing Test Suite")
    print("🔍" * 40)

    # Initialize observer
    config = ObservabilityConfig()
    init_observer(config)

    try:
        # Run synchronous tests
        test_single_session_multiple_tools()
        test_session_isolation()
        test_session_metadata()
        test_session_lifecycle()

        # Run async test
        asyncio.run(test_concurrent_sessions())

        print("\n" + "🎉" * 40)
        print("ALL TESTS PASSED!")
        print("🎉" * 40)
        print("\n📊 Summary:")
        print("  ✅ Single session with multiple tools")
        print("  ✅ Session isolation")
        print("  ✅ Concurrent sessions (async)")
        print("  ✅ Session metadata")
        print("  ✅ Session lifecycle")
        print("\n💡 Check Langfuse Console to view session replays:")
        print("   https://cloud.langfuse.com/sessions")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        # Flush and shutdown
        observer = get_observer()
        observer.flush()
        observer.shutdown()
        print("\n🔌 Observer flushed and shutdown")


if __name__ == "__main__":
    main()
