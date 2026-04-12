"""
Dashboard Usage Example

Demonstrates how to use the Dashboard class to generate operational reports.
"""

from datetime import datetime, timedelta

from analysis.dashboard import Dashboard


def main():
    """Example usage of the Dashboard class"""

    # Initialize dashboard
    dashboard = Dashboard(environment="production")

    # Define date range (last 7 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    print("=" * 80)
    print("Customer Service Operations Dashboard - Example Usage")
    print("=" * 80)
    print()

    # Example 1: Get session overview
    print("1. Fetching Session Overview...")
    try:
        session_overview = dashboard.get_session_overview(start_date=start_date, end_date=end_date)
        print(f"   Total Sessions: {session_overview['total_sessions']}")
        print(f"   Avg Duration: {session_overview['avg_duration_minutes']:.2f} min")
        print(f"   Avg Turns/Session: {session_overview['avg_turns_per_session']:.2f}")
        print()
    except Exception as e:
        print(f"   Error: {e}")
        print()

    # Example 2: Get core business metrics
    print("2. Fetching Core Business Metrics...")
    try:
        core_metrics = dashboard.get_core_metrics(start_date=start_date, end_date=end_date)
        print(f"   Resolution Rate: {core_metrics['resolution_rate']:.2%}")
        print(f"   Escalation Rate: {core_metrics['escalation_rate']:.2%}")
        print(f"   First Contact Resolution: {core_metrics['first_contact_resolution']:.2%}")
        print(f"   Avg Satisfaction: {core_metrics['avg_satisfaction']:.2f}/5.0")
        print()
    except Exception as e:
        print(f"   Error: {e}")
        print()

    # Example 3: Get failure analysis
    print("3. Fetching Failure Analysis...")
    try:
        failure_analysis = dashboard.get_failure_analysis(
            start_date=start_date, end_date=end_date, top_n=10
        )
        print(f"   Total Failures: {failure_analysis['total_failures']}")
        print(f"   Overall Failure Rate: {failure_analysis['overall_failure_rate']:.2%}")
        print("   Top Failure Issues:")
        for issue in failure_analysis["top_failure_issues"][:5]:
            print(f"      - {issue['type']}: {issue['count']} occurrences")
        print()
    except Exception as e:
        print(f"   Error: {e}")
        print()

    # Example 4: Get system health
    print("4. Fetching System Health...")
    try:
        system_health = dashboard.get_system_health(start_date=start_date, end_date=end_date)
        print(f"   Model Success Rate: {system_health['model_success_rate']:.2%}")
        print(f"   Avg Response Time: {system_health['avg_response_time_ms']:.0f}ms")
        print(f"   P95 Response Time: {system_health['p95_response_time_ms']:.0f}ms")
        print(f"   Total Tokens Used: {system_health['total_tokens_used']:,}")
        print()
    except Exception as e:
        print(f"   Error: {e}")
        print()

    # Example 5: Export comprehensive report to Markdown
    print("5. Generating Markdown Report...")
    try:
        report = dashboard.export_to_markdown(
            start_date=start_date, end_date=end_date, output_file="dashboard_report.md"
        )
        print("   Report generated successfully!")
        print(f"   Report length: {len(report)} characters")
        print("   Saved to: dashboard_report.md")
        print()
    except Exception as e:
        print(f"   Error: {e}")
        print()

    print("=" * 80)
    print("Dashboard example completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
