# MCP 性能指标对照表

> **文档版本**: 1.0.0  
> **最后更新**: 2026-04-30  
> **适用范围**: mcp-with-tracing 项目所有性能指标

---

## 目录

1. [指标总览](#指标总览)
2. [可用性指标](#可用性指标)
3. [性能指标](#性能指标)
4. [质量指标](#质量指标)
5. [会话与用户指标](#会话与用户指标)
6. [错误分析指标](#错误分析指标)
7. [工具维度指标](#工具维度指标)
8. [缓存与基础设施指标](#缓存与基础设施指标)
9. [指标采集方法映射](#指标采集方法映射)
10. [Prometheus 指标命名规范](#prometheus-指标命名规范)

---

## 指标总览

| 类别 | 指标数量 | 已实现 | 覆盖率 |
|------|---------|-------|--------|
| 可用性指标 | 4 | 4 | 100% |
| 性能指标 | 6 | 6 | 100% |
| 质量指标 | 3 | 3 | 100% |
| 会话与用户指标 | 1 | 1 | 100% |
| 错误分析指标 | 2 | 2 | 100% |
| 工具维度指标 | 1 | 1 | 100% |
| 缓存与基础设施 | 4 | 4 | 100% |
| **总计** | **21** | **21** | **100%** |

---

## 可用性指标

### 1. 成功率 (Success Rate)

| 属性 | 值 |
|------|---|
| **指标名称** | `success_rate` |
| **数据类型** | `float` (0.0 - 1.0) |
| **采集方法** | `MetricsCollector.collect_success_rate()` |
| **计算公式** | `(total_traces - error_traces) / total_traces` |
| **时间窗口** | 可配置 (默认 10 分钟) |
| **告警阈值** | `< 0.99` (WARNING), `< 0.95` (CRITICAL) |
| **Prometheus 指标** | `mcp_success_rate` |
| **Grafana 面板** | "成功率趋势" |

**代码示例**:
```python
collector = MetricsCollector(window_minutes=10)
rate = collector.collect_success_rate()  # 返回 0.95
```

---

### 2. 错误率 (Error Rate)

| 属性 | 值 |
|------|---|
| **指标名称** | `error_rate` |
| **数据类型** | `float` (0.0 - 1.0) |
| **采集方法** | 推导: `1 - success_rate` |
| **告警阈值** | `> 0.01` (WARNING), `> 0.05` (CRITICAL) |
| **Prometheus 指标** | `mcp_error_rate` |

---

### 3. 系统可用性 (Uptime)

| 属性 | 值 |
|------|---|
| **指标名称** | `uptime_seconds` |
| **数据类型** | `float` (秒) |
| **采集方法** | `health.py: get_health_status()` |
| **计算公式** | `current_time - start_time` |
| **Prometheus 指标** | `mcp_process_uptime_seconds` |

---

### 4. Langfuse 连接状态

| 属性 | 值 |
|------|---|
| **指标名称** | `langfuse_connection_status` |
| **数据类型** | `bool` / `enum` (connected/disconnected/error) |
| **采集方法** | `health.py` 组件检查 |
| **Prometheus 指标** | `mcp_langfuse_connected` (1/0) |

---

## 性能指标

### 5. P50 延迟 (中位数延迟)

| 属性 | 值 |
|------|---|
| **指标名称** | `latency_p50` |
| **数据类型** | `float` (毫秒) |
| **采集方法** | `MetricsCollector.collect_latency_p50()` |
| **计算公式** | `np.percentile(durations, 50)` |
| **告警阈值** | `> 500ms` (WARNING), `> 1000ms` (CRITICAL) |
| **Prometheus 指标** | `mcp_latency_p50_ms` |
| **Grafana 面板** | "P50/P95/P99 延迟对比" |

**代码示例**:
```python
p50 = collector.collect_latency_p50()  # 返回 150.5 (ms)
```

---

### 6. P95 延迟

| 属性 | 值 |
|------|---|
| **指标名称** | `latency_p95` |
| **数据类型** | `float` (毫秒) |
| **采集方法** | `MetricsCollector.collect_latency_p95()` |
| **计算公式** | `np.percentile(durations, 95)` |
| **告警阈值** | `> 1000ms` (WARNING), `> 2000ms` (CRITICAL) |
| **Prometheus 指标** | `mcp_latency_p95_ms` |

---

### 7. P99 延迟 (长尾延迟)

| 属性 | 值 |
|------|---|
| **指标名称** | `latency_p99` |
| **数据类型** | `float` (毫秒) |
| **采集方法** | `MetricsCollector.collect_latency_p99()` |
| **计算公式** | `np.percentile(durations, 99)` |
| **告警阈值** | `> 2000ms` (WARNING), `> 5000ms` (CRITICAL) |
| **Prometheus 指标** | `mcp_latency_p99_ms` |
| **重要性** | 监控长尾延迟，发现极端慢请求 |

---

### 8. 请求率 (QPS)

| 属性 | 值 |
|------|---|
| **指标名称** | `request_rate` |
| **数据类型** | `float` (requests/second) |
| **采集方法** | `MetricsCollector.collect_request_rate()` |
| **计算公式** | `total_traces / (window_minutes * 60)` |
| **告警阈值** | 突增 `> 200%` (WARNING), 突降 `< 50%` (WARNING) |
| **Prometheus 指标** | `mcp_request_rate_qps` |

**代码示例**:
```python
qps = collector.collect_request_rate()  # 返回 8.5 (req/s)
```

---

## 质量指标

### 9. 用户满意度 (Satisfaction Score)

| 属性 | 值 |
|------|---|
| **指标名称** | `satisfaction` |
| **数据类型** | `float` (1.0 - 5.0) 或 `None` |
| **采集方法** | `MetricsCollector.collect_avg_satisfaction()` |
| **数据来源** | `FeedbackCollector.get_average_rating()` |
| **告警阈值** | `< 3.5` (WARNING), `< 2.5` (CRITICAL) |
| **Prometheus 指标** | `mcp_user_satisfaction_avg` |

---

### 10. 接受率 (Acceptance Rate)

| 属性 | 值 |
|------|---|
| **指标名称** | `acceptance_rate` |
| **数据类型** | `float` (0.0 - 100.0) |
| **采集方法** | `FeedbackCollector.get_acceptance_rate()` |
| **计算公式** | `(accepts / (accepts + rejects)) * 100` |
| **Prometheus 指标** | `mcp_feedback_acceptance_rate` |

---

### 11. 拒绝率 (Rejection Rate)

| 属性 | 值 |
|------|---|
| **指标名称** | `rejection_rate` |
| **数据类型** | `float` (0.0 - 100.0) |
| **采集方法** | 推导: `100 - acceptance_rate` |
| **Prometheus 指标** | `mcp_feedback_rejection_rate` |

---

## 会话与用户指标

### 12. 活跃会话数 (Active Sessions)

| 属性 | 值 |
|------|---|
| **指标名称** | `active_sessions` |
| **数据类型** | `int` |
| **采集方法** | `MetricsCollector.count_active_sessions()` |
| **计算逻辑** | 基于 `session_id` 去重统计 |
| **告警阈值** | 突增 `> 300%` (WARNING), 归零 (CRITICAL) |
| **Prometheus 指标** | `mcp_active_sessions` |

**代码示例**:
```python
sessions = collector.count_active_sessions()  # 返回 42
```

---

## 错误分析指标

### 13. 错误分类统计 (Error Breakdown)

| 属性 | 值 |
|------|---|
| **指标名称** | `error_breakdown` |
| **数据类型** | `dict[str, int]` |
| **采集方法** | `MetricsCollector.collect_error_breakdown()` |
| **分类策略** | metadata.error_type 或 trace name 模式匹配 |
| **错误类别** | `timeout`, `rate_limit`, `validation_error`, `unknown` |
| **Prometheus 指标** | `mcp_errors_total{type="timeout"}` |

**返回示例**:
```python
{
    "timeout": 5,
    "rate_limit": 2,
    "validation_error": 1,
    "unknown": 3
}
```

---

### 14. 错误总数 (Error Count)

| 属性 | 值 |
|------|---|
| **指标名称** | `error_count` |
| **数据类型** | `int` |
| **采集方法** | `sum(error_breakdown.values())` |
| **Prometheus 指标** | `mcp_errors_total` |

---

## 工具维度指标

### 15. 工具性能指标 (Tool Metrics)

| 属性 | 值 |
|------|---|
| **指标名称** | `tool_metrics` |
| **数据类型** | `dict[str, Any]` |
| **采集方法** | `MetricsCollector.collect_tool_metrics(tool_name)` |
| **包含字段** | `call_count`, `success_rate`, `p50/p95/p99_latency_ms`, `error_count` |
| **Prometheus 指标** | `mcp_tool_calls_total{tool="search_knowledge_base"}` |

**返回示例**:
```python
{
    "tool_name": "search_knowledge_base",
    "call_count": 150,
    "success_rate": 0.96,
    "p50_latency_ms": 120.0,
    "p95_latency_ms": 350.0,
    "p99_latency_ms": 800.0,
    "error_count": 6
}
```

---

## 缓存与基础设施指标

### 16. 缓存命中率 (Cache Hit Rate)

| 属性 | 值 |
|------|---|
| **指标名称** | `cache_hit_rate` |
| **数据类型** | `float` (0.0 - 1.0) |
| **采集方法** | `MetricsCollector.get_cache_stats()["hit_rate"]` |
| **告警阈值** | `< 0.5` (WARNING) - 可能缓存配置不当 |
| **Prometheus 指标** | `mcp_cache_hit_rate` |

---

### 17. 缓存大小 (Cache Size)

| 属性 | 值 |
|------|---|
| **指标名称** | `cache_size` |
| **数据类型** | `int` |
| **采集方法** | `MetricsCollector.get_cache_stats()["size"]` |
| **最大容量** | 64 (可配置) |
| **Prometheus 指标** | `mcp_cache_entries` |

---

### 18. 缓存 TTL (Cache TTL)

| 属性 | 值 |
|------|---|
| **指标名称** | `cache_ttl_seconds` |
| **数据类型** | `int` (秒) |
| **默认值** | 300 秒 (5 分钟) |
| **Prometheus 指标** | `mcp_cache_ttl_seconds` |

---

### 19. 告警规则数 (Alert Rules Count)

| 属性 | 值 |
|------|---|
| **指标名称** | `alert_rules_loaded` |
| **数据类型** | `int` |
| **采集方法** | `AlertManager.list_rules()` |
| **Prometheus 指标** | `mcp_alert_rules_count` |

---

### 20. 告警监控状态 (Alert Monitor Status)

| 属性 | 值 |
|------|---|
| **指标名称** | `alert_monitor_running` |
| **数据类型** | `bool` (1/0) |
| **采集方法** | `AlertMonitorScheduler.get_status()["is_running"]` |
| **Prometheus 指标** | `mcp_alert_monitor_running` |

---

### 21. ML 异常检测状态 (Smart Alert Status)

| 属性 | 值 |
|------|---|
| **指标名称** | `smart_alert_running` |
| **数据类型** | `bool` (1/0) |
| **采集方法** | `SmartAlertManager.get_status()["is_running"]` |
| **Prometheus 指标** | `mcp_smart_alert_running` |

---

## 指标采集方法映射

| 指标名称 | Python 方法 | 返回类型 | 默认时间窗口 |
|---------|-----------|---------|------------|
| `success_rate` | `collect_success_rate()` | `float` | 10 min |
| `latency_p50` | `collect_latency_p50()` | `float` | 10 min |
| `latency_p95` | `collect_latency_p95()` | `float` | 10 min |
| `latency_p99` | `collect_latency_p99()` | `float` | 10 min |
| `request_rate` | `collect_request_rate()` | `float` | 10 min |
| `satisfaction` | `collect_avg_satisfaction()` | `float \| None` | N/A |
| `active_sessions` | `count_active_sessions()` | `int` | 10 min |
| `error_breakdown` | `collect_error_breakdown()` | `dict` | 10 min |
| `tool_metrics` | `collect_tool_metrics(name)` | `dict` | 10 min |
| `cache_stats` | `get_cache_stats()` | `dict` | N/A |

---

## Prometheus 指标命名规范

### 命名约定

```
mcp_<category>_<metric_name>_<unit>
```

**示例**:
- `mcp_success_rate` (无单位，0-1)
- `mcp_latency_p95_ms` (毫秒)
- `mcp_request_rate_qps` (每秒请求数)
- `mcp_active_sessions` (计数)

### 标签 (Labels) 规范

```promql
# 工具维度指标
mcp_tool_calls_total{tool="search_knowledge_base"}
mcp_tool_latency_p95_ms{tool="generate_response"}
mcp_tool_error_rate{tool="classify_intent"}

# 错误分类
mcp_errors_total{type="timeout"}
mcp_errors_total{type="rate_limit"}
mcp_errors_total{type="validation_error"}

# 告警维度
mcp_alerts_triggered{severity="warning"}
mcp_alerts_triggered{severity="critical"}
```

---

## 快速查询示例

### 获取所有当前指标

```python
from src.observability.metrics_collector import MetricsCollector
from src.observability.health import get_health_status

collector = MetricsCollector(window_minutes=10)

# 核心性能指标
metrics = {
    "success_rate": collector.collect_success_rate(),
    "latency_p50": collector.collect_latency_p50(),
    "latency_p95": collector.collect_latency_p95(),
    "latency_p99": collector.collect_latency_p99(),
    "request_rate": collector.collect_request_rate(),
    "active_sessions": collector.count_active_sessions(),
    "error_breakdown": collector.collect_error_breakdown(),
}

# 系统健康状态
health = get_health_status()
```

---

## 相关文档

- [智能告警指南](smart-alerting-guide.md)
- [监控指南](monitoring-guide.md)
- [事件响应手册](event-response-runbook.md)
- [告警配置指南](alert-config-guide.md)

---

**维护者**: 平台团队  
**下次更新**: 新增指标或修改阈值时
