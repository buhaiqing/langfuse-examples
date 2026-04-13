# Monitoring Guide

> **Purpose**: Dashboard designs and alert configurations  
> **Last Updated**: 2026-04-13

---

## Alert Systems Overview

本项目包含两套并行的告警系统：

### 1. 传统告警 (Phase 5)

基于固定阈值的规则引擎，适合明确的业务规则。

**特点**:
- ✅ 手动配置阈值
- ✅ 即时触发
- ✅ 支持任意自定义指标
- ✅ 检测间隔: 默认 5 分钟

**示例配置**:
```yaml
# 成功率告警
metric: success_rate
threshold: 0.95
operator: lt  # less than
severity: critical

# P95延迟告警
metric: latency_p95_ms
threshold: 500
operator: gt  # greater than
severity: warning
```

**文档**: [docs/alert-monitoring-guide.md](alert-monitoring-guide.md)

### 2. 智能告警 (Phase 6)

基于机器学习的异常检测，自动发现未知异常模式。

**特点**:
- 🤖 自动学习历史数据
- 📊 多维关联分析
- 🎯 减少误报率
- ⚡ 检测间隔: 默认 10 分钟
- 🔧 需要 ML 依赖: prophet, pyod, pandas, numpy, sklearn

**检测指标**:
- 成功率 (Success Rate)
- P95 延迟 (Latency P95)
- 请求率 (Request Rate / QPS)
- 用户满意度 (Satisfaction)

**文档**: [docs/smart-alerting-guide.md](smart-alerting-guide.md), [docs/phase6-quick-start.md](phase6-quick-start.md)

### 两者关系

| 特性 | 传统告警 | 智能告警 |
|------|---------|----------|
| **用途** | 已知规则监控 | 未知异常发现 |
| **配置** | 手动设置阈值 | 自动训练模型 |
| **适用** | SLA 监控、业务规则 | 趋势异常、模式变化 |
| **运行** | 并行运行，互不干扰 | 并行运行，互不干扰 |
| **通知** | 共享通知渠道 | 共享通知渠道 |

**推荐策略**: 同时启用两套系统，传统告警处理明确的业务规则，智能告警发现潜在问题。

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
