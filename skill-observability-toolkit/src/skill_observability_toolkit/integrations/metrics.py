"""
Performance Metrics Integration.

This module provides performance metrics collection and integration.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import statistics


class MetricType(Enum):
    """Metric type."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricData:
    """Metric data point."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """Metric definition."""
    name: str
    metric_type: MetricType
    description: str = ""
    unit: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    data_points: List[MetricData] = field(default_factory=list)
    
    def add_point(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Add a data point."""
        self.data_points.append(MetricData(
            timestamp=time.time(),
            value=value,
            labels=labels or {},
        ))
    
    def get_last_value(self) -> Optional[float]:
        """Get last value."""
        if self.data_points:
            return self.data_points[-1].value
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        if not self.data_points:
            return {}
        
        values = [dp.value for dp in self.data_points]
        
        stats = {
            "count": len(values),
            "sum": sum(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
        }
        
        if len(values) > 1:
            stats["std"] = statistics.stdev(values)
            stats["min"] = min(values)
            stats["max"] = max(values)
        
        return stats
    
    def filter_by_labels(self, labels: Dict[str, str]) -> List[MetricData]:
        """Filter data points by labels."""
        return [
            dp for dp in self.data_points
            if all(dp.labels.get(k) == v for k, v in labels.items())
        ]


class MetricsCollector:
    """
    Collect and manage metrics.
    
    Provides functionality to:
    - Collect performance metrics
    - Track timing
    - Calculate statistics
    - Export metrics
    """
    
    def __init__(self):
        """Initialize the metrics collector."""
        self._metrics: Dict[str, Metric] = {}
    
    def register_metric(
        self,
        name: str,
        metric_type: MetricType,
        description: str = "",
        unit: str = "",
    ) -> "MetricsCollector":
        """
        Register a metric.
        
        Args:
            name: Metric name
            metric_type: Type of metric
            description: Metric description
            unit: Metric unit
            
        Returns:
            Self for method chaining
        """
        self._metrics[name] = Metric(
            name=name,
            metric_type=metric_type,
            description=description,
            unit=unit,
        )
        return self
    
    def record(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Record a metric value.
        
        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels
            
        Returns:
            True if recorded
        """
        metric = self._metrics.get(name)
        
        if not metric:
            return False
        
        metric.add_point(value, labels)
        return True
    
    def timing(
        self,
        name: str,
        start_time: float,
        end_time: Optional[float] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Record a timing metric.
        
        Args:
            name: Metric name (should be a histogram)
            start_time: Start timestamp
            end_time: End timestamp (current if None)
            labels: Optional labels
            
        Returns:
            True if recorded
        """
        if end_time is None:
            end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        
        return self.record(name, duration_ms, labels)
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric."""
        return self._metrics.get(name)
    
    def get_metrics(self) -> Dict[str, Metric]:
        """Get all metrics."""
        return self._metrics.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics for all metrics."""
        return {
            name: metric.get_stats()
            for name, metric in self._metrics.items()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            name: {
                "name": metric.name,
                "type": metric.metric_type.value,
                "description": metric.description,
                "unit": metric.unit,
                "data_points": [
                    {
                        "timestamp": dp.timestamp,
                        "value": dp.value,
                        "labels": dp.labels,
                    }
                    for dp in metric.data_points
                ],
            }
            for name, metric in self._metrics.items()
        }
    
    def clear(self):
        """Clear all metrics."""
        self._metrics = {}


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def register_metric(
    name: str,
    metric_type: MetricType,
    description: str = "",
    unit: str = "",
) -> MetricsCollector:
    """Register a metric (convenience function)."""
    return _metrics_collector.register_metric(name, metric_type, description, unit)


def record_metric(
    name: str,
    value: float,
    labels: Optional[Dict[str, str]] = None,
) -> bool:
    """Record a metric (convenience function)."""
    return _metrics_collector.record(name, value, labels)


def timing_metric(
    name: str,
    start_time: float,
    end_time: Optional[float] = None,
    labels: Optional[Dict[str, str]] = None,
) -> bool:
    """Record a timing metric (convenience function)."""
    return _metrics_collector.timing(name, start_time, end_time, labels)


def get_metrics() -> Dict[str, Metric]:
    """Get all metrics (convenience function)."""
    return _metrics_collector.get_metrics()


def get_metrics_statistics() -> Dict[str, Any]:
    """Get metrics statistics (convenience function)."""
    return _metrics_collector.get_statistics()


def export_metrics() -> str:
    """Export metrics (convenience function)."""
    import json
    return json.dumps(_metrics_collector.to_dict(), indent=2)
