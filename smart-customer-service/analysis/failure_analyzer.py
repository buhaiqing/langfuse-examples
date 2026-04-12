"""
Failure analysis engine for automated collection and root cause analysis of low-score sessions.

This module provides comprehensive failure analysis capabilities including:
- Automated collection of low-score cases from Langfuse
- Multi-dimensional aggregation statistics (by failure type, intent, channel, time)
- Root cause drill-down analysis
- Markdown report generation

Usage:
    analyzer = FailureAnalyzer()
    cases = analyzer.collect_failure_cases(threshold=0.3, limit=100)
    patterns = analyzer.analyze_failure_patterns(cases)
    report = analyzer.generate_failure_report(patterns)
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from core.langfuse_client import langfuse
from core.scoring import FAILURE_TYPE, ISSUE_RESOLVED, USER_SATISFACTION

# Default failure threshold constants
DEFAULT_SCORE_THRESHOLD = 0.3
DEFAULT_CASE_LIMIT = 100
DEFAULT_TIME_RANGE_DAYS = 7


class FailureCase:
    """
    Represents a single failure case extracted from Langfuse trace.

    Attributes:
        trace_id: Unique trace identifier
        session_id: Session identifier for grouping related traces
        user_id: Anonymized user identifier
        timestamp: When the trace was created
        scores: Dictionary of all scores associated with this trace
        metadata: Additional trace metadata
        input_data: Trace input data
        output_data: Trace output data
        tags: List of tags attached to the trace
    """

    def __init__(
        self,
        trace_id: str,
        session_id: str | None = None,
        user_id: str | None = None,
        timestamp: datetime | None = None,
        scores: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        input_data: Any | None = None,
        output_data: Any | None = None,
        tags: list[str] | None = None,
    ):
        """
        Initialize a failure case instance.

        Args:
            trace_id: Unique trace identifier
            session_id: Session identifier for grouping related traces
            user_id: Anonymized user identifier
            timestamp: When the trace was created
            scores: Dictionary of all scores associated with this trace
            metadata: Additional trace metadata
            input_data: Trace input data
            output_data: Trace output data
            tags: List of tags attached to the trace
        """
        self.trace_id = trace_id
        self.session_id = session_id
        self.user_id = user_id
        self.timestamp = timestamp or datetime.now()
        self.scores = scores or {}
        self.metadata = metadata or {}
        self.input_data = input_data
        self.output_data = output_data
        self.tags = tags or []

    @property
    def is_resolved(self) -> bool:
        """Check if the issue was resolved based on scores."""
        return bool(self.scores.get(ISSUE_RESOLVED, 0))

    @property
    def satisfaction_rating(self) -> float | None:
        """Get user satisfaction rating if available."""
        return self.scores.get(USER_SATISFACTION)

    @property
    def failure_type(self) -> str | None:
        """Get failure type classification if available."""
        return self.scores.get(FAILURE_TYPE)

    @property
    def min_score(self) -> float:
        """Get minimum numeric score across all dimensions."""
        numeric_scores = [
            v for k, v in self.scores.items() if isinstance(v, (int, float)) and 0 <= v <= 1
        ]
        return min(numeric_scores) if numeric_scores else 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert failure case to dictionary representation."""
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "scores": self.scores,
            "metadata": self.metadata,
            "tags": self.tags,
            "is_resolved": self.is_resolved,
            "failure_type": self.failure_type,
            "min_score": self.min_score,
        }

    def __repr__(self) -> str:
        return f"FailureCase(trace_id={self.trace_id}, failure_type={self.failure_type})"


class FailurePattern:
    """
    Represents an aggregated failure pattern identified through analysis.

    Attributes:
        pattern_name: Descriptive name of the pattern
        count: Number of occurrences
        percentage: Percentage of total failures
        avg_score: Average score for this pattern
        common_intents: Most frequent intents in this pattern
        common_channels: Most frequent channels in this pattern
        time_distribution: Temporal distribution of occurrences
        sample_cases: Representative sample cases
    """

    def __init__(
        self,
        pattern_name: str,
        count: int,
        total_failures: int,
        avg_score: float,
        common_intents: list[tuple[str, int]] | None = None,
        common_channels: list[tuple[str, int]] | None = None,
        time_distribution: dict[str, int] | None = None,
        sample_cases: list[FailureCase] | None = None,
    ):
        """
        Initialize a failure pattern instance.

        Args:
            pattern_name: Descriptive name of the pattern
            count: Number of occurrences
            total_failures: Total number of failures for percentage calculation
            avg_score: Average score for this pattern
            common_intents: Most frequent intents as (intent, count) tuples
            common_channels: Most frequent channels as (channel, count) tuples
            time_distribution: Temporal distribution as {time_bucket: count}
            sample_cases: Representative sample cases
        """
        self.pattern_name = pattern_name
        self.count = count
        self.percentage = (count / total_failures * 100) if total_failures > 0 else 0
        self.avg_score = avg_score
        self.common_intents = common_intents or []
        self.common_channels = common_channels or []
        self.time_distribution = time_distribution or {}
        self.sample_cases = sample_cases or []

    def to_dict(self) -> dict[str, Any]:
        """Convert failure pattern to dictionary representation."""
        return {
            "pattern_name": self.pattern_name,
            "count": self.count,
            "percentage": round(self.percentage, 2),
            "avg_score": round(self.avg_score, 3),
            "common_intents": self.common_intents[:5],
            "common_channels": self.common_channels[:5],
            "time_distribution": self.time_distribution,
            "sample_count": len(self.sample_cases),
        }

    def __repr__(self) -> str:
        return f"FailurePattern({self.pattern_name}, count={self.count}, avg_score={self.avg_score:.2f})"


class FailureAnalyzer:
    """
    Comprehensive failure analysis engine for Langfuse-traced customer service interactions.

    This analyzer automatically collects low-score cases, performs multi-dimensional
    aggregation, conducts root cause analysis, and generates detailed reports.

    Attributes:
        default_threshold: Default score threshold for identifying failures
        default_limit: Default maximum number of cases to collect
        default_time_range_days: Default time range in days for data collection
    """

    def __init__(
        self,
        default_threshold: float = DEFAULT_SCORE_THRESHOLD,
        default_limit: int = DEFAULT_CASE_LIMIT,
        default_time_range_days: int = DEFAULT_TIME_RANGE_DAYS,
    ):
        """
        Initialize the failure analyzer with configuration parameters.

        Args:
            default_threshold: Score threshold below which cases are considered failures (0-1)
            default_limit: Maximum number of cases to retrieve per query
            default_time_range_days: Default time range in days for data collection
        """
        self.default_threshold = default_threshold
        self.default_limit = default_limit
        self.default_time_range_days = default_time_range_days

    def collect_failure_cases(
        self,
        threshold: float | None = None,
        limit: int | None = None,
        time_range_days: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        filter_tags: list[str] | None = None,
        filter_session_id: str | None = None,
        filter_user_id: str | None = None,
    ) -> list[FailureCase]:
        """
        Collect failure cases from Langfuse based on score threshold filtering.

        Retrieves traces with scores below the specified threshold, indicating
        potential failures in customer service interactions.

        Args:
            threshold: Score threshold below which cases are considered failures (0-1).
                      Defaults to self.default_threshold if not provided.
            limit: Maximum number of cases to retrieve.
                  Defaults to self.default_limit if not provided.
            time_range_days: Number of days to look back for data collection.
                            Mutually exclusive with start_time/end_time.
            start_time: Start time for data collection window.
                       Mutually exclusive with time_range_days.
            end_time: End time for data collection window.
                     Defaults to current time if not provided.
            filter_tags: Optional list of tags to filter traces by.
            filter_session_id: Optional session ID to filter traces by.
            filter_user_id: Optional user ID to filter traces by.

        Returns:
            List of FailureCase objects representing low-score interactions.

        Raises:
            ValueError: If both time_range_days and start_time are provided.

        Example:
            >>> analyzer = FailureAnalyzer()
            >>> failures = analyzer.collect_failure_cases(
            ...     threshold=0.3,
            ...     limit=50,
            ...     time_range_days=7
            ... )
            >>> print(f"Found {len(failures)} failure cases")
        """
        if threshold is None:
            threshold = self.default_threshold
        if limit is None:
            limit = self.default_limit

        # Calculate time range
        if time_range_days is not None and start_time is not None:
            raise ValueError("Cannot specify both time_range_days and start_time")

        if start_time is None:
            days = time_range_days or self.default_time_range_days
            start_time = datetime.now() - timedelta(days=days)

        if end_time is None:
            end_time = datetime.now()

        # Fetch traces from Langfuse
        traces = langfuse.fetch_traces(
            page=1,
            limit=limit,
            from_timestamp=start_time,
            to_timestamp=end_time,
            tags=filter_tags,
            session_id=filter_session_id,
            user_id=filter_user_id,
        )

        failure_cases = []

        for trace in traces.data:
            # Get scores for this trace
            scores = self._extract_trace_scores(trace.id)

            # Check if any score indicates failure
            if self._is_failure_case(scores, threshold):
                failure_case = FailureCase(
                    trace_id=trace.id,
                    session_id=trace.sessionId,
                    user_id=trace.userId,
                    timestamp=trace.timestamp,
                    scores=scores,
                    metadata=trace.metadata or {},
                    input_data=trace.input,
                    output_data=trace.output,
                    tags=trace.tags or [],
                )
                failure_cases.append(failure_case)

        # Sort by minimum score (worst first)
        failure_cases.sort(key=lambda x: x.min_score)

        return failure_cases

    def analyze_failure_patterns(self, failure_cases: list[FailureCase]) -> dict[str, Any]:
        """
        Perform multi-dimensional aggregation analysis on failure cases.

        Analyzes failure patterns across multiple dimensions including:
        - Failure type distribution
        - Intent-based clustering
        - Channel/source analysis
        - Temporal patterns
        - User impact assessment

        Args:
            failure_cases: List of failure cases to analyze.

        Returns:
            Dictionary containing aggregated analysis results with keys:
            - summary: Overall statistics
            - by_failure_type: Distribution by failure type
            - by_intent: Distribution by user intent
            - by_channel: Distribution by communication channel
            - by_time: Temporal distribution
            - top_patterns: Identified recurring patterns
            - severity_distribution: Distribution by severity level

        Example:
            >>> cases = analyzer.collect_failure_cases(threshold=0.3)
            >>> patterns = analyzer.analyze_failure_patterns(cases)
            >>> print(patterns['summary']['total_failures'])
        """
        if not failure_cases:
            return self._empty_analysis_result()

        total = len(failure_cases)

        # Aggregate by different dimensions
        by_failure_type = self._aggregate_by_field(
            failure_cases, field="failure_type", default_value="unclassified"
        )

        by_intent = self._aggregate_by_metadata(failure_cases, metadata_key="intent")

        by_channel = self._aggregate_by_metadata(failure_cases, metadata_key="channel")

        by_time = self._aggregate_by_time(failure_cases)

        # Identify top patterns
        top_patterns = self._identify_top_patterns(failure_cases, total)

        # Calculate severity distribution
        severity_dist = self._calculate_severity_distribution(failure_cases)

        # Build result
        result = {
            "summary": {
                "total_failures": total,
                "avg_min_score": sum(c.min_score for c in failure_cases) / total,
                "resolution_rate": sum(1 for c in failure_cases if c.is_resolved) / total,
                "unique_users": len(set(c.user_id for c in failure_cases if c.user_id)),
                "unique_sessions": len(set(c.session_id for c in failure_cases if c.session_id)),
                "time_range": {
                    "start": min(c.timestamp for c in failure_cases).isoformat(),
                    "end": max(c.timestamp for c in failure_cases).isoformat(),
                },
            },
            "by_failure_type": by_failure_type,
            "by_intent": by_intent,
            "by_channel": by_channel,
            "by_time": by_time,
            "top_patterns": [p.to_dict() for p in top_patterns],
            "severity_distribution": severity_dist,
        }

        return result

    def get_root_cause_analysis(self, failure_case: FailureCase) -> dict[str, Any]:
        """
        Perform root cause analysis for a specific failure case.

        Conducts deep-dive analysis to identify the underlying causes of failure
        by examining scores, metadata, conversation flow, and contextual factors.

        Args:
            failure_case: The failure case to analyze.

        Returns:
            Dictionary containing root cause analysis with keys:
            - case_summary: Basic case information
            - score_breakdown: Detailed score analysis
            - probable_causes: List of identified probable causes with confidence
            - contributing_factors: Factors that contributed to the failure
            - recommendations: Suggested actions to prevent similar failures
            - related_cases: Similar failure cases for pattern matching

        Example:
            >>> cases = analyzer.collect_failure_cases(threshold=0.3)
            >>> if cases:
            ...     analysis = analyzer.get_root_cause_analysis(cases[0])
            ...     print(analysis['probable_causes'])
        """
        # Extract score breakdown
        score_breakdown = self._analyze_score_breakdown(failure_case)

        # Identify probable causes
        probable_causes = self._identify_probable_causes(failure_case, score_breakdown)

        # Determine contributing factors
        contributing_factors = self._identify_contributing_factors(failure_case)

        # Generate recommendations
        recommendations = self._generate_recommendations(probable_causes, contributing_factors)

        # Find related cases
        related_cases = self._find_related_cases(failure_case)

        result = {
            "case_summary": {
                "trace_id": failure_case.trace_id,
                "session_id": failure_case.session_id,
                "user_id": failure_case.user_id,
                "timestamp": failure_case.timestamp.isoformat(),
                "failure_type": failure_case.failure_type,
                "is_resolved": failure_case.is_resolved,
                "min_score": failure_case.min_score,
            },
            "score_breakdown": score_breakdown,
            "probable_causes": probable_causes,
            "contributing_factors": contributing_factors,
            "recommendations": recommendations,
            "related_cases": [
                {"trace_id": rc.trace_id, "similarity": rc.get("similarity", 0)}
                for rc in related_cases[:5]
            ],
        }

        return result

    def generate_failure_report(
        self,
        analysis_result: dict[str, Any],
        title: str = "Failure Analysis Report",
        include_recommendations: bool = True,
        output_file: str | None = None,
    ) -> str:
        """
        Generate a comprehensive Markdown-formatted failure analysis report.

        Creates a detailed report covering all aspects of the failure analysis,
        including executive summary, detailed breakdowns, patterns, and recommendations.

        Args:
            analysis_result: Result from analyze_failure_patterns() method.
            title: Report title.
            include_recommendations: Whether to include recommendation section.
            output_file: Optional file path to write the report. If None, returns string only.

        Returns:
            Markdown-formatted report string.

        Example:
            >>> cases = analyzer.collect_failure_cases(threshold=0.3)
            >>> patterns = analyzer.analyze_failure_patterns(cases)
            >>> report = analyzer.generate_failure_report(
            ...     patterns,
            ...     title="Weekly Failure Analysis",
            ...     output_file="reports/failure_report.md"
            ... )
        """
        lines = []

        # Title and metadata
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        summary = analysis_result.get("summary", {})
        lines.append(f"- **Total Failures Analyzed:** {summary.get('total_failures', 0)}")
        lines.append(f"- **Average Minimum Score:** {summary.get('avg_min_score', 0):.3f}")
        lines.append(f"- **Resolution Rate:** {summary.get('resolution_rate', 0):.1%}")
        lines.append(f"- **Unique Users Affected:** {summary.get('unique_users', 0)}")
        lines.append(f"- **Unique Sessions:** {summary.get('unique_sessions', 0)}")

        time_range = summary.get("time_range", {})
        if time_range:
            lines.append(
                f"- **Analysis Period:** {time_range.get('start', 'N/A')} to {time_range.get('end', 'N/A')}"
            )
        lines.append("")

        # Severity Distribution
        lines.append("## Severity Distribution")
        lines.append("")
        severity_dist = analysis_result.get("severity_distribution", {})
        if severity_dist:
            lines.append("| Severity Level | Count | Percentage |")
            lines.append("|---------------|-------|------------|")
            for level, data in sorted(severity_dist.items()):
                lines.append(f"| {level} | {data['count']} | {data['percentage']:.1f}% |")
            lines.append("")

        # Failure Type Breakdown
        lines.append("## Failure Type Distribution")
        lines.append("")
        by_failure_type = analysis_result.get("by_failure_type", {})
        if by_failure_type:
            lines.append("| Failure Type | Count | Percentage | Avg Score |")
            lines.append("|-------------|-------|------------|-----------|")
            for ftype, data in sorted(
                by_failure_type.items(), key=lambda x: x[1]["count"], reverse=True
            ):
                lines.append(
                    f"| {ftype} | {data['count']} | {data['percentage']:.1f}% | {data['avg_score']:.3f} |"
                )
            lines.append("")

        # Intent Analysis
        lines.append("## Intent-Based Analysis")
        lines.append("")
        by_intent = analysis_result.get("by_intent", {})
        if by_intent:
            lines.append("| Intent | Count | Percentage |")
            lines.append("|--------|-------|------------|")
            for intent, data in sorted(
                by_intent.items(), key=lambda x: x[1]["count"], reverse=True
            )[:10]:
                lines.append(f"| {intent} | {data['count']} | {data['percentage']:.1f}% |")
            lines.append("")

        # Channel Analysis
        lines.append("## Channel Distribution")
        lines.append("")
        by_channel = analysis_result.get("by_channel", {})
        if by_channel:
            lines.append("| Channel | Count | Percentage |")
            lines.append("|---------|-------|------------|")
            for channel, data in sorted(
                by_channel.items(), key=lambda x: x[1]["count"], reverse=True
            ):
                lines.append(f"| {channel} | {data['count']} | {data['percentage']:.1f}% |")
            lines.append("")

        # Temporal Patterns
        lines.append("## Temporal Patterns")
        lines.append("")
        by_time = analysis_result.get("by_time", {})
        if by_time:
            lines.append("| Time Bucket | Count |")
            lines.append("|------------|-------|")
            for bucket, count in sorted(by_time.items()):
                lines.append(f"| {bucket} | {count} |")
            lines.append("")

        # Top Patterns
        lines.append("## Top Failure Patterns")
        lines.append("")
        top_patterns = analysis_result.get("top_patterns", [])
        if top_patterns:
            for i, pattern in enumerate(top_patterns[:5], 1):
                lines.append(f"### Pattern {i}: {pattern['pattern_name']}")
                lines.append("")
                lines.append(
                    f"- **Occurrences:** {pattern['count']} ({pattern['percentage']:.1f}%)"
                )
                lines.append(f"- **Average Score:** {pattern['avg_score']:.3f}")

                if pattern.get("common_intents"):
                    intents_str = ", ".join(
                        [f"{intent} ({cnt})" for intent, cnt in pattern["common_intents"][:3]]
                    )
                    lines.append(f"- **Common Intents:** {intents_str}")

                if pattern.get("common_channels"):
                    channels_str = ", ".join(
                        [f"{ch} ({cnt})" for ch, cnt in pattern["common_channels"][:3]]
                    )
                    lines.append(f"- **Common Channels:** {channels_str}")

                lines.append("")

        # Recommendations
        if include_recommendations:
            lines.append("## Recommendations")
            lines.append("")
            recommendations = self._generate_overall_recommendations(analysis_result)
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. **{rec['priority'].upper()}**: {rec['action']}")
                lines.append(f"   - Impact: {rec['impact']}")
                lines.append(f"   - Effort: {rec['effort']}")
                lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*Report generated by FailureAnalyzer*")

        report = "\n".join(lines)

        # Write to file if specified
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)

        return report

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _extract_trace_scores(self, trace_id: str) -> dict[str, Any]:
        """
        Extract all scores associated with a trace.

        Args:
            trace_id: The trace identifier.

        Returns:
            Dictionary mapping score names to their values.
        """
        try:
            scores_response = langfuse.client.scores.list(trace_id=trace_id, limit=100)
            scores = {}
            for score in scores_response.data:
                scores[score.name] = score.value
            return scores
        except Exception:
            # Return empty dict if score retrieval fails
            return {}

    def _is_failure_case(self, scores: dict[str, Any], threshold: float) -> bool:
        """
        Determine if a set of scores indicates a failure case.

        A case is considered a failure if:
        - Any numeric score (0-1 range) is below the threshold
        - Issue resolved score is 0 (not resolved)
        - User satisfaction is below 2 (on 1-5 scale)

        Args:
            scores: Dictionary of score names to values.
            threshold: Threshold below which scores indicate failure.

        Returns:
            True if the case should be considered a failure.
        """
        # Check numeric scores in 0-1 range
        for name, value in scores.items():
            if isinstance(value, (int, float)):
                if 0 <= value <= 1 and value < threshold:
                    return True

        # Check issue resolution
        if scores.get(ISSUE_RESOLVED) == 0:
            return True

        # Check user satisfaction (1-5 scale, below 2 is poor)
        satisfaction = scores.get(USER_SATISFACTION)
        if satisfaction is not None and satisfaction < 2:
            return True

        return False

    def _aggregate_by_field(
        self, cases: list[FailureCase], field: str, default_value: str = "unknown"
    ) -> dict[str, dict[str, Any]]:
        """
        Aggregate cases by a specific attribute field.

        Args:
            cases: List of failure cases.
            field: Attribute name to aggregate by.
            default_value: Default value if field is missing.

        Returns:
            Dictionary with aggregated statistics per field value.
        """
        counter = Counter()
        score_sums = defaultdict(float)

        for case in cases:
            value = getattr(case, field, None) or default_value
            counter[value] += 1
            score_sums[value] += case.min_score

        total = len(cases)
        result = {}
        for value, count in counter.most_common():
            result[value] = {
                "count": count,
                "percentage": (count / total * 100) if total > 0 else 0,
                "avg_score": score_sums[value] / count if count > 0 else 0,
            }

        return result

    def _aggregate_by_metadata(
        self, cases: list[FailureCase], metadata_key: str
    ) -> dict[str, dict[str, Any]]:
        """
        Aggregate cases by a metadata field.

        Args:
            cases: List of failure cases.
            metadata_key: Key in metadata dictionary to aggregate by.

        Returns:
            Dictionary with aggregated statistics per metadata value.
        """
        counter = Counter()
        score_sums = defaultdict(float)

        for case in cases:
            value = case.metadata.get(metadata_key, "unknown")
            counter[value] += 1
            score_sums[value] += case.min_score

        total = len(cases)
        result = {}
        for value, count in counter.most_common():
            result[value] = {
                "count": count,
                "percentage": (count / total * 100) if total > 0 else 0,
                "avg_score": score_sums[value] / count if count > 0 else 0,
            }

        return result

    def _aggregate_by_time(self, cases: list[FailureCase]) -> dict[str, int]:
        """
        Aggregate cases by time buckets (hourly).

        Args:
            cases: List of failure cases.

        Returns:
            Dictionary mapping time buckets to occurrence counts.
        """
        counter = Counter()

        for case in cases:
            # Bucket by hour
            bucket = case.timestamp.strftime("%Y-%m-%d %H:00")
            counter[bucket] += 1

        return dict(counter.most_common())

    def _identify_top_patterns(self, cases: list[FailureCase], total: int) -> list[FailurePattern]:
        """
        Identify top recurring failure patterns.

        Groups cases by failure type and identifies common characteristics.

        Args:
            cases: List of failure cases.
            total: Total number of failures for percentage calculation.

        Returns:
            List of FailurePattern objects sorted by frequency.
        """
        # Group by failure type
        groups = defaultdict(list)
        for case in cases:
            ftype = case.failure_type or "unclassified"
            groups[ftype].append(case)

        patterns = []
        for ftype, group_cases in groups.items():
            # Analyze intents within this group
            intent_counter = Counter()
            channel_counter = Counter()
            time_counter = Counter()
            score_sum = 0

            for case in group_cases:
                intent = case.metadata.get("intent", "unknown")
                intent_counter[intent] += 1

                channel = case.metadata.get("channel", "unknown")
                channel_counter[channel] += 1

                time_bucket = case.timestamp.strftime("%Y-%m-%d %H:00")
                time_counter[time_bucket] += 1

                score_sum += case.min_score

            pattern = FailurePattern(
                pattern_name=f"Type: {ftype}",
                count=len(group_cases),
                total_failures=total,
                avg_score=score_sum / len(group_cases) if group_cases else 0,
                common_intents=intent_counter.most_common(5),
                common_channels=channel_counter.most_common(5),
                time_distribution=dict(time_counter.most_common(10)),
                sample_cases=group_cases[:3],
            )
            patterns.append(pattern)

        # Sort by count descending
        patterns.sort(key=lambda p: p.count, reverse=True)
        return patterns

    def _calculate_severity_distribution(
        self, cases: list[FailureCase]
    ) -> dict[str, dict[str, int]]:
        """
        Calculate severity distribution based on minimum scores.

        Severity levels:
        - Critical: score < 0.1
        - High: 0.1 <= score < 0.3
        - Medium: 0.3 <= score < 0.5
        - Low: score >= 0.5

        Args:
            cases: List of failure cases.

        Returns:
            Dictionary mapping severity levels to count and percentage.
        """
        severity_counts = Counter()

        for case in cases:
            score = case.min_score
            if score < 0.1:
                severity_counts["Critical"] += 1
            elif score < 0.3:
                severity_counts["High"] += 1
            elif score < 0.5:
                severity_counts["Medium"] += 1
            else:
                severity_counts["Low"] += 1

        total = len(cases)
        result = {}
        for level, count in severity_counts.most_common():
            result[level] = {
                "count": count,
                "percentage": (count / total * 100) if total > 0 else 0,
            }

        return result

    def _analyze_score_breakdown(self, case: FailureCase) -> dict[str, Any]:
        """
        Analyze the score breakdown for a failure case.

        Args:
            case: The failure case to analyze.

        Returns:
            Dictionary with detailed score analysis.
        """
        breakdown = {"all_scores": case.scores, "lowest_scores": [], "missing_critical_scores": []}

        # Find lowest scores
        numeric_scores = [
            (name, value)
            for name, value in case.scores.items()
            if isinstance(value, (int, float)) and 0 <= value <= 1
        ]
        numeric_scores.sort(key=lambda x: x[1])
        breakdown["lowest_scores"] = [
            {"name": name, "value": value} for name, value in numeric_scores[:5]
        ]

        # Check for missing critical scores
        critical_scores = [ISSUE_RESOLVED, USER_SATISFACTION, FAILURE_TYPE]
        for score_name in critical_scores:
            if score_name not in case.scores:
                breakdown["missing_critical_scores"].append(score_name)

        return breakdown

    def _identify_probable_causes(
        self, case: FailureCase, score_breakdown: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Identify probable causes based on score analysis.

        Args:
            case: The failure case.
            score_breakdown: Score breakdown from _analyze_score_breakdown.

        Returns:
            List of probable causes with confidence levels.
        """
        causes = []
        scores = case.scores

        # Check for intent recognition issues
        intent_confidence = scores.get("intent_confidence")
        if intent_confidence is not None and intent_confidence < 0.5:
            causes.append(
                {
                    "cause": "Low intent recognition confidence",
                    "confidence": 0.9,
                    "evidence": f"Intent confidence score: {intent_confidence:.2f}",
                    "category": "intent_recognition",
                }
            )

        # Check for RAG retrieval issues
        retrieval_relevance = scores.get("retrieval_relevance")
        if retrieval_relevance is not None and retrieval_relevance < 0.5:
            causes.append(
                {
                    "cause": "Poor knowledge retrieval relevance",
                    "confidence": 0.85,
                    "evidence": f"Retrieval relevance score: {retrieval_relevance:.2f}",
                    "category": "rag_retrieval",
                }
            )

        # Check for tool execution issues
        tool_success = scores.get("tool_success_rate")
        if tool_success is not None and tool_success < 0.8:
            causes.append(
                {
                    "cause": "Tool execution failures",
                    "confidence": 0.8,
                    "evidence": f"Tool success rate: {tool_success:.2f}",
                    "category": "tool_execution",
                }
            )

        # Check for unresolved issues
        if not case.is_resolved:
            causes.append(
                {
                    "cause": "Issue not resolved",
                    "confidence": 0.95,
                    "evidence": "Issue resolution score indicates failure",
                    "category": "resolution",
                }
            )

        # Check for low user satisfaction
        satisfaction = scores.get(USER_SATISFACTION)
        if satisfaction is not None and satisfaction < 3:
            causes.append(
                {
                    "cause": "Low user satisfaction",
                    "confidence": 0.75,
                    "evidence": f"User satisfaction rating: {satisfaction}/5",
                    "category": "user_experience",
                }
            )

        # Check for high latency
        latency = scores.get("response_latency_ms")
        if latency is not None and latency > 5000:
            causes.append(
                {
                    "cause": "High response latency",
                    "confidence": 0.6,
                    "evidence": f"Response time: {latency:.0f}ms",
                    "category": "performance",
                }
            )

        # Sort by confidence
        causes.sort(key=lambda x: x["confidence"], reverse=True)
        return causes

    def _identify_contributing_factors(self, case: FailureCase) -> list[dict[str, Any]]:
        """
        Identify contributing factors to the failure.

        Args:
            case: The failure case.

        Returns:
            List of contributing factors.
        """
        factors = []

        # Check metadata for context
        metadata = case.metadata

        if metadata.get("retry_count", 0) > 2:
            factors.append(
                {
                    "factor": "Multiple retry attempts",
                    "value": metadata["retry_count"],
                    "impact": "high",
                }
            )

        if metadata.get("escalation_triggered"):
            factors.append(
                {"factor": "Escalation was triggered", "value": True, "impact": "medium"}
            )

        dialogue_coherence = case.scores.get("dialogue_coherence")
        if dialogue_coherence is not None and dialogue_coherence < 0.6:
            factors.append(
                {"factor": "Low dialogue coherence", "value": dialogue_coherence, "impact": "high"}
            )

        slot_completion = case.scores.get("slot_completion_rate")
        if slot_completion is not None and slot_completion < 0.7:
            factors.append(
                {"factor": "Incomplete slot filling", "value": slot_completion, "impact": "medium"}
            )

        return factors

    def _generate_recommendations(
        self, probable_causes: list[dict[str, Any]], contributing_factors: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """
        Generate actionable recommendations based on analysis.

        Args:
            probable_causes: List of probable causes.
            contributing_factors: List of contributing factors.

        Returns:
            List of recommendation dictionaries.
        """
        recommendations = []
        seen_categories = set()

        for cause in probable_causes:
            category = cause.get("category", "")
            if category in seen_categories:
                continue
            seen_categories.add(category)

            if category == "intent_recognition":
                recommendations.append(
                    {
                        "action": "Improve intent classifier training data with more diverse examples",
                        "priority": "high",
                        "impact": "Reduce misclassification rate and improve routing accuracy",
                        "effort": "medium",
                    }
                )
            elif category == "rag_retrieval":
                recommendations.append(
                    {
                        "action": "Enhance knowledge base indexing and implement hybrid search strategies",
                        "priority": "high",
                        "impact": "Improve answer relevance and reduce hallucination",
                        "effort": "medium",
                    }
                )
            elif category == "tool_execution":
                recommendations.append(
                    {
                        "action": "Add retry logic and fallback mechanisms for tool calls",
                        "priority": "high",
                        "impact": "Increase successful task completion rate",
                        "effort": "low",
                    }
                )
            elif category == "resolution":
                recommendations.append(
                    {
                        "action": "Implement escalation triggers for complex or ambiguous queries",
                        "priority": "critical",
                        "impact": "Ensure customer issues are ultimately resolved",
                        "effort": "medium",
                    }
                )
            elif category == "user_experience":
                recommendations.append(
                    {
                        "action": "Review response templates and add empathy-driven language patterns",
                        "priority": "medium",
                        "impact": "Improve perceived quality even when technical issues occur",
                        "effort": "low",
                    }
                )
            elif category == "performance":
                recommendations.append(
                    {
                        "action": "Optimize LLM prompts and implement caching for common queries",
                        "priority": "medium",
                        "impact": "Reduce response times and improve user experience",
                        "effort": "medium",
                    }
                )

        return recommendations

    def _find_related_cases(
        self, case: FailureCase, similarity_threshold: float = 0.6
    ) -> list[dict[str, Any]]:
        """
        Find similar failure cases for pattern matching.

        Args:
            case: The reference failure case.
            similarity_threshold: Minimum similarity score to include.

        Returns:
            List of related cases with similarity scores.
        """
        # In a production system, this would use vector similarity or ML models
        # For now, we use simple heuristic matching
        related = []

        # Try to fetch more traces with similar characteristics
        try:
            similar_traces = langfuse.fetch_traces(
                page=1,
                limit=20,
                tags=case.tags[:1] if case.tags else None,
                session_id=case.session_id,
            )

            for trace in similar_traces.data:
                if trace.id == case.trace_id:
                    continue

                # Calculate simple similarity based on shared tags
                trace_tags = set(trace.tags or [])
                case_tags = set(case.tags or [])

                if case_tags:
                    similarity = len(trace_tags & case_tags) / len(case_tags | trace_tags)
                else:
                    similarity = 0.5  # Default similarity for untagged cases

                if similarity >= similarity_threshold:
                    related.append(
                        {
                            "trace_id": trace.id,
                            "similarity": similarity,
                            "session_id": trace.sessionId,
                        }
                    )

        except Exception:
            pass

        # Sort by similarity
        related.sort(key=lambda x: x["similarity"], reverse=True)
        return related

    def _generate_overall_recommendations(
        self, analysis_result: dict[str, Any]
    ) -> list[dict[str, str]]:
        """
        Generate overall recommendations based on complete analysis.

        Args:
            analysis_result: Complete analysis result.

        Returns:
            List of prioritized recommendations.
        """
        recommendations = []
        summary = analysis_result.get("summary", {})
        by_failure_type = analysis_result.get("by_failure_type", {})

        # Check resolution rate
        resolution_rate = summary.get("resolution_rate", 1)
        if resolution_rate < 0.7:
            recommendations.append(
                {
                    "action": "Implement automatic escalation for unresolved issues after 2 turns",
                    "priority": "critical",
                    "impact": f"Current resolution rate is {resolution_rate:.1%}, target >80%",
                    "effort": "medium",
                }
            )

        # Check dominant failure types
        if by_failure_type:
            top_failure = max(by_failure_type.items(), key=lambda x: x[1]["count"])
            ftype, fdata = top_failure
            if fdata["percentage"] > 40:
                recommendations.append(
                    {
                        "action": f"Prioritize fixing {ftype} issues (represents {fdata['percentage']:.0f}% of failures)",
                        "priority": "high",
                        "impact": "Address the most common failure mode",
                        "effort": "varies",
                    }
                )

        # Check severity
        severity_dist = analysis_result.get("severity_distribution", {})
        critical_count = severity_dist.get("Critical", {}).get("count", 0)
        if critical_count > 0:
            recommendations.append(
                {
                    "action": f"Investigate {critical_count} critical failures immediately",
                    "priority": "critical",
                    "impact": "Prevent severe customer dissatisfaction",
                    "effort": "high",
                }
            )

        # General best practices
        recommendations.append(
            {
                "action": "Set up automated alerts for failure rate spikes",
                "priority": "medium",
                "impact": "Enable proactive issue detection",
                "effort": "low",
            }
        )

        recommendations.append(
            {
                "action": "Schedule weekly failure review meetings with engineering team",
                "priority": "medium",
                "impact": "Continuous improvement through regular analysis",
                "effort": "low",
            }
        )

        return recommendations

    def _empty_analysis_result(self) -> dict[str, Any]:
        """
        Return an empty analysis result structure.

        Returns:
            Empty analysis result dictionary.
        """
        return {
            "summary": {
                "total_failures": 0,
                "avg_min_score": 0,
                "resolution_rate": 0,
                "unique_users": 0,
                "unique_sessions": 0,
                "time_range": {},
            },
            "by_failure_type": {},
            "by_intent": {},
            "by_channel": {},
            "by_time": {},
            "top_patterns": [],
            "severity_distribution": {},
        }


# Export main classes
__all__ = [
    "FailureAnalyzer",
    "FailureCase",
    "FailurePattern",
    "DEFAULT_SCORE_THRESHOLD",
    "DEFAULT_CASE_LIMIT",
    "DEFAULT_TIME_RANGE_DAYS",
]
