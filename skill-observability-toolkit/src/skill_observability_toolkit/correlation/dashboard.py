"""
Dashboard Integration.

This module provides dashboard data models, metrics aggregation,
and visualization helpers for unified observability dashboards.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MetricType(Enum):
    """Type of metric."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class TimeGranularity(Enum):
    """Time granularity for metrics."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


@dataclass
class TimeSeriesPoint:
    """A point in a time series."""
    timestamp: float
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """A metric definition."""
    name: str
    metric_type: MetricType
    description: str = ""
    unit: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    data_points: list[TimeSeriesPoint] = field(default_factory=list)

    def add_point(self, value: float, labels: dict[str, str] | None = None):
        """Add a data point to the metric."""
        self.data_points.append(TimeSeriesPoint(
            timestamp=time.time(),
            value=value,
            labels=labels or {},
        ))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "description": self.description,
            "unit": self.unit,
            "labels": self.labels,
            "data_points": [
                {
                    "timestamp": dp.timestamp,
                    "value": dp.value,
                    "labels": dp.labels,
                }
                for dp in self.data_points
            ],
        }


@dataclass
class DashboardPanel:
    """A dashboard panel (visualization)."""
    id: str
    title: str
    panel_type: str  # e.g., "timeseries", "gauge", "counter"
    metric_name: str
    description: str = ""
    options: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.panel_type,
            "metric": self.metric_name,
            "description": self.description,
            "options": self.options,
        }


@dataclass
class Dashboard:
    """A dashboard definition."""
    id: str
    title: str
    description: str = ""
    panels: list[DashboardPanel] = field(default_factory=list)
    refresh_interval: int = 60  # seconds
    time_range: str = "1h"  # e.g., "1h", "24h", "7d"

    def add_panel(self, panel: DashboardPanel):
        """Add a panel to the dashboard."""
        self.panels.append(panel)

    def remove_panel(self, panel_id: str):
        """Remove a panel from the dashboard."""
        self.panels = [
            p for p in self.panels if p.id != panel_id
        ]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "panels": [p.to_dict() for p in self.panels],
            "refresh_interval": self.refresh_interval,
            "time_range": self.time_range,
        }


class MetricsAggregator:
    """
    Aggregate metrics data.

    Provides functionality to:
    - Aggregate time series data
    - Calculate statistics
    - Generate aggregations
    - Support Grafana-style queries
    """

    def __init__(self):
        """Initialize the aggregator."""
        self._metrics: dict[str, Metric] = {}

    def add_metric(self, metric: Metric) -> "MetricsAggregator":
        """
        Add a metric.

        Args:
            metric: Metric to add

        Returns:
            Self for method chaining
        """
        self._metrics[metric.name] = metric
        return self

    def get_metric(self, name: str) -> Metric | None:
        """
        Get a metric by name.

        Args:
            name: Metric name

        Returns:
            Metric or None
        """
        return self._metrics.get(name)

    def list_metrics(self) -> list[str]:
        """List all metric names."""
        return list(self._metrics.keys())

    def aggregate(
        self,
        metric_name: str,
        aggregation: str = "mean",
        window: int | None = None,
    ) -> float | None:
        """
        Aggregate metric data.

        Args:
            metric_name: Name of the metric
            aggregation: Aggregation function ("mean", "sum", "max", "min")
            window: Time window in seconds (optional)

        Returns:
            Aggregated value or None
        """
        metric = self._metrics.get(metric_name)
        if not metric:
            return None

        if not metric.data_points:
            return None

        values = [dp.value for dp in metric.data_points]

        if not values:
            return None

        if aggregation == "mean":
            return sum(values) / len(values)
        elif aggregation == "sum":
            return sum(values)
        elif aggregation == "max":
            return max(values)
        elif aggregation == "min":
            return min(values)
        else:
            return None

    def range_query(
        self,
        metric_name: str,
        start_time: float,
        end_time: float,
        granularity: TimeGranularity = TimeGranularity.MINUTE,
    ) -> list[TimeSeriesPoint]:
        """
        Query metric data within a time range.

        Args:
            metric_name: Name of the metric
            start_time: Start timestamp
            end_time: End timestamp
            granularity: Time granularity

        Returns:
            List of time series points
        """
        metric = self._metrics.get(metric_name)
        if not metric:
            return []

        # Filter by time range
        filtered = [
            dp for dp in metric.data_points
            if start_time <= dp.timestamp <= end_time
        ]

        # Granularity-based aggregation
        granularity_seconds = {
            TimeGranularity.SECOND: 1,
            TimeGranularity.MINUTE: 60,
            TimeGranularity.HOUR: 3600,
            TimeGranularity.DAY: 86400,
            TimeGranularity.WEEK: 604800,
        }
        
        bucket_size = granularity_seconds.get(granularity, 60)
        
        # Group data points into buckets
        buckets: dict[int, list] = {}
        for dp in filtered:
            bucket_key = int(dp.timestamp // bucket_size)
            if bucket_key not in buckets:
                buckets[bucket_key] = []
            buckets[bucket_key].append(dp)
        
        # Aggregate each bucket
        aggregated = []
        for bucket_key, points in sorted(buckets.items()):
            avg_value = sum(p.value for p in points) / len(points)
            bucket_timestamp = bucket_key * bucket_size
            
            aggregated.append(TimeSeriesPoint(
                timestamp=bucket_timestamp,
                value=avg_value,
                labels={"bucket_size": str(bucket_size), "points_count": str(len(points))},
            ))
        
        return aggregated

    def generate_dashboard_data(
        self,
        dashboard: Dashboard,
    ) -> dict[str, Any]:
        """
        Generate data for a dashboard.

        Args:
            dashboard: Dashboard definition

        Returns:
            Dashboard data dictionary
        """
        data = {
            "dashboard": dashboard.to_dict(),
            "metrics": {},
        }

        for panel in dashboard.panels:
            metric_data = {
                "metric": self._metrics.get(panel.metric_name, {}).to_dict() if self._metrics.get(panel.metric_name) else {},
                "aggregations": {
                    "mean": self.aggregate(panel.metric_name, "mean"),
                    "sum": self.aggregate(panel.metric_name, "sum"),
                    "max": self.aggregate(panel.metric_name, "max"),
                    "min": self.aggregate(panel.metric_name, "min"),
                },
            }
            data["metrics"][panel.metric_name] = metric_data

        return data


class DashboardBuilder:
    """
    Builder for creating dashboards.

    Provides fluent API for dashboard creation.
    """

    def __init__(self):
        """Initialize the builder."""
        self._dashboard: Dashboard | None = None

    def create_dashboard(
        self,
        dashboard_id: str,
        title: str,
        description: str = "",
    ) -> "DashboardBuilder":
        """
        Create a new dashboard.

        Args:
            dashboard_id: Dashboard ID
            title: Dashboard title
            description: Dashboard description

        Returns:
            Self for method chaining
        """
        self._dashboard = Dashboard(
            id=dashboard_id,
            title=title,
            description=description,
        )
        return self

    def add_time_series_panel(
        self,
        panel_id: str,
        title: str,
        metric_name: str,
        description: str = "",
        y_axis_label: str = "",
    ) -> "DashboardBuilder":
        """
        Add a time series panel.

        Args:
            panel_id: Panel ID
            title: Panel title
            metric_name: Metric name to visualize
            description: Panel description
            y_axis_label: Y-axis label

        Returns:
            Self for method chaining
        """
        if not self._dashboard:
            raise ValueError("Dashboard not created. Call create_dashboard() first.")

        panel = DashboardPanel(
            id=panel_id,
            title=title,
            panel_type="timeseries",
            metric_name=metric_name,
            description=description,
            options={
                "y_axis_label": y_axis_label,
                "line_color": "blue",
                "show_points": True,
            },
        )

        self._dashboard.add_panel(panel)
        return self

    def add_gauge_panel(
        self,
        panel_id: str,
        title: str,
        metric_name: str,
        description: str = "",
        min_value: float = 0,
        max_value: float = 100,
    ) -> "DashboardBuilder":
        """
        Add a gauge panel.

        Args:
            panel_id: Panel ID
            title: Panel title
            metric_name: Metric name to visualize
            description: Panel description
            min_value: Minimum value
            max_value: Maximum value

        Returns:
            Self for method chaining
        """
        if not self._dashboard:
            raise ValueError("Dashboard not created. Call create_dashboard() first.")

        panel = DashboardPanel(
            id=panel_id,
            title=title,
            panel_type="gauge",
            metric_name=metric_name,
            description=description,
            options={
                "min_value": min_value,
                "max_value": max_value,
                "show_value": True,
            },
        )

        self._dashboard.add_panel(panel)
        return self

    def add_counter_panel(
        self,
        panel_id: str,
        title: str,
        metric_name: str,
        description: str = "",
        format: str = "short",
    ) -> "DashboardBuilder":
        """
        Add a counter panel.

        Args:
            panel_id: Panel ID
            title: Panel title
            metric_name: Metric name to visualize
            description: Panel description
            format: Value format ("short", "long", "percent")

        Returns:
            Self for method chaining
        """
        if not self._dashboard:
            raise ValueError("Dashboard not created. Call create_dashboard() first.")

        panel = DashboardPanel(
            id=panel_id,
            title=title,
            panel_type="counter",
            metric_name=metric_name,
            description=description,
            options={
                "format": format,
                "show_change": True,
            },
        )

        self._dashboard.add_panel(panel)
        return self

    def set_refresh_interval(self, interval_seconds: int) -> "DashboardBuilder":
        """
        Set dashboard refresh interval.

        Args:
            interval_seconds: Refresh interval in seconds

        Returns:
            Self for method chaining
        """
        if not self._dashboard:
            raise ValueError("Dashboard not created. Call create_dashboard() first.")

        self._dashboard.refresh_interval = interval_seconds
        return self

    def set_time_range(self, time_range: str) -> "DashboardBuilder":
        """
        Set default time range.

        Args:
            time_range: Time range string (e.g., "1h", "24h", "7d")

        Returns:
            Self for method chaining
        """
        if not self._dashboard:
            raise ValueError("Dashboard not created. Call create_dashboard() first.")

        self._dashboard.time_range = time_range
        return self

    def build(self) -> Dashboard:
        """Build and return the dashboard."""
        if not self._dashboard:
            raise ValueError("Dashboard not created. Call create_dashboard() first.")

        dashboard = self._dashboard
        self._dashboard = None
        return dashboard


# Global aggregator instance
_aggregator = MetricsAggregator()


def get_aggregator() -> MetricsAggregator:
    """Get global aggregator instance."""
    return _aggregator


# Convenience functions
def add_metric(metric: Metric) -> MetricsAggregator:
    """Add a metric (convenience function)."""
    return _aggregator.add_metric(metric)


def aggregate(
    metric_name: str,
    aggregation: str = "mean",
) -> float | None:
    """Aggregate metric (convenience function)."""
    return _aggregator.aggregate(metric_name, aggregation)


def generate_dashboard_data(dashboard: Dashboard) -> dict[str, Any]:
    """Generate dashboard data (convenience function)."""
    return _aggregator.generate_dashboard_data(dashboard)
