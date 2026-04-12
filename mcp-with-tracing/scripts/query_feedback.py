#!/usr/bin/env python3
"""
Query script for feedback aggregation and analysis.

Provides feedback statistics and satisfaction metrics.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.observability.feedback import (
    get_feedback_collector,
    get_acceptance_rate,
    get_feedback_statistics,
)
from src.observability.prompt_versioning import get_prompt_version_manager


def print_feedback_summary():
    """Print comprehensive feedback summary."""
    stats = get_feedback_statistics()

    print("\n" + "=" * 60)
    print("Feedback Summary")
    print("=" * 60)

    print(f"\nTotal Feedback: {stats['total_feedback']}")
    print(f"\nAcceptance Rate: {stats['acceptance_rate']:.1f}%")
    print(f"  - Accepts: {stats['accepts']}")
    print(f"  - Rejects: {stats['rejects']}")

    if stats.get("average_rating"):
        print(f"\nAverage Rating: {stats['average_rating']:.1f}/5")
        print(f"  - Ratings: {stats['ratings_count']}")
        if stats.get("rating_distribution"):
            print(f"  - Distribution:")
            for rating, count in stats["rating_distribution"].items():
                print(f"      {rating} stars: {count}")

    print(f"\nComments: {stats['comments_count']}")


def print_acceptance_trend():
    """Print acceptance rate trend."""
    collector = get_feedback_collector()
    feedback = collector.get_all_feedback()

    if not feedback:
        print("\nNo feedback data available")
        return

    print("\n" + "=" * 60)
    print("Acceptance Trend")
    print("=" * 60)

    accepts = 0
    rejects = 0
    window_size = 5

    for i, fb in enumerate(feedback):
        if fb.feedback_type.value == "accept":
            accepts += 1
        elif fb.feedback_type.value == "reject":
            rejects += 1

        if (i + 1) % window_size == 0:
            total = accepts + rejects
            rate = (accepts / total * 100) if total > 0 else 100
            print(
                f"Last {window_size}: {rate:.0f}% acceptance ({accepts} accept, {rejects} reject)"
            )
            accepts = 0
            rejects = 0

    if accepts + rejects > 0:
        total = accepts + rejects
        rate = (accepts / total * 100) if total > 0 else 100
        print(f"Remaining: {rate:.0f}% acceptance ({accepts} accept, {rejects} reject)")


def print_rejection_reasons():
    """Print rejection reason analysis."""
    collector = get_feedback_collector()
    feedback = collector.get_all_feedback()

    reject_feedback = [f for f in feedback if f.feedback_type.value == "reject"]

    if not reject_feedback:
        print("\nNo rejections recorded")
        return

    print("\n" + "=" * 60)
    print("Rejection Reasons")
    print("=" * 60)

    reasons = {}
    for fb in reject_feedback:
        reason = fb.metadata.get("rejection_reason", "unspecified")
        reasons[reason] = reasons.get(reason, 0) + 1

    for reason, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
        pct = count / len(reject_feedback) * 100
        print(f"  {reason}: {count} ({pct:.0f}%)")


def print_user_satisfaction():
    """Print user satisfaction metrics."""
    stats = get_feedback_statistics()

    print("\n" + "=" * 60)
    print("User Satisfaction Metrics")
    print("=" * 60)

    acceptance_rate = stats["acceptance_rate"]

    if acceptance_rate >= 90:
        rating = "Excellent"
        emoji = "✓✓✓"
    elif acceptance_rate >= 75:
        rating = "Good"
        emoji = "✓✓"
    elif acceptance_rate >= 60:
        rating = "Fair"
        emoji = "✓"
    else:
        rating = "Needs Improvement"
        emoji = "✗"

    print(f"\nOverall Rating: {rating} {emoji}")
    print(f"Acceptance Rate: {acceptance_rate:.1f}%")

    if stats.get("average_rating"):
        print(f"Average Score: {stats['average_rating']:.1f}/5")

    print(f"\nQuality Indicators:")
    print(f"  - Total Responses: {stats['total_feedback']}")
    print(f"  - Positive: {stats['accepts']}")
    print(f"  - Negative: {stats['rejects']}")


def print_version_comparison():
    """Print feedback by prompt version."""
    print("\n" + "=" * 60)
    print("Feedback by Prompt Version")
    print("=" * 60)

    manager = get_prompt_version_manager()
    prompts = manager.list_prompts()

    if not prompts:
        print("\nNo prompts registered")
        return

    for prompt_id in prompts:
        versions = manager.get_all_versions(prompt_id)
        print(f"\n{prompt_id}:")
        for v in versions:
            print(f"  - {v.version}: {v.description or 'No description'}")


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("Feedback Analytics Dashboard")
    print("=" * 60)

    collector = get_feedback_collector()

    if len(collector.get_all_feedback()) == 0:
        print("\nNo feedback collected yet.")
        print("\nUsage:")
        print("  from src.observability.feedback import record_acceptance, record_rejection")
        print("  record_acceptance(trace_id='...', user_id='...')")
        print("  record_rejection(trace_id='...', reason='...')")
        return 0

    print_feedback_summary()
    print_acceptance_trend()
    print_rejection_reasons()
    print_user_satisfaction()
    print_version_comparison()

    print("\n\nQuery Langfuse for detailed analytics:")
    print("  - Navigate to Custom Dashboards")
    print("  - Create Score-based widgets")
    print("  - Filter by session_id or user_id")

    return 0


if __name__ == "__main__":
    sys.exit(main())
