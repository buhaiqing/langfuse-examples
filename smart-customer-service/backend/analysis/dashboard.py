"""
Custom Operations Dashboard Module

Provides comprehensive analytics and metrics for customer service operations,
including session overview, core business metrics, failure analysis, and system health.
Uses Langfuse API to fetch traces, scores, and sessions for aggregation and calculation.
"""

import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from langfuse import Langfuse

from core.langfuse_client import get_langfuse_client


class DashboardMetrics:
    """Data class for dashboard metrics results"""

    def __init__(self):
        self.session_overview: dict[str, Any] = {}
        self.core_metrics: dict[str, Any] = {}
        self.failure_analysis: dict[str, Any] = {}
        self.system_health: dict[str, Any] = {}


class Dashboard:
    """
    Custom Operations Dashboard for customer service analytics.

    Provides comprehensive metrics including:
    - Session overview (daily active users, channel distribution, average duration/turns)
    - Core business metrics (resolution rate, escalation rate, satisfaction trends)
    - Failure analysis (top 10 failure issues, high failure rate intents)
    - System health metrics (model success rate, average response time, token usage)

    Attributes:
        client: Langfuse client instance for API access
        environment: Environment filter (e.g., 'production', 'staging')
    """

    def __init__(self, client: Langfuse | None = None, environment: str = "production") -> None:
        """
        Initialize the Dashboard with Langfuse client.

        Args:
            client: Optional Langfuse client instance. If not provided, uses default client.
            environment: Environment filter for data queries. Defaults to 'production'.
        """
        self.client = client or get_langfuse_client()
        self.environment = environment

    def get_session_overview(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve session overview metrics including daily active users,
        channel distribution, and average session duration/turns.

        Args:
            start_date: Start date for the query range. Defaults to 7 days ago.
            end_date: End date for the query range. Defaults to current datetime.
            project_id: Optional project ID filter.

        Returns:
            Dictionary containing session overview metrics:
                - total_sessions: Total number of sessions
                - daily_active_users: Number of unique users per day
                - channel_distribution: Distribution of sessions by channel
                - avg_duration_minutes: Average session duration in minutes
                - avg_turns_per_session: Average number of turns per session
                - peak_hour: Hour with highest activity
                - sessions_by_day: Daily session counts

        Example:
            >>> dashboard = Dashboard()
            >>> overview = dashboard.get_session_overview()
            >>> print(f"Total sessions: {overview['total_sessions']}")
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        # Fetch sessions from Langfuse
        sessions = self._fetch_sessions(
            start_date=start_date, end_date=end_date, project_id=project_id
        )

        # Calculate total sessions
        total_sessions = len(sessions)

        # Calculate daily active users
        daily_users = self._calculate_daily_active_users(sessions)

        # Calculate channel distribution
        channel_distribution = self._calculate_channel_distribution(sessions)

        # Calculate average duration and turns
        avg_duration, avg_turns = self._calculate_session_stats(sessions)

        # Find peak hour
        peak_hour = self._find_peak_hour(sessions)

        # Calculate sessions by day
        sessions_by_day = self._calculate_sessions_by_day(sessions)

        return {
            "total_sessions": total_sessions,
            "daily_active_users": daily_users,
            "channel_distribution": channel_distribution,
            "avg_duration_minutes": round(avg_duration, 2),
            "avg_turns_per_session": round(avg_turns, 2),
            "peak_hour": peak_hour,
            "sessions_by_day": sessions_by_day,
            "query_range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        }

    def get_core_metrics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve core business metrics including resolution rate,
        escalation rate, and satisfaction trends.

        Args:
            start_date: Start date for the query range. Defaults to 7 days ago.
            end_date: End date for the query range. Defaults to current datetime.
            project_id: Optional project ID filter.

        Returns:
            Dictionary containing core business metrics:
                - resolution_rate: Overall issue resolution rate (0-1)
                - escalation_rate: Rate of escalations to human agents (0-1)
                - first_contact_resolution: First contact resolution rate (0-1)
                - avg_satisfaction: Average user satisfaction score (1-5)
                - satisfaction_trend: Daily satisfaction trend over time
                - resolution_by_intent: Resolution rates grouped by intent
                - total_resolved: Total number of resolved issues
                - total_unresolved: Total number of unresolved issues

        Example:
            >>> dashboard = Dashboard()
            >>> metrics = dashboard.get_core_metrics()
            >>> print(f"Resolution rate: {metrics['resolution_rate']:.2%}")
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        # Fetch traces with scores
        traces = self._fetch_traces_with_scores(
            start_date=start_date, end_date=end_date, project_id=project_id
        )

        # Calculate resolution rate
        resolution_rate = self._calculate_resolution_rate(traces)

        # Calculate escalation rate
        escalation_rate = self._calculate_escalation_rate(traces)

        # Calculate first contact resolution
        fcr_rate = self._calculate_first_contact_resolution(traces)

        # Calculate satisfaction metrics
        avg_satisfaction, satisfaction_trend = self._calculate_satisfaction_metrics(traces)

        # Calculate resolution by intent
        resolution_by_intent = self._calculate_resolution_by_intent(traces)

        # Count resolved/unresolved
        total_resolved = sum(1 for t in traces if self._get_score_value(t, "issue_resolved") == 1.0)
        total_unresolved = len(traces) - total_resolved

        return {
            "resolution_rate": round(resolution_rate, 4),
            "escalation_rate": round(escalation_rate, 4),
            "first_contact_resolution": round(fcr_rate, 4),
            "avg_satisfaction": round(avg_satisfaction, 2),
            "satisfaction_trend": satisfaction_trend,
            "resolution_by_intent": resolution_by_intent,
            "total_resolved": total_resolved,
            "total_unresolved": total_unresolved,
            "query_range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        }

    def get_failure_analysis(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        project_id: str | None = None,
        top_n: int = 10,
    ) -> dict[str, Any]:
        """
        Analyze failure patterns including top failure issues and
        high failure rate intents.

        Args:
            start_date: Start date for the query range. Defaults to 7 days ago.
            end_date: End date for the query range. Defaults to current datetime.
            project_id: Optional project ID filter.
            top_n: Number of top failures to return. Defaults to 10.

        Returns:
            Dictionary containing failure analysis:
                - top_failure_issues: Top N most frequent failure types
                - high_failure_intents: Intents with highest failure rates
                - failure_rate_by_type: Failure rates categorized by type
                - failure_trend: Daily failure trend over time
                - total_failures: Total number of failed interactions
                - overall_failure_rate: Overall failure rate (0-1)

        Example:
            >>> dashboard = Dashboard()
            >>> failures = dashboard.get_failure_analysis(top_n=10)
            >>> for issue in failures['top_failure_issues']:
            ...     print(f"{issue['type']}: {issue['count']} occurrences")
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        # Fetch traces with failure information
        traces = self._fetch_traces_with_scores(
            start_date=start_date, end_date=end_date, project_id=project_id
        )

        # Identify failures
        failures = [t for t in traces if self._is_failure(t)]

        # Get top failure issues
        top_failure_issues = self._get_top_failure_issues(failures, top_n)

        # Get high failure rate intents
        high_failure_intents = self._get_high_failure_intents(traces)

        # Calculate failure rate by type
        failure_rate_by_type = self._calculate_failure_rate_by_type(failures)

        # Calculate failure trend
        failure_trend = self._calculate_failure_trend(traces)

        # Calculate overall failure rate
        total_failures = len(failures)
        overall_failure_rate = total_failures / len(traces) if traces else 0.0

        return {
            "top_failure_issues": top_failure_issues,
            "high_failure_intents": high_failure_intents,
            "failure_rate_by_type": failure_rate_by_type,
            "failure_trend": failure_trend,
            "total_failures": total_failures,
            "overall_failure_rate": round(overall_failure_rate, 4),
            "query_range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        }

    def get_system_health(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Monitor system health metrics including model success rate,
        average response time, and token usage.

        Args:
            start_date: Start date for the query range. Defaults to 7 days ago.
            end_date: End date for the query range. Defaults to current datetime.
            project_id: Optional project ID filter.

        Returns:
            Dictionary containing system health metrics:
                - model_success_rate: Overall model invocation success rate (0-1)
                - avg_response_time_ms: Average response time in milliseconds
                - p95_response_time_ms: 95th percentile response time
                - p99_response_time_ms: 99th percentile response time
                - total_tokens_used: Total tokens consumed
                - avg_tokens_per_request: Average tokens per request
                - error_rate: Overall error rate (0-1)
                - latency_trend: Response time trend over time
                - token_usage_by_model: Token usage breakdown by model

        Example:
            >>> dashboard = Dashboard()
            >>> health = dashboard.get_system_health()
            >>> print(f"Model success rate: {health['model_success_rate']:.2%}")
            >>> print(f"Avg response time: {health['avg_response_time_ms']:.0f}ms")
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        # Fetch traces with generation spans
        traces = self._fetch_traces_with_generations(
            start_date=start_date, end_date=end_date, project_id=project_id
        )

        # Calculate model success rate
        model_success_rate = self._calculate_model_success_rate(traces)

        # Calculate response time metrics
        avg_response_time, p95_response_time, p99_response_time = (
            self._calculate_response_time_metrics(traces)
        )

        # Calculate token usage
        total_tokens, avg_tokens, token_by_model = self._calculate_token_usage(traces)

        # Calculate error rate
        error_rate = self._calculate_error_rate(traces)

        # Calculate latency trend
        latency_trend = self._calculate_latency_trend(traces)

        return {
            "model_success_rate": round(model_success_rate, 4),
            "avg_response_time_ms": round(avg_response_time, 2),
            "p95_response_time_ms": round(p95_response_time, 2),
            "p99_response_time_ms": round(p99_response_time, 2),
            "total_tokens_used": total_tokens,
            "avg_tokens_per_request": round(avg_tokens, 2),
            "error_rate": round(error_rate, 4),
            "latency_trend": latency_trend,
            "token_usage_by_model": token_by_model,
            "query_range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        }

    def export_to_markdown(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        project_id: str | None = None,
        output_file: str | None = None,
    ) -> str:
        """
        Export comprehensive dashboard report as Markdown format.

        Generates a complete operational report including all metrics sections:
        session overview, core business metrics, failure analysis, and system health.

        Args:
            start_date: Start date for the query range. Defaults to 7 days ago.
            end_date: End date for the query range. Defaults to current datetime.
            project_id: Optional project ID filter.
            output_file: Optional file path to save the report. If None, returns string only.

        Returns:
            Markdown formatted report string containing all dashboard metrics.

        Example:
            >>> dashboard = Dashboard()
            >>> report = dashboard.export_to_markdown()
            >>> print(report)
            >>> # Or save to file
            >>> dashboard.export_to_markdown(output_file="report.md")
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        # Gather all metrics
        session_overview = self.get_session_overview(start_date, end_date, project_id)
        core_metrics = self.get_core_metrics(start_date, end_date, project_id)
        failure_analysis = self.get_failure_analysis(start_date, end_date, project_id)
        system_health = self.get_system_health(start_date, end_date, project_id)

        # Build markdown report
        report_lines = []

        # Header
        report_lines.append("# Customer Service Operations Dashboard Report")
        report_lines.append("")
        report_lines.append(
            f"**Report Period**: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        )
        report_lines.append(f"**Generated At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**Environment**: {self.environment}")
        if project_id:
            report_lines.append(f"**Project ID**: {project_id}")
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")

        # Section 1: Session Overview
        report_lines.append("## 1. Session Overview")
        report_lines.append("")
        report_lines.append("### Key Metrics")
        report_lines.append("")
        report_lines.append("| Metric | Value |")
        report_lines.append("|--------|-------|")
        report_lines.append(f"| Total Sessions | {session_overview['total_sessions']:,} |")
        report_lines.append(
            f"| Avg Duration | {session_overview['avg_duration_minutes']:.2f} min |"
        )
        report_lines.append(
            f"| Avg Turns/Session | {session_overview['avg_turns_per_session']:.2f} |"
        )
        report_lines.append(f"| Peak Hour | {session_overview['peak_hour']:02d}:00 |")
        report_lines.append("")

        # Channel Distribution
        report_lines.append("### Channel Distribution")
        report_lines.append("")
        report_lines.append("| Channel | Sessions | Percentage |")
        report_lines.append("|---------|----------|------------|")
        for channel, count in sorted(
            session_overview.get("channel_distribution", {}).items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            percentage = (
                count / session_overview["total_sessions"] * 100
                if session_overview["total_sessions"] > 0
                else 0
            )
            report_lines.append(f"| {channel} | {count:,} | {percentage:.1f}% |")
        report_lines.append("")

        # Daily Active Users
        report_lines.append("### Daily Active Users Trend")
        report_lines.append("")
        report_lines.append("| Date | Active Users |")
        report_lines.append("|------|--------------|")
        for date_str, users in sorted(session_overview.get("daily_active_users", {}).items()):
            report_lines.append(f"| {date_str} | {users:,} |")
        report_lines.append("")

        report_lines.append("---")
        report_lines.append("")

        # Section 2: Core Business Metrics
        report_lines.append("## 2. Core Business Metrics")
        report_lines.append("")
        report_lines.append("### Performance Indicators")
        report_lines.append("")
        report_lines.append("| Metric | Value | Status |")
        report_lines.append("|--------|-------|--------|")

        resolution_rate = core_metrics.get("resolution_rate", 0)
        resolution_status = (
            "Good"
            if resolution_rate >= 0.8
            else "Warning" if resolution_rate >= 0.6 else "Critical"
        )
        report_lines.append(f"| Resolution Rate | {resolution_rate:.2%} | {resolution_status} |")

        escalation_rate = core_metrics.get("escalation_rate", 0)
        escalation_status = (
            "Good"
            if escalation_rate <= 0.1
            else "Warning" if escalation_rate <= 0.2 else "Critical"
        )
        report_lines.append(f"| Escalation Rate | {escalation_rate:.2%} | {escalation_status} |")

        fcr_rate = core_metrics.get("first_contact_resolution", 0)
        fcr_status = "Good" if fcr_rate >= 0.7 else "Warning" if fcr_rate >= 0.5 else "Critical"
        report_lines.append(f"| First Contact Resolution | {fcr_rate:.2%} | {fcr_status} |")

        avg_sat = core_metrics.get("avg_satisfaction", 0)
        sat_status = "Good" if avg_sat >= 4.0 else "Warning" if avg_sat >= 3.0 else "Critical"
        report_lines.append(f"| Avg Satisfaction | {avg_sat:.2f}/5.0 | {sat_status} |")
        report_lines.append("")

        # Resolution Summary
        report_lines.append("### Resolution Summary")
        report_lines.append("")
        report_lines.append(f"- **Total Resolved**: {core_metrics.get('total_resolved', 0):,}")
        report_lines.append(f"- **Total Unresolved**: {core_metrics.get('total_unresolved', 0):,}")
        report_lines.append("")

        # Satisfaction Trend
        report_lines.append("### Satisfaction Trend")
        report_lines.append("")
        report_lines.append("| Date | Avg Satisfaction |")
        report_lines.append("|------|------------------|")
        for date_str, sat in sorted(core_metrics.get("satisfaction_trend", {}).items()):
            report_lines.append(f"| {date_str} | {sat:.2f} |")
        report_lines.append("")

        # Resolution by Intent
        report_lines.append("### Resolution Rate by Intent")
        report_lines.append("")
        report_lines.append("| Intent | Resolution Rate | Total Cases |")
        report_lines.append("|--------|-----------------|-------------|")
        for intent, data in sorted(
            core_metrics.get("resolution_by_intent", {}).items(),
            key=lambda x: x[1].get("rate", 0),
            reverse=True,
        ):
            report_lines.append(
                f"| {intent} | {data.get('rate', 0):.2%} | {data.get('total', 0):,} |"
            )
        report_lines.append("")

        report_lines.append("---")
        report_lines.append("")

        # Section 3: Failure Analysis
        report_lines.append("## 3. Failure Analysis")
        report_lines.append("")
        report_lines.append("### Overall Failure Metrics")
        report_lines.append("")
        report_lines.append("| Metric | Value |")
        report_lines.append("|--------|-------|")
        report_lines.append(f"| Total Failures | {failure_analysis.get('total_failures', 0):,} |")
        report_lines.append(
            f"| Overall Failure Rate | {failure_analysis.get('overall_failure_rate', 0):.2%} |"
        )
        report_lines.append("")

        # Top Failure Issues
        report_lines.append("### Top 10 Failure Issues")
        report_lines.append("")
        report_lines.append("| Rank | Failure Type | Count | Percentage |")
        report_lines.append("|------|--------------|-------|------------|")
        for idx, issue in enumerate(failure_analysis.get("top_failure_issues", [])[:10], 1):
            total = failure_analysis.get("total_failures", 1)
            percentage = issue.get("count", 0) / total * 100 if total > 0 else 0
            report_lines.append(
                f"| {idx} | {issue.get('type', 'N/A')} | {issue.get('count', 0):,} | {percentage:.1f}% |"
            )
        report_lines.append("")

        # High Failure Rate Intents
        report_lines.append("### High Failure Rate Intents")
        report_lines.append("")
        report_lines.append("| Intent | Failure Rate | Total Interactions |")
        report_lines.append("|--------|--------------|-------------------|")
        for intent_data in failure_analysis.get("high_failure_intents", []):
            report_lines.append(
                f"| {intent_data.get('intent', 'N/A')} | "
                f"{intent_data.get('failure_rate', 0):.2%} | "
                f"{intent_data.get('total', 0):,} |"
            )
        report_lines.append("")

        # Failure Trend
        report_lines.append("### Failure Trend")
        report_lines.append("")
        report_lines.append("| Date | Failures | Failure Rate |")
        report_lines.append("|------|----------|--------------|")
        for date_str, data in sorted(failure_analysis.get("failure_trend", {}).items()):
            report_lines.append(
                f"| {date_str} | {data.get('count', 0):,} | {data.get('rate', 0):.2%} |"
            )
        report_lines.append("")

        report_lines.append("---")
        report_lines.append("")

        # Section 4: System Health
        report_lines.append("## 4. System Health")
        report_lines.append("")
        report_lines.append("### Model Performance")
        report_lines.append("")
        report_lines.append("| Metric | Value | Status |")
        report_lines.append("|--------|-------|--------|")

        success_rate = system_health.get("model_success_rate", 0)
        success_status = (
            "Healthy" if success_rate >= 0.95 else "Warning" if success_rate >= 0.90 else "Critical"
        )
        report_lines.append(f"| Model Success Rate | {success_rate:.2%} | {success_status} |")

        error_rate = system_health.get("error_rate", 0)
        error_status = (
            "Healthy" if error_rate <= 0.05 else "Warning" if error_rate <= 0.10 else "Critical"
        )
        report_lines.append(f"| Error Rate | {error_rate:.2%} | {error_status} |")
        report_lines.append("")

        # Response Time Metrics
        report_lines.append("### Response Time Metrics")
        report_lines.append("")
        report_lines.append("| Metric | Value (ms) |")
        report_lines.append("|--------|------------|")
        report_lines.append(f"| Average | {system_health.get('avg_response_time_ms', 0):.0f} |")
        report_lines.append(f"| P95 | {system_health.get('p95_response_time_ms', 0):.0f} |")
        report_lines.append(f"| P99 | {system_health.get('p99_response_time_ms', 0):.0f} |")
        report_lines.append("")

        # Token Usage
        report_lines.append("### Token Usage")
        report_lines.append("")
        report_lines.append("| Metric | Value |")
        report_lines.append("|--------|-------|")
        report_lines.append(
            f"| Total Tokens Used | {system_health.get('total_tokens_used', 0):,} |"
        )
        report_lines.append(
            f"| Avg Tokens/Request | {system_health.get('avg_tokens_per_request', 0):.0f} |"
        )
        report_lines.append("")

        # Token Usage by Model
        token_by_model = system_health.get("token_usage_by_model", {})
        if token_by_model:
            report_lines.append("### Token Usage by Model")
            report_lines.append("")
            report_lines.append("| Model | Tokens | Percentage |")
            report_lines.append("|-------|--------|------------|")
            total_tokens = system_health.get("total_tokens_used", 1)
            for model, tokens in sorted(token_by_model.items(), key=lambda x: x[1], reverse=True):
                percentage = tokens / total_tokens * 100 if total_tokens > 0 else 0
                report_lines.append(f"| {model} | {tokens:,} | {percentage:.1f}% |")
            report_lines.append("")

        # Latency Trend
        report_lines.append("### Latency Trend")
        report_lines.append("")
        report_lines.append("| Date | Avg Latency (ms) | P95 Latency (ms) |")
        report_lines.append("|------|------------------|------------------|")
        for date_str, data in sorted(system_health.get("latency_trend", {}).items()):
            report_lines.append(
                f"| {date_str} | {data.get('avg', 0):.0f} | {data.get('p95', 0):.0f} |"
            )
        report_lines.append("")

        report_lines.append("---")
        report_lines.append("")
        report_lines.append("*Report generated by Langfuse Operations Dashboard*")

        # Join all lines
        report = "\n".join(report_lines)

        # Save to file if specified
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"Report saved to: {output_file}")

        return report

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _fetch_sessions(
        self, start_date: datetime, end_date: datetime, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Fetch sessions from Langfuse API.

        Args:
            start_date: Start date for query
            end_date: End date for query
            project_id: Optional project ID filter

        Returns:
            List of session dictionaries
        """
        try:
            sessions = self.client.fetch_sessions(
                page=1, limit=1000, from_timestamp=start_date, to_timestamp=end_date
            )
            return sessions.data if hasattr(sessions, "data") else []
        except Exception as e:
            print(f"Warning: Failed to fetch sessions: {e}")
            return []

    def _fetch_traces_with_scores(
        self, start_date: datetime, end_date: datetime, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Fetch traces with associated scores from Langfuse API.

        Args:
            start_date: Start date for query
            end_date: End date for query
            project_id: Optional project ID filter

        Returns:
            List of trace dictionaries with scores
        """
        try:
            traces = self.client.fetch_traces(
                page=1, limit=1000, from_timestamp=start_date, to_timestamp=end_date
            )
            return traces.data if hasattr(traces, "data") else []
        except Exception as e:
            print(f"Warning: Failed to fetch traces: {e}")
            return []

    def _fetch_traces_with_generations(
        self, start_date: datetime, end_date: datetime, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Fetch traces with generation spans from Langfuse API.

        Args:
            start_date: Start date for query
            end_date: End date for query
            project_id: Optional project ID filter

        Returns:
            List of trace dictionaries with generation data
        """
        try:
            traces = self.client.fetch_traces(
                page=1, limit=1000, from_timestamp=start_date, to_timestamp=end_date
            )
            return traces.data if hasattr(traces, "data") else []
        except Exception as e:
            print(f"Warning: Failed to fetch traces with generations: {e}")
            return []

    def _calculate_daily_active_users(self, sessions: list[dict[str, Any]]) -> dict[str, int]:
        """
        Calculate daily active users from sessions.

        Args:
            sessions: List of session dictionaries

        Returns:
            Dictionary mapping date strings to unique user counts
        """
        daily_users: dict[str, set] = defaultdict(set)

        for session in sessions:
            # Extract date and user ID
            created_at = session.get("createdAt", "")
            user_id = session.get("userId", session.get("id", "unknown"))

            if created_at:
                try:
                    date_str = created_at[:10]  # Extract YYYY-MM-DD
                    daily_users[date_str].add(user_id)
                except (ValueError, IndexError):
                    continue

        # Convert sets to counts
        return {date: len(users) for date, users in sorted(daily_users.items())}

    def _calculate_channel_distribution(self, sessions: list[dict[str, Any]]) -> dict[str, int]:
        """
        Calculate session distribution by channel.

        Args:
            sessions: List of session dictionaries

        Returns:
            Dictionary mapping channel names to session counts
        """
        channel_counts: Counter = Counter()

        for session in sessions:
            # Try to extract channel from metadata or tags
            metadata = session.get("metadata", {})
            channel = metadata.get("channel", metadata.get("source", "unknown"))
            channel_counts[channel] += 1

        return dict(channel_counts)

    def _calculate_session_stats(self, sessions: list[dict[str, Any]]) -> tuple[float, float]:
        """
        Calculate average session duration and turns.

        Args:
            sessions: List of session dictionaries

        Returns:
            Tuple of (average_duration_minutes, average_turns)
        """
        durations = []
        turns = []

        for session in sessions:
            # Calculate duration
            created_at = session.get("createdAt")
            updated_at = session.get("updatedAt")

            if created_at and updated_at:
                try:
                    start = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    end = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    duration_minutes = (end - start).total_seconds() / 60
                    durations.append(duration_minutes)
                except (ValueError, TypeError):
                    pass

            # Get turn count from metadata
            metadata = session.get("metadata", {})
            turn_count = metadata.get("turn_count", metadata.get("messageCount", 0))
            if turn_count:
                turns.append(float(turn_count))

        avg_duration = statistics.mean(durations) if durations else 0.0
        avg_turns = statistics.mean(turns) if turns else 0.0

        return avg_duration, avg_turns

    def _find_peak_hour(self, sessions: list[dict[str, Any]]) -> int:
        """
        Find the hour with highest session activity.

        Args:
            sessions: List of session dictionaries

        Returns:
            Hour (0-23) with most sessions
        """
        hour_counts: Counter = Counter()

        for session in sessions:
            created_at = session.get("createdAt", "")
            if created_at:
                try:
                    # Extract hour from ISO timestamp
                    hour = int(created_at[11:13])
                    hour_counts[hour] += 1
                except (ValueError, IndexError):
                    continue

        if not hour_counts:
            return 0

        return hour_counts.most_common(1)[0][0]

    def _calculate_sessions_by_day(self, sessions: list[dict[str, Any]]) -> dict[str, int]:
        """
        Calculate session counts by day.

        Args:
            sessions: List of session dictionaries

        Returns:
            Dictionary mapping date strings to session counts
        """
        daily_counts: Counter = Counter()

        for session in sessions:
            created_at = session.get("createdAt", "")
            if created_at:
                try:
                    date_str = created_at[:10]
                    daily_counts[date_str] += 1
                except (ValueError, IndexError):
                    continue

        return dict(sorted(daily_counts.items()))

    def _get_score_value(self, trace: dict[str, Any], score_name: str) -> float | None:
        """
        Extract score value from trace by score name.

        Args:
            trace: Trace dictionary
            score_name: Name of the score to find

        Returns:
            Score value if found, None otherwise
        """
        scores = trace.get("scores", [])
        for score in scores:
            if score.get("name") == score_name:
                return score.get("value")
        return None

    def _calculate_resolution_rate(self, traces: list[dict[str, Any]]) -> float:
        """
        Calculate overall issue resolution rate.

        Args:
            traces: List of trace dictionaries

        Returns:
            Resolution rate (0-1)
        """
        if not traces:
            return 0.0

        resolved_count = sum(1 for t in traces if self._get_score_value(t, "issue_resolved") == 1.0)

        return resolved_count / len(traces)

    def _calculate_escalation_rate(self, traces: list[dict[str, Any]]) -> float:
        """
        Calculate escalation rate to human agents.

        Args:
            traces: List of trace dictionaries

        Returns:
            Escalation rate (0-1)
        """
        if not traces:
            return 0.0

        escalated_count = sum(
            1 for t in traces if self._get_score_value(t, "escalation_required") == 1.0
        )

        return escalated_count / len(traces)

    def _calculate_first_contact_resolution(self, traces: list[dict[str, Any]]) -> float:
        """
        Calculate first contact resolution rate.

        Args:
            traces: List of trace dictionaries

        Returns:
            First contact resolution rate (0-1)
        """
        if not traces:
            return 0.0

        fcr_count = sum(
            1 for t in traces if self._get_score_value(t, "first_contact_resolution") == 1.0
        )

        return fcr_count / len(traces)

    def _calculate_satisfaction_metrics(
        self, traces: list[dict[str, Any]]
    ) -> tuple[float, dict[str, float]]:
        """
        Calculate satisfaction metrics and trends.

        Args:
            traces: List of trace dictionaries

        Returns:
            Tuple of (average_satisfaction, daily_trend)
        """
        satisfaction_scores = []
        daily_satisfaction: dict[str, list[float]] = defaultdict(list)

        for trace in traces:
            sat_score = self._get_score_value(trace, "user_satisfaction")
            if sat_score is not None:
                satisfaction_scores.append(sat_score)

                # Add to daily trend
                created_at = trace.get("timestamp", "")
                if created_at:
                    try:
                        date_str = created_at[:10]
                        daily_satisfaction[date_str].append(sat_score)
                    except (ValueError, IndexError):
                        pass

        avg_satisfaction = statistics.mean(satisfaction_scores) if satisfaction_scores else 0.0

        # Calculate daily averages
        satisfaction_trend = {
            date: statistics.mean(scores) for date, scores in sorted(daily_satisfaction.items())
        }

        return avg_satisfaction, satisfaction_trend

    def _calculate_resolution_by_intent(
        self, traces: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """
        Calculate resolution rates grouped by intent.

        Args:
            traces: List of trace dictionaries

        Returns:
            Dictionary mapping intents to resolution statistics
        """
        intent_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"resolved": 0, "total": 0})

        for trace in traces:
            # Extract intent from metadata or tags
            metadata = trace.get("metadata", {})
            intent = metadata.get("intent", metadata.get("detected_intent", "unknown"))

            intent_stats[intent]["total"] += 1

            if self._get_score_value(trace, "issue_resolved") == 1.0:
                intent_stats[intent]["resolved"] += 1

        # Calculate rates
        result = {}
        for intent, stats in intent_stats.items():
            total = stats["total"]
            resolved = stats["resolved"]
            result[intent] = {
                "rate": resolved / total if total > 0 else 0.0,
                "resolved": resolved,
                "total": total,
            }

        return result

    def _is_failure(self, trace: dict[str, Any]) -> bool:
        """
        Determine if a trace represents a failure.

        Args:
            trace: Trace dictionary

        Returns:
            True if the trace indicates a failure
        """
        # Check for explicit failure type
        failure_type = self._get_score_value(trace, "failure_type")
        if failure_type is not None and failure_type != "none":
            return True

        # Check if issue was not resolved
        issue_resolved = self._get_score_value(trace, "issue_resolved")
        if issue_resolved == 0.0:
            return True

        # Check for escalation
        escalation = self._get_score_value(trace, "escalation_required")
        if escalation == 1.0:
            return True

        return False

    def _get_top_failure_issues(
        self, failures: list[dict[str, Any]], top_n: int
    ) -> list[dict[str, Any]]:
        """
        Get top N most frequent failure types.

        Args:
            failures: List of failed trace dictionaries
            top_n: Number of top failures to return

        Returns:
            List of dictionaries with failure type and count
        """
        failure_types: Counter = Counter()

        for trace in failures:
            failure_type = self._get_score_value(trace, "failure_type")
            if failure_type and failure_type != "none":
                failure_types[str(failure_type)] += 1
            else:
                failure_types["unresolved_issue"] += 1

        return [
            {"type": ftype, "count": count} for ftype, count in failure_types.most_common(top_n)
        ]

    def _get_high_failure_intents(self, traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Get intents with highest failure rates.

        Args:
            traces: List of trace dictionaries

        Returns:
            List of intents sorted by failure rate (descending)
        """
        intent_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"failures": 0, "total": 0})

        for trace in traces:
            metadata = trace.get("metadata", {})
            intent = metadata.get("intent", metadata.get("detected_intent", "unknown"))

            intent_stats[intent]["total"] += 1

            if self._is_failure(trace):
                intent_stats[intent]["failures"] += 1

        # Calculate failure rates and sort
        result = []
        for intent, stats in intent_stats.items():
            if stats["total"] >= 5:  # Minimum sample size
                failure_rate = stats["failures"] / stats["total"]
                result.append(
                    {
                        "intent": intent,
                        "failure_rate": failure_rate,
                        "failures": stats["failures"],
                        "total": stats["total"],
                    }
                )

        # Sort by failure rate descending
        result.sort(key=lambda x: x["failure_rate"], reverse=True)

        return result[:10]  # Return top 10

    def _calculate_failure_rate_by_type(self, failures: list[dict[str, Any]]) -> dict[str, int]:
        """
        Calculate failure counts by type.

        Args:
            failures: List of failed trace dictionaries

        Returns:
            Dictionary mapping failure types to counts
        """
        type_counts: Counter = Counter()

        for trace in failures:
            failure_type = self._get_score_value(trace, "failure_type")
            if failure_type:
                type_counts[str(failure_type)] += 1
            else:
                type_counts["unknown"] += 1

        return dict(type_counts)

    def _calculate_failure_trend(self, traces: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """
        Calculate daily failure trend.

        Args:
            traces: List of trace dictionaries

        Returns:
            Dictionary mapping dates to failure statistics
        """
        daily_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"failures": 0, "total": 0})

        for trace in traces:
            created_at = trace.get("timestamp", "")
            if created_at:
                try:
                    date_str = created_at[:10]
                    daily_stats[date_str]["total"] += 1

                    if self._is_failure(trace):
                        daily_stats[date_str]["failures"] += 1
                except (ValueError, IndexError):
                    pass

        # Calculate rates
        result = {}
        for date, stats in sorted(daily_stats.items()):
            total = stats["total"]
            failures = stats["failures"]
            result[date] = {
                "count": failures,
                "total": total,
                "rate": failures / total if total > 0 else 0.0,
            }

        return result

    def _calculate_model_success_rate(self, traces: list[dict[str, Any]]) -> float:
        """
        Calculate model invocation success rate.

        Args:
            traces: List of trace dictionaries

        Returns:
            Success rate (0-1)
        """
        if not traces:
            return 0.0

        successful = 0
        total = 0

        for trace in traces:
            # Check generations within trace
            observations = trace.get("observations", [])
            for obs in observations:
                if obs.get("type") == "GENERATION":
                    total += 1
                    # Check if generation completed successfully
                    if obs.get("completionStartTime") and not obs.get("level") == "ERROR":
                        successful += 1

        return successful / total if total > 0 else 1.0

    def _calculate_response_time_metrics(
        self, traces: list[dict[str, Any]]
    ) -> tuple[float, float, float]:
        """
        Calculate response time statistics.

        Args:
            traces: List of trace dictionaries

        Returns:
            Tuple of (average, p95, p99) response times in ms
        """
        latencies = []

        for trace in traces:
            # Get latency from metadata or calculate from timestamps
            metadata = trace.get("metadata", {})
            latency = metadata.get("response_latency_ms")

            if latency is None:
                # Try to calculate from trace timestamps
                start_time = trace.get("timestamp")
                end_time = trace.get("release")  # Sometimes used as completion marker

                if start_time and end_time:
                    try:
                        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                        latency = (end - start).total_seconds() * 1000
                    except (ValueError, TypeError):
                        pass

            if latency is not None:
                latencies.append(float(latency))

        if not latencies:
            return 0.0, 0.0, 0.0

        avg_latency = statistics.mean(latencies)
        sorted_latencies = sorted(latencies)

        # Calculate percentiles
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)

        p95_latency = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
        p99_latency = sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)]

        return avg_latency, p95_latency, p99_latency

    def _calculate_token_usage(
        self, traces: list[dict[str, Any]]
    ) -> tuple[int, float, dict[str, int]]:
        """
        Calculate token usage statistics.

        Args:
            traces: List of trace dictionaries

        Returns:
            Tuple of (total_tokens, avg_tokens, token_usage_by_model)
        """
        total_tokens = 0
        request_count = 0
        model_tokens: dict[str, int] = defaultdict(int)

        for trace in traces:
            observations = trace.get("observations", [])
            for obs in observations:
                if obs.get("type") == "GENERATION":
                    usage = obs.get("usage", {})
                    prompt_tokens = usage.get("promptTokens", 0) or 0
                    completion_tokens = usage.get("completionTokens", 0) or 0
                    total = prompt_tokens + completion_tokens

                    if total > 0:
                        total_tokens += total
                        request_count += 1

                        # Track by model
                        model_name = obs.get("model", "unknown")
                        model_tokens[model_name] += total

        avg_tokens = total_tokens / request_count if request_count > 0 else 0.0

        return total_tokens, avg_tokens, dict(model_tokens)

    def _calculate_error_rate(self, traces: list[dict[str, Any]]) -> float:
        """
        Calculate overall error rate.

        Args:
            traces: List of trace dictionaries

        Returns:
            Error rate (0-1)
        """
        if not traces:
            return 0.0

        error_count = sum(1 for t in traces if t.get("level") == "ERROR")

        return error_count / len(traces)

    def _calculate_latency_trend(self, traces: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
        """
        Calculate daily latency trend.

        Args:
            traces: List of trace dictionaries

        Returns:
            Dictionary mapping dates to latency statistics
        """
        daily_latencies: dict[str, list[float]] = defaultdict(list)

        for trace in traces:
            metadata = trace.get("metadata", {})
            latency = metadata.get("response_latency_ms")

            if latency is None:
                # Try to calculate from timestamps
                start_time = trace.get("timestamp")
                if start_time:
                    try:
                        # Use observation duration if available
                        observations = trace.get("observations", [])
                        for obs in observations:
                            if obs.get("type") == "GENERATION":
                                start = obs.get("startTime")
                                end = obs.get("endTime")
                                if start and end:
                                    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                                    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                                    latency = (end_dt - start_dt).total_seconds() * 1000
                                    break
                    except (ValueError, TypeError):
                        pass

            if latency is not None:
                created_at = trace.get("timestamp", "")
                if created_at:
                    try:
                        date_str = created_at[:10]
                        daily_latencies[date_str].append(float(latency))
                    except (ValueError, IndexError):
                        pass

        # Calculate daily statistics
        result = {}
        for date, latencies in sorted(daily_latencies.items()):
            if latencies:
                sorted_lat = sorted(latencies)
                p95_idx = int(len(sorted_lat) * 0.95)
                result[date] = {
                    "avg": statistics.mean(latencies),
                    "p95": sorted_lat[min(p95_idx, len(sorted_lat) - 1)],
                    "count": len(latencies),
                }

        return result
