# Monitoring Guide

> **Purpose**: Dashboard designs and alert configurations  
> **Last Updated**: 2026-04-08

---

## Key Metrics

### Success Rate
```yaml
metric: tool_call_success_rate
formula: (successful_calls / total_calls) * 100
target: >99.5%
alert:
  condition: < 99%
  duration: 5m
  severity: warning
```

### Latency
```yaml
metrics:
  - tool_call_duration_p50
  - tool_call_duration_p95
  - tool_call_duration_p99
target: P95 < 500ms
alert:
  condition: P95 > 500ms
  duration: 10m
  severity: warning
```

### User Satisfaction
```yaml
metric: user_acceptance_rate
formula: (accepted / total_with_feedback) * 100
target: >85%
```

## Dashboard Layout

```
┌────────────────────────────────────────┐
│  Success Rate: 99.2%                   │
│  P95 Latency: 320ms                    │
│  Satisfaction: 87.5%                   │
├────────────────────────────────────────┤
│  [Time Series: Success Rate Chart]     │
├────────────────────────────────────────┤
│  [Latency Heatmap]                     │
├────────────────────────────────────────┤
│  [Prompt Version Comparison Table]     │
└────────────────────────────────────────┘
```

---

**See Full Documentation**: Session analytics, prompt effectiveness, alert configuration, incident response.
