"""
Basic tracing examples demonstrating Langfuse integration
Run this to see how traces, spans, and scores work
"""

import asyncio

from core.langfuse_client import flush_traces, langfuse


async def example_1_basic_trace():
    """Example 1: Create a basic trace with spans"""
    print("\n[Example 1] Basic Trace with Spans")
    print("-" * 60)

    # Create a trace
    trace = langfuse.trace(
        name="basic_trace_example",
        session_id="session_001",
        user_id="user_123",
        tags=["example", "basic"],
        metadata={"example_number": 1},
    )

    # Add spans
    with trace.span(name="step_1_processing") as span:
        # Simulate processing
        await asyncio.sleep(0.1)
        span.end(output_data={"result": "processed"})

    with trace.span(name="step_2_validation") as span:
        await asyncio.sleep(0.05)
        span.end(output_data={"valid": True})

    # Add a score
    trace.score(
        name="quality_score", value=0.95, data_type="NUMERIC", comment="High quality processing"
    )

    print("✓ Basic trace created with 2 spans and 1 score")


async def example_2_nested_spans():
    """Example 2: Nested spans for hierarchical tracking"""
    print("\n[Example 2] Nested Spans")
    print("-" * 60)

    trace = langfuse.trace(name="nested_spans_example", session_id="session_002")

    # Parent span
    with trace.span(name="parent_operation") as parent:
        # Child span 1
        with parent.span(name="child_operation_1") as child1:
            await asyncio.sleep(0.1)
            child1.end(output_data={"data": "result_1"})

        # Child span 2
        with parent.span(name="child_operation_2") as child2:
            await asyncio.sleep(0.15)
            child2.end(output_data={"data": "result_2"})

        parent.end(output_data={"children_completed": 2})

    print("✓ Nested spans created (parent with 2 children)")


async def example_3_scoring():
    """Example 3: Different types of scores"""
    print("\n[Example 3] Different Score Types")
    print("-" * 60)

    trace = langfuse.trace(name="scoring_example", session_id="session_003")

    # Numeric score
    trace.score(name="accuracy", value=0.92, data_type="NUMERIC", comment="Model accuracy score")

    # Categorical score
    trace.score(
        name="intent_category",
        value="technical_support",
        data_type="CATEGORICAL",
        comment="Classified intent category",
    )

    # Boolean score
    trace.score(
        name="issue_resolved",
        value=1.0,  # 1.0 = true, 0.0 = false
        data_type="BOOLEAN",
        comment="Issue was successfully resolved",
    )

    print("✓ Created 3 different score types (NUMERIC, CATEGORICAL, BOOLEAN)")


async def example_4_events():
    """Example 4: Adding events to traces"""
    print("\n[Example 4] Events")
    print("-" * 60)

    trace = langfuse.trace(name="events_example", session_id="session_004")

    # Add various events
    trace.event(
        name="user_login",
        input_data={"user_id": "user_123"},
        output_data={"login_successful": True},
    )

    trace.event(
        name="api_call_made",
        input_data={"endpoint": "/api/tickets"},
        output_data={"status_code": 200},
    )

    trace.event(
        name="escalation_triggered", output_data={"reason": "low_confidence", "confidence": 0.45}
    )

    print("✓ Added 3 events to trace")


async def example_5_metadata_and_tags():
    """Example 5: Using metadata and tags for filtering"""
    print("\n[Example 5] Metadata and Tags")
    print("-" * 60)

    trace = langfuse.trace(
        name="metadata_tags_example",
        session_id="session_005",
        user_id="user_456",
        tags=["production", "vip_customer", "api_issue"],
        metadata={
            "channel": "web_chat",
            "customer_tier": "enterprise",
            "product_version": "v2.3",
            "region": "cn-north-1",
            "priority": "high",
        },
    )

    # Update tags dynamically
    langfuse.update_current_trace(tags=["production", "vip_customer", "api_issue", "resolved"])

    # Update metadata
    langfuse.update_current_trace(metadata={"processing_time_ms": 250, "retry_count": 0})

    print("✓ Created trace with rich metadata and tags")
    print("  Tags: production, vip_customer, api_issue, resolved")
    print("  Metadata: channel, customer_tier, product_version, etc.")


async def run_all_examples():
    """Run all tracing examples"""
    print("=" * 60)
    print("Langfuse Basic Tracing Examples")
    print("=" * 60)

    await example_1_basic_trace()
    await example_2_nested_spans()
    await example_3_scoring()
    await example_4_events()
    await example_5_metadata_and_tags()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("Check your Langfuse dashboard to see the traces:")
    print("https://cloud.langfuse.com")
    print("=" * 60)

    # Flush all traces to Langfuse
    flush_traces()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    asyncio.run(run_all_examples())
