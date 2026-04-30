"""
Metrics collector for ML-based anomaly detection.

Collects and aggregates monitoring metrics from Langfuse API,
including success rate, latency, request rate, and user satisfaction.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from langfuse import Langfuse

from src.observability.cache import TTLCache
from src.observability.instrumentation import get_langfuse_client

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Represents a single metric data point."""

    timestamp: datetime
    value: float
    metadata: dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and aggregates monitoring metrics from Langfuse.

    Provides methods to calculate key performance indicators (KPIs)
    over sliding time windows for ML-based anomaly detection.

    Uses the shared Langfuse client from get_langfuse_client().
    """

    def __init__(self, window_minutes: int = 10, cache_ttl: int = 300):
        """
        Initialize the metrics collector.

        Args:
            window_minutes: Time window for metric calculation (in minutes).
            cache_ttl: Cache lifetime in seconds (default: 5 minutes).
        """
        self.window_minutes = window_minutes
        self._metrics_cache: dict[str, list[MetricPoint]] = {}
        self._trace_cache = TTLCache(ttl=cache_ttl, max_size=64)

    def _get_client(self) -> Optional["Langfuse"]:
        """Get the Langfuse client, returning None if unavailable."""
        return get_langfuse_client()

    def collect_success_rate(self, session_id: str | None = None) -> float:
        """
        Calculate success rate within the time window.

        Args:
            session_id: Optional session filter.

        Returns:
            Success rate as a float between 0.0 and 1.0.
        """
        traces = self._fetch_traces(session_id=session_id)

        if not traces:
            return 1.0

        total_count = len(traces)
        error_count = sum(
            1 for trace in traces if hasattr(trace, "status") and trace.status == "ERROR"
        )

        success_rate = (total_count - error_count) / total_count
        return success_rate

    def collect_latency_p95(self, session_id: str | None = None) -> float:
        """
        Calculate P95 latency within the time window.

        Args:
            session_id: Optional session filter.

        Returns:
            P95 latency in milliseconds.
        """
        traces = self._fetch_traces(session_id=session_id)

        if not traces:
            return 0.0

        durations = []
        for trace in traces:
            if hasattr(trace, "duration") and trace.duration is not None:
                durations.append(trace.duration)

        if not durations:
            return 0.0

        import numpy as np

        p95_latency = np.percentile(durations, 95)
        return float(p95_latency)

    def collect_latency_p99(self, session_id: str | None = None) -> float:
        """
        Calculate P99 latency within the time window (tail latency).

        Args:
            session_id: Optional session filter.

        Returns:
            P99 latency in milliseconds.
        """
        traces = self._fetch_traces(session_id=session_id)

        if not traces:
            return 0.0

        durations = []
        for trace in traces:
            if hasattr(trace, "duration") and trace.duration is not None:
                durations.append(trace.duration)

        if not durations:
            return 0.0

        import numpy as np

        p99_latency = np.percentile(durations, 99)
        return float(p99_latency)

    def collect_latency_p50(self, session_id: str | None = None) -> float:
        """
        Calculate P50 latency (median) within the time window.

        Args:
            session_id: Optional session filter.

        Returns:
            P50 (median) latency in milliseconds.
        """
        traces = self._fetch_traces(session_id=session_id)

        if not traces:
            return 0.0

        durations = []
        for trace in traces:
            if hasattr(trace, "duration") and trace.duration is not None:
                durations.append(trace.duration)

        if not durations:
            return 0.0

        import numpy as np

        p50_latency = np.percentile(durations, 50)
        return float(p50_latency)

    def collect_request_rate(self) -> float:
        """
        Calculate request rate (QPS) within the time window.

        Returns:
            Requests per second.
        """
        traces = self._fetch_traces()

        if not traces:
            return 0.0

        window_seconds = self.window_minutes * 60
        qps = len(traces) / window_seconds

        return qps

    def collect_avg_satisfaction(self) -> float | None:
        """
        Calculate average user satisfaction score within the time window.

        Uses the FeedbackCollector's local data as the primary source,
        since the Langfuse SDK does not provide a direct score listing API.

        Returns:
            Average satisfaction score, or None if no scores available.
        """
        try:
            from src.observability.feedback import get_feedback_collector

            collector = get_feedback_collector()
            avg_rating = collector.get_average_rating()
            return avg_rating
        except Exception as e:
            logger.warning("Failed to collect satisfaction scores: %s", e)
            return None

    def count_active_sessions(self) -> int:
        """
        Count unique active sessions within the time window.

        Returns:
            Number of unique session IDs.
        """
        traces = self._fetch_traces()

        if not traces:
            return 0

        session_ids = set()
        for trace in traces:
            if hasattr(trace, "session_id") and trace.session_id:
                session_ids.add(trace.session_id)

        return len(session_ids)

    def collect_error_breakdown(self) -> dict[str, int]:
        """
        Get error breakdown by error type/category.

        Analyzes trace metadata and status to categorize errors.

        Returns:
            Dictionary mapping error categories to their counts.
        """
        traces = self._fetch_traces()

        if not traces:
            return {}

        error_breakdown: dict[str, int] = {}

        for trace in traces:
            if hasattr(trace, "status") and trace.status == "ERROR":
                # Try to get error category from metadata
                error_category = "unknown"

                if hasattr(trace, "metadata") and trace.metadata:
                    error_category = trace.metadata.get("error_type", "unknown")

                # Check for specific error patterns in trace name
                if hasattr(trace, "name") and trace.name:
                    trace_name = trace.name.lower()
                    if "timeout" in trace_name:
                        error_category = "timeout"
                    elif "rate_limit" in trace_name or "rate-limit" in trace_name:
                        error_category = "rate_limit"
                    elif "validation" in trace_name:
                        error_category = "validation_error"

                error_breakdown[error_category] = error_breakdown.get(error_category, 0) + 1

        return error_breakdown

    def collect_tool_metrics(self, tool_name: str) -> dict[str, Any]:
        """
        Collect metrics for a specific tool.

        Args:
            tool_name: Name of the tool to collect metrics for.

        Returns:
            Dictionary containing tool-specific metrics.
        """
        traces = self._fetch_traces()

        if not traces:
            return {
                "tool_name": tool_name,
                "call_count": 0,
                "success_rate": 1.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "error_count": 0,
            }

        # Filter traces for this tool
        tool_traces = [t for t in traces if hasattr(t, "name") and t.name and tool_name in t.name]

        if not tool_traces:
            return {
                "tool_name": tool_name,
                "call_count": 0,
                "success_rate": 1.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "error_count": 0,
            }

        import numpy as np

        # Calculate metrics
        total_count = len(tool_traces)
        error_count = sum(1 for t in tool_traces if hasattr(t, "status") and t.status == "ERROR")
        success_rate = (total_count - error_count) / total_count

        # Calculate latencies
        durations = [
            t.duration for t in tool_traces if hasattr(t, "duration") and t.duration is not None
        ]

        p50_latency = float(np.percentile(durations, 50)) if durations else 0.0
        p95_latency = float(np.percentile(durations, 95)) if durations else 0.0
        p99_latency = float(np.percentile(durations, 99)) if durations else 0.0

        return {
            "tool_name": tool_name,
            "call_count": total_count,
            "success_rate": success_rate,
            "p50_latency_ms": p50_latency,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": p99_latency,
            "error_count": error_count,
        }

    def get_historical_data(
        self,
        metric_name: str,
        hours: int = 24,
        interval_minutes: int | None = None,
    ) -> Any:  # pd.DataFrame
        """
        Get historical data for model training.

        Args:
            metric_name: Name of the metric ('success_rate', 'latency_p95',
                        'request_rate', 'satisfaction').
            hours: Number of hours of historical data to fetch.
            interval_minutes: Aggregation interval (defaults to window_minutes).

        Returns:
            DataFrame with columns ['ds', 'y'] where:
                - ds: datetime
                - y: metric value
        """
        import pandas as pd

        if interval_minutes is None:
            interval_minutes = self.window_minutes

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        intervals = pd.date_range(start=start_time, end=end_time, freq=f"{interval_minutes}min")

        values = []
        timestamps = []

        for i in range(len(intervals) - 1):
            window_start = intervals[i]
            window_end = intervals[i + 1]

            value = self._calculate_metric_for_window(metric_name, window_start, window_end)

            if value is not None:
                values.append(value)
                timestamps.append(window_end)

        df = pd.DataFrame({"ds": timestamps, "y": values})

        return df

    def _fetch_traces(
        self,
        session_id: str | None = None,
    ) -> list[Any]:
        """
        Fetch traces from Langfuse within the time window.

        Uses lf.get_traces() which is the high-level SDK API.
        Implements TTL caching to reduce redundant API calls.

        Args:
            session_id: Optional session filter.

        Returns:
            List of trace objects.
        """
        # Generate cache key
        cache_key = f"traces:{session_id or 'all'}:{self.window_minutes}"

        # Check cache first
        cached_traces = self._trace_cache.get(cache_key)
        if cached_traces is not None:
            logger.debug("Trace cache hit for key: %s", cache_key)
            return cached_traces

        # Cache miss - fetch from API
        client = self._get_client()
        if not client:
            logger.debug("Langfuse client not available, returning empty traces")
            return []

        try:
            from_timestamp = datetime.now(timezone.utc) - timedelta(minutes=self.window_minutes)

            kwargs = {
                "limit": 1000,
                "from_timestamp": from_timestamp,
            }

            if session_id:
                kwargs["session_id"] = session_id

            response = client.get_traces(**kwargs)

            if hasattr(response, "data"):
                traces = response.data
                # Cache the result
                self._trace_cache.set(cache_key, traces)
                logger.debug("Cached %d traces for key: %s", len(traces), cache_key)
                return traces
            return []

        except Exception as e:
            logger.warning("Failed to fetch traces: %s", e)
            return []

    def _calculate_metric_for_window(
        self,
        metric_name: str,
        window_start: datetime,
        window_end: datetime,
    ) -> float | None:
        """
        Calculate a specific metric for a given time window.

        Args:
            metric_name: Name of the metric.
            window_start: Start of the time window.
            window_end: End of the time window.

        Returns:
            Metric value, or None if unavailable.
        """
        import numpy as np

        client = self._get_client()
        if not client:
            return None

        try:
            kwargs = {
                "limit": 1000,
                "from_timestamp": window_start,
            }

            response = client.get_traces(**kwargs)
            traces = response.data if hasattr(response, "data") else []

            if not traces:
                return None

            if metric_name == "success_rate":
                total = len(traces)
                errors = sum(1 for t in traces if hasattr(t, "status") and t.status == "ERROR")
                return (total - errors) / total

            elif metric_name == "latency_p95":
                durations = [
                    t.duration for t in traces if hasattr(t, "duration") and t.duration is not None
                ]
                if not durations:
                    return None
                return float(np.percentile(durations, 95))

            elif metric_name == "request_rate":
                window_seconds = (window_end - window_start).total_seconds()
                if window_seconds == 0:
                    return None
                return len(traces) / window_seconds

            elif metric_name == "satisfaction":
                return None

            return None

        except Exception as e:
            logger.warning("Failed to calculate metric %s: %s", metric_name, e)
            return None

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dictionary with cache hit rate, size, and configuration.
        """
        return {
            "hit_rate": self._trace_cache.hit_rate,
            "size": self._trace_cache.size,
            "max_size": self._trace_cache.max_size,
            "ttl_seconds": self._trace_cache.ttl,
        }

    def clear_cache(self) -> None:
        """Clear all cached traces."""
        self._trace_cache.clear()
        logger.info("Metrics collector cache cleared")

    def invalidate_cache(self, session_id: str | None = None) -> None:
        """
        Invalidate cache for specific session or all sessions.

        Args:
            session_id: Session ID to invalidate, or None for all.
        """
        if session_id:
            cache_key = f"traces:{session_id}:{self.window_minutes}"
            self._trace_cache.invalidate(cache_key)
            logger.info("Invalidated cache for session: %s", session_id)
        else:
            self.clear_cache()
