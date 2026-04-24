"""Tests for Prometheus Metrics Exporter."""

from skill_observability_toolkit.integrations.prometheus_exporter import (
    MetricFamily,
    PrometheusExporter,
)


def test_prometheus_exporter_initialization():
    """Test PrometheusExporter can be initialized."""
    exporter = PrometheusExporter(namespace="skill_obs")
    assert exporter.namespace == "skill_obs"
    assert "counters" in exporter.metrics
    assert "gauges" in exporter.metrics
    assert "histograms" in exporter.metrics


def test_counter_metric_export():
    """Test counter metric exports to Prometheus format."""
    exporter = PrometheusExporter(namespace="test")
    exporter.increment_counter("skill_executions_total", labels={"skill": "test-skill"})

    output = exporter.to_prometheus_format()
    assert "skill_executions_total" in output
    assert "# TYPE test_skill_executions_total counter" in output


def test_gauge_metric_export():
    """Test gauge metric exports to Prometheus format."""
    exporter = PrometheusExporter(namespace="test")
    exporter.set_gauge("trust_score", 0.85, labels={"skill": "test-skill"})

    output = exporter.to_prometheus_format()
    assert "trust_score" in output
    assert "# TYPE test_trust_score gauge" in output


def test_histogram_metric_export():
    """Test histogram metric exports to Prometheus format."""
    exporter = PrometheusExporter(namespace="test")
    exporter.observe_histogram("latency_seconds", 0.5, labels={"skill": "test-skill"})
    exporter.observe_histogram("latency_seconds", 1.2, labels={"skill": "test-skill"})

    output = exporter.to_prometheus_format()
    assert "latency_seconds" in output
    assert "# TYPE test_latency_seconds histogram" in output


def test_multiple_labels():
    """Test metrics with multiple labels."""
    exporter = PrometheusExporter(namespace="test")
    exporter.increment_counter("requests_total", labels={
        "method": "GET",
        "status": "200",
    })

    output = exporter.to_prometheus_format()
    assert 'method="GET"' in output
    assert 'status="200"' in output


def test_metric_family_initialization():
    """Test MetricFamily can be initialized."""
    family = MetricFamily(
        name="test_metric",
        metric_type="counter",
        description="Test metric",
        help_text="A test metric",
    )
    assert family.name == "test_metric"
    assert family.metric_type == "counter"
    assert family.description == "Test metric"


def test_metric_family_to_prometheus():
    """Test MetricFamily converts to Prometheus format."""
    family = MetricFamily(
        name="test_metric",
        metric_type="counter",
        help_text="A test metric",
    )
    family.values.append(({"label1": "value1"}, 10.0))

    output = family.to_prometheus("test")
    assert "# HELP test_test_metric A test metric" in output
    assert "# TYPE test_test_metric counter" in output
    assert "test_test_metric" in output


def test_prometheus_exporter_with_const_labels():
    """Test PrometheusExporter with constant labels."""
    exporter = PrometheusExporter(
        namespace="test",
        const_labels={"env": "production"},
    )
    exporter.increment_counter("requests_total")

    output = exporter.to_prometheus_format()
    assert 'env="production"' in output


def test_counter_increment_multiple_times():
    """Test counter accumulates values correctly."""
    exporter = PrometheusExporter(namespace="test")
    exporter.increment_counter("requests_total", value=1.0)
    exporter.increment_counter("requests_total", value=2.0)

    output = exporter.to_prometheus_format()
    lines = output.split("\n")
    metric_line = [line for line in lines if "requests_total" in line and not line.startswith("#")][0]
    value = float(metric_line.split()[-1])
    assert value == 3.0


def test_prometheus_exporter_clear():
    """Test clear() method resets all metrics."""
    exporter = PrometheusExporter(namespace="test")
    exporter.increment_counter("requests_total")
    exporter.set_gauge("temperature", 25.0)

    exporter.clear()
    output = exporter.to_prometheus_format()
    assert output == ""
