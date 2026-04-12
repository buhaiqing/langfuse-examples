"""
Metrics collector for ML-based anomaly detection.

Collects and aggregates monitoring metrics from Langfuse API,
including success rate, latency, request rate, and user satisfaction.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from src.observability.instrumentation import get_langfuse_client


@dataclass
class MetricPoint:
    """Represents a single metric data point."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and aggregates monitoring metrics from Langfuse.
    
    Provides methods to calculate key performance indicators (KPIs)
    over sliding time windows for ML-based anomaly detection.
    """

    def __init__(self, window_minutes: int = 10):
        """
        Initialize the metrics collector.
        
        Args:
            window_minutes: Time window for metric calculation (in minutes).
        """
        self.window_minutes = window_minutes
        self._langfuse = get_langfuse_client()
        self._metrics_cache: Dict[str, List[MetricPoint]] = {}

    def collect_success_rate(self, session_id: Optional[str] = None) -> float:
        """
        Calculate success rate within the time window.
        
        Args:
            session_id: Optional session filter.
            
        Returns:
            Success rate as a float between 0.0 and 1.0.
        """
        traces = self._fetch_traces(session_id=session_id)
        
        if not traces:
            return 1.0  # Default to 100% if no data
        
        # Count successful traces (those without errors)
        total_count = len(traces)
        error_count = sum(
            1 for trace in traces 
            if hasattr(trace, 'status') and trace.status == 'ERROR'
        )
        
        success_rate = (total_count - error_count) / total_count
        return success_rate

    def collect_latency_p95(self, session_id: Optional[str] = None) -> float:
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
        
        # Extract durations (in milliseconds)
        durations = []
        for trace in traces:
            if hasattr(trace, 'duration') and trace.duration is not None:
                durations.append(trace.duration)
        
        if not durations:
            return 0.0
        
        # Calculate P95
        p95_latency = np.percentile(durations, 95)
        return float(p95_latency)

    def collect_request_rate(self) -> float:
        """
        Calculate request rate (QPS) within the time window.
        
        Returns:
            Requests per second.
        """
        traces = self._fetch_traces()
        
        if not traces:
            return 0.0
        
        # Calculate QPS: number of requests / window duration in seconds
        window_seconds = self.window_minutes * 60
        qps = len(traces) / window_seconds
        
        return qps

    def collect_avg_satisfaction(self) -> Optional[float]:
        """
        Calculate average user satisfaction score within the time window.
        
        Returns:
            Average satisfaction score, or None if no scores available.
        """
        # Fetch scores from Langfuse
        try:
            scores = self._langfuse.client.score.list(
                limit=1000,
                from_timestamp=(
                    datetime.now(timezone.utc) - 
                    timedelta(minutes=self.window_minutes)
                ).isoformat()
            )
            
            if not scores.data:
                return None
            
            # Filter for satisfaction-related scores
            satisfaction_scores = [
                score.value for score in scores.data
                if hasattr(score, 'name') and 
                'satisfaction' in score.name.lower()
            ]
            
            if not satisfaction_scores:
                return None
            
            avg_satisfaction = np.mean(satisfaction_scores)
            return float(avg_satisfaction)
            
        except Exception as e:
            print(f"Failed to collect satisfaction scores: {e}")
            return None

    def get_historical_data(
        self,
        metric_name: str,
        hours: int = 24,
        interval_minutes: Optional[int] = None
    ) -> pd.DataFrame:
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
        if interval_minutes is None:
            interval_minutes = self.window_minutes
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        # Generate time intervals
        intervals = pd.date_range(
            start=start_time,
            end=end_time,
            freq=f'{interval_minutes}min'
        )
        
        # Collect metric values for each interval
        values = []
        timestamps = []
        
        for i in range(len(intervals) - 1):
            window_start = intervals[i]
            window_end = intervals[i + 1]
            
            # Calculate metric for this window
            value = self._calculate_metric_for_window(
                metric_name, window_start, window_end
            )
            
            if value is not None:
                values.append(value)
                timestamps.append(window_end)
        
        # Create DataFrame
        df = pd.DataFrame({
            'ds': timestamps,
            'y': values
        })
        
        return df

    def _fetch_traces(
        self,
        session_id: Optional[str] = None
    ) -> List[Any]:
        """
        Fetch traces from Langfuse within the time window.
        
        Args:
            session_id: Optional session filter.
            
        Returns:
            List of trace objects.
        """
        try:
            params = {
                'limit': 1000,
                'from_timestamp': (
                    datetime.now(timezone.utc) - 
                    timedelta(minutes=self.window_minutes)
                ).isoformat()
            }
            
            if session_id:
                params['session_id'] = session_id
            
            response = self._langfuse.client.trace.list(**params)
            return response.data if hasattr(response, 'data') else []
            
        except Exception as e:
            print(f"Failed to fetch traces: {e}")
            return []

    def _calculate_metric_for_window(
        self,
        metric_name: str,
        window_start: datetime,
        window_end: datetime
    ) -> Optional[float]:
        """
        Calculate a specific metric for a given time window.
        
        Args:
            metric_name: Name of the metric.
            window_start: Start of the time window.
            window_end: End of the time window.
            
        Returns:
            Metric value, or None if unavailable.
        """
        try:
            params = {
                'limit': 1000,
                'from_timestamp': window_start.isoformat(),
                'to_timestamp': window_end.isoformat()
            }
            
            response = self._langfuse.client.trace.list(**params)
            traces = response.data if hasattr(response, 'data') else []
            
            if not traces:
                return None
            
            if metric_name == 'success_rate':
                total = len(traces)
                errors = sum(
                    1 for t in traces
                    if hasattr(t, 'status') and t.status == 'ERROR'
                )
                return (total - errors) / total
            
            elif metric_name == 'latency_p95':
                durations = [
                    t.duration for t in traces
                    if hasattr(t, 'duration') and t.duration is not None
                ]
                if not durations:
                    return None
                return float(np.percentile(durations, 95))
            
            elif metric_name == 'request_rate':
                window_seconds = (window_end - window_start).total_seconds()
                if window_seconds == 0:
                    return None
                return len(traces) / window_seconds
            
            elif metric_name == 'satisfaction':
                # This would require fetching scores for the specific window
                # Simplified implementation
                return None
            
            return None
            
        except Exception as e:
            print(f"Failed to calculate metric {metric_name}: {e}")
            return None
