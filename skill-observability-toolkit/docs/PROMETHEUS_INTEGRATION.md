# Prometheus Integration Guide

Real-time monitoring capabilities with Prometheus, Grafana, and Trust Score calculation.

## Quick Start

### 1. Start Metrics Server

```python
from skill_observability_toolkit.integrations import MetricsServer

server = MetricsServer(port=9090)
server.start()
```

### 2. Record Metrics

```python
from skill_observability_toolkit.integrations.prometheus_exporter import PrometheusExporter

exporter = PrometheusExporter(namespace="skill_obs")

exporter.increment_counter("skill_executions_total", labels={"skill": "my-skill"})
exporter.set_gauge("trust_score", 0.85, labels={"skill": "my-skill"})
exporter.observe_histogram("latency_seconds", 0.125)

print(exporter.to_prometheus_format())
```

### 3. Prometheus Config

```yaml
scrape_configs:
  - job_name: 'skill-observability'
    static_configs:
      - targets: ['localhost:9090']
```

## Modules

### PrometheusExporter

Export metrics in Prometheus format.

**Methods:**
- `increment_counter(name, value=1.0, labels={})` - Increment counter
- `set_gauge(name, value, labels={})` - Set gauge value
- `observe_histogram(name, value, labels={})` - Add histogram observation
- `to_prometheus_format()` - Export in Prometheus format
- `clear()` - Reset all metrics

### TrustScoreCalculator

Real-time trust score with sliding window and exponential decay.

```python
from skill_observability_toolkit.stop.trust_score import TrustScoreCalculator, TrustScoreConfig

config = TrustScoreConfig(window_size=30, min_samples=5)
calculator = TrustScoreCalculator(config)

calculator.record_check(passed=True)
calculator.record_check(passed=False)

score = calculator.get_current_score()  # 0.0 - 1.0
stats = calculator.get_stats()
```

### MetricsServer

HTTP server exposing /metrics endpoint.

```python
from skill_observability_toolkit.integrations import MetricsServer

with MetricsServer(port=9090) as server:
    # Server running
    pass
```

### GrafanaDashboardGenerator

Generate Grafana dashboard JSON.

```python
from skill_observability_toolkit.integrations.grafana_dashboard import (
    DashboardConfig,
    GrafanaDashboardGenerator,
)

config = DashboardConfig(title="Skill Observability")
generator = GrafanaDashboardGenerator(config)

generator.add_graph_panel("Executions", ["skill_executions_total"])
generator.add_singlestat_panel("Trust Score", "trust_score")

dashboard = generator.generate()
```

## Metrics Reference

| Metric | Type | Description |
|--------|------|-------------|
| `skill_executions_total` | Counter | Total skill executions |
| `trust_score` | Gauge | Current trust score (0-1) |
| `latency_seconds` | Histogram | Skill execution latency |
