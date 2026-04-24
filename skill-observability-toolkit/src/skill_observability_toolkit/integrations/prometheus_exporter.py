"""
Prometheus Metrics Exporter for skill-observability-toolkit.

Provides Prometheus-compatible metrics export with support for:
- Counters (monotonically increasing)
- Gauges (up/down values)
- Histograms (distributions)
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricFamily:
    """Represents a metric family (e.g., request_latency_seconds)."""

    name: str
    metric_type: str  # counter, gauge, histogram
    description: str = ""
    help_text: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    values: list[tuple[dict[str, str], float]] = field(default_factory=list)

    def to_prometheus(self, namespace: str) -> str:
        """Convert to Prometheus exposition format."""
        prefixed_name = f"{namespace}_{self.name}" if namespace else self.name
        lines = []

        if self.help_text:
            lines.append(f"# HELP {prefixed_name} {self.help_text}")
        lines.append(f"# TYPE {prefixed_name} {self.metric_type}")

        for labels, value in self.values:
            label_str = ""
            if labels:
                label_str = "{" + ",".join(f'{k}="{v}"' for k, v in labels.items()) + "}"
            lines.append(f"{prefixed_name}{label_str} {value}")

        return "\n".join(lines)


class PrometheusExporter:
    """
    Prometheus metrics exporter.

    Provides methods to create and export Prometheus-compatible metrics.

    Example:
        exporter = PrometheusExporter(namespace="skill_obs")
        exporter.increment_counter("skill_executions_total", labels={"skill": "my-skill"})
        output = exporter.to_prometheus_format()
    """

    def __init__(
        self, namespace: str = "skill_obs", const_labels: dict[str, str] | None = None
    ):
        """
        Initialize the exporter.

        Args:
            namespace: Prometheus namespace prefix for all metrics
            const_labels: Labels applied to all metrics
        """
        self.namespace = namespace
        self.const_labels = const_labels or {}
        self._counters: dict[str, tuple[dict[str, str], float]] = {}
        self._gauges: dict[str, tuple[dict[str, str], float]] = {}
        self._histograms: dict[str, list[tuple[dict[str, str], float]]] = {}

    @property
    def metrics(self) -> dict[str, Any]:
        """Get all metrics as a dictionary."""
        return {
            "counters": self._counters,
            "gauges": self._gauges,
            "histograms": self._histograms,
        }

    def increment_counter(
        self, name: str, value: float = 1.0, labels: dict[str, str] | None = None
    ):
        """Increment a counter metric."""
        full_labels = {**self.const_labels, **(labels or {})}
        key = (name, tuple(sorted(full_labels.items())))

        if key not in self._counters:
            self._counters[key] = (full_labels, 0.0)
        self._counters[key] = (full_labels, self._counters[key][1] + value)

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None):
        """Set a gauge metric value."""
        full_labels = {**self.const_labels, **(labels or {})}
        key = (name, tuple(sorted(full_labels.items())))
        self._gauges[key] = (full_labels, value)

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ):
        """Observe a value for histogram metric."""
        full_labels = {**self.const_labels, **(labels or {})}
        key = (name, tuple(sorted(full_labels.items())))

        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append((full_labels, value))

    def to_prometheus_format(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines = []

        for (name, labels), (label_dict, value) in self._counters.items():
            prefixed = f"{self.namespace}_{name}" if self.namespace else name
            lines.append(f"# TYPE {prefixed} counter")
            label_str = ""
            if label_dict:
                label_str = "{" + ",".join(f'{k}="{v}"' for k, v in label_dict.items()) + "}"
            lines.append(f"{prefixed}{label_str} {value}")

        for (name, labels), (label_dict, value) in self._gauges.items():
            prefixed = f"{self.namespace}_{name}" if self.namespace else name
            lines.append(f"# TYPE {prefixed} gauge")
            label_str = ""
            if label_dict:
                label_str = "{" + ",".join(f'{k}="{v}"' for k, v in label_dict.items()) + "}"
            lines.append(f"{prefixed}{label_str} {value}")

        for (name, labels), values in self._histograms.items():
            prefixed = f"{self.namespace}_{name}" if self.namespace else name
            lines.append(f"# TYPE {prefixed} histogram")
            for label_dict, value in values:
                label_str = ""
                if label_dict:
                    label_str = "{" + ",".join(f'{k}="{v}"' for k, v in label_dict.items()) + "}"
                lines.append(f"{prefixed}{label_str} {value}")

        return "\n".join(lines)

    def clear(self):
        """Clear all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
