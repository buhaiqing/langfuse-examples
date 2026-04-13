# 后台告警监控功能说明

> **版本**: 1.0.0  
> **最后更新**: 2026-04-13  
> **状态**: ✅ 已实现

---

## 📋 概述

本系统现已支持**后台自动巡检告警规则**，无需手动调用检查函数。

### 核心功能

1. ✅ **周期性指标采集** - 定期从 Langfuse 获取最新监控数据
2. ✅ **自动规则巡检** - 遍历所有告警规则并比对阈值
3. ✅ **智能告警触发** - 检测到异常时自动发送通知
4. ✅ **可配置检查间隔** - 通过环境变量灵活调整

---

## 🚀 工作原理

### 架构图

```
┌─────────────────────────────────────────────┐
│         MCP Server Startup                  │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  1. Load Alert Rules (alerts.yaml)          │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  2. Start Alert Monitor Scheduler           │
│     (APScheduler - AsyncIOScheduler)        │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  3. Periodic Check Loop (every N minutes)   │
│  ┌───────────────────────────────────────┐  │
│  │ For each enabled alert rule:          │  │
│  │  1. Fetch current metric value        │  │
│  │  2. Compare with threshold            │  │
│  │  3. If exceeded → Trigger alert       │  │
│  │  4. Send notification                 │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### 执行流程

```
T=0min: 服务器启动 → 加载规则 → 启动监控器
T=5min: 第一次检查 → 采集指标 → 比对阈值 → 触发告警（如有）
T=10min: 第二次检查 → ...
T=15min: 第三次检查 → ...
...持续运行...
```

---

## ⚙️ 配置说明

### 1. 检查间隔配置

在 `.env` 文件中设置：

```bash
# 告警检查间隔（分钟）
# 默认值: 5
# 推荐范围: 
#   - 开发环境: 10-30 分钟
#   - 测试环境: 5-10 分钟
#   - 生产环境: 1-5 分钟
ALERT_CHECK_INTERVAL_MINUTES=5
```

### 2. 告警规则配置

在 `config/alerts.yaml` 中定义规则（详见 [告警规则配置指南](./alert-config-guide.md)）：

```yaml
alerts:
  - name: "success-rate-low"
    metric: "success_rate"
    threshold: 0.95
    operator: "lt"
    severity: "warning"
    window_minutes: 60
    channels:
      - "wecom"
      - "slack"
    enabled: true
```

### 3. 通知渠道配置

在 `.env` 中配置通知渠道的 webhook URL：

```bash
# 企业微信
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/...

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# Email
ALERT_EMAIL_SMTP_HOST=smtp.example.com
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_SENDER=alerts@example.com
ALERT_EMAIL_PASSWORD=your-password
ALERT_EMAIL_RECIPIENTS=admin@example.com
```

---

## 🎯 支持的监控指标

### 内置指标

| 指标名称 | 说明 | 数据来源 | 单位 |
|---------|------|---------|------|
| `success_rate` | 成功率 | Langfuse traces | 0.0-1.0 |
| `latency_p95_ms` | P95 延迟 | Langfuse trace durations | 毫秒 |
| `latency_p99_ms` | P99 延迟 | Langfuse trace durations (使用 P95 代替) | 毫秒 |
| `avg_rating` | 平均用户评分 | Langfuse scores | 1-5 |
| `error_rate` | 错误率 | 1 - success_rate | 0.0-1.0 |

### 自定义指标扩展

如需添加自定义指标，修改 `alert_monitor.py` 中的 `_get_metric_value()` 方法：

```python
async def _get_metric_value(self, rule: AlertRule) -> Optional[float]:
    metric = rule.metric.lower()
    
    if metric == 'custom_metric':
        # Your custom logic here
        return calculate_custom_metric()
    
    # ... existing metrics ...
```

---

## 📊 运行示例

### 启动服务器

```bash
$ python -m src.server

============================================================
Loading alert rules...
============================================================
✓ Registered alert rule: success-rate-low-warning
✓ Registered alert rule: latency-p95-high-warning
✓ Registered alert rule: success-rate-critical

✅ Loaded 6 alert rule(s) from config/alerts.yaml
============================================================

============================================================
Starting alert monitoring...
============================================================

🔄 Starting alert monitor (interval: 5min)...
✅ Alert monitor started successfully
   - Check interval: 5 minutes
   - Next check in: 5 minutes
✅ Alert monitoring enabled (every 5 minutes)
============================================================
```

### 定期检查输出

```
🔍 Running alert check (6 rules)...
   ✓ success-rate-low-warning: OK (value=0.98)
   ✓ latency-p95-high-warning: OK (value=320.5)
   🚨 success-rate-critical: TRIGGERED (value=0.85, threshold=lt 0.90)
   ✓ feedback-rating-low: OK (value=4.2)
   ✓ error-rate-spike: OK (value=0.02)
   ⊘ latency-p99-high: No data available

✅ Alert check complete: 1 alert(s) triggered
```

### 告警触发通知

当检测到异常时，会自动发送通知到配置的渠道：

**企业微信示例**:
```
🚨 **告警通知**

**告警名称**: success-rate-critical
**严重级别**: CRITICAL
**监控指标**: success_rate
**当前值**: `0.85`
**阈值条件**: `lt 0.90`
**时间窗口**: 30 分钟
**触发时间**: 2026-04-13T10:30:00+00:00

**详细信息**: Alert 'success-rate-critical': success_rate = 0.85 (threshold: lt 0.90)
```

---

## 🔧 高级配置

### 1. 不同环境的检查间隔

**开发环境** (`.env.dev`):
```bash
ALERT_CHECK_INTERVAL_MINUTES=15  # 降低频率，减少日志噪音
```

**生产环境** (`.env.prod`):
```bash
ALERT_CHECK_INTERVAL_MINUTES=2   # 高频检查，快速发现问题
```

### 2. 禁用自动监控

如果只想手动触发检查，可以注释掉监控启动代码：

```python
# In server.py
# monitor = start_alert_monitor(check_interval_minutes=check_interval)
```

或者设置很长的间隔：
```bash
ALERT_CHECK_INTERVAL_MINUTES=1440  # 每天检查一次（相当于禁用）
```

### 3. 动态调整检查间隔

目前需要重启服务器才能更改间隔。未来可扩展为 API 端点：

```python
# Future: POST /api/alerts/monitor/config
{
  "check_interval_minutes": 10
}
```

---

## 🐛 故障排查

### 问题 1: 监控器未启动

**症状**: 启动时显示 "Failed to start alert monitor"

**原因**: 
- APScheduler 未安装
- 配置文件语法错误

**解决**:
```bash
# 安装依赖
pip install apscheduler

# 检查配置
python scripts/test_alert_config.py
```

### 问题 2: 告警未触发

**症状**: 指标异常但未收到通知

**检查清单**:
1. ✅ 告警规则已启用 (`enabled: true`)
2. ✅ 通知渠道已正确配置（webhook URL 有效）
3. ✅ 指标数据存在（Langfuse 中有 traces）
4. ✅ 阈值设置合理

**调试步骤**:
```python
# 手动检查规则
from src.observability.alerting import get_alert_manager

manager = get_alert_manager()
print(manager.list_rules())  # 查看已注册的规则

# 手动触发检查
from src.observability.metrics_collector import MetricsCollector

collector = MetricsCollector()
current_rate = collector.collect_success_rate()
print(f"Current success rate: {current_rate}")

alert = manager.check_rule("success-rate-low", current_rate)
print(f"Alert triggered: {alert is not None}")
```

### 问题 3: 指标数据为空

**症状**: 日志显示 "No data available"

**原因**: 
- Langfuse 中没有足够的 traces
- 时间窗口内没有数据

**解决**:
1. 确认应用正在生成 traces
2. 检查 `window_minutes` 设置是否合理
3. 等待足够的时间积累数据

---

## 📈 性能考虑

### 资源占用

| 指标 | 估算值 | 说明 |
|------|--------|------|
| **内存占用** | ~10-20 MB | APScheduler + MetricsCollector |
| **CPU 占用** | < 1% | 仅在检查时短暂使用 |
| **网络请求** | 每次检查 2-5 次 | 查询 Langfuse API |
| **数据库负载** | 低 | 只读查询，无写入 |

### 优化建议

1. **合理设置检查间隔**
   - 过短：增加 API 调用频率，可能触发限流
   - 过长：延迟发现问题的时间

2. **使用时间窗口缓存**
   - `MetricsCollector` 内部已实现缓存
   - 同一窗口内的多次检查复用数据

3. **限制并发检查**
   - APScheduler 的 `max_instances=1` 防止重叠执行

---

## 🎓 最佳实践

### 1. 分级检查策略

```yaml
# 关键指标 - 高频检查
- name: "success-rate-critical"
  window_minutes: 15
  # 在 .env 中设置 ALERT_CHECK_INTERVAL_MINUTES=2

# 次要指标 - 低频检查
- name: "feedback-rating-trend"
  window_minutes: 120
  enabled: false  # 或禁用以减少检查频率
```

### 2. 避免告警风暴

```yaml
# ❌ 避免：多个相似阈值的规则
- name: "rate-warning-1"
  threshold: 0.95
- name: "rate-warning-2"
  threshold: 0.94  # 太接近，可能同时触发

# ✅ 推荐：明显的分级
- name: "rate-warning"
  threshold: 0.95
  severity: "warning"
- name: "rate-critical"
  threshold: 0.90
  severity: "critical"
```

### 3. 监控监控器本身

定期检查监控器状态：

```python
from src.observability.alert_monitor import get_alert_monitor

monitor = get_alert_monitor()
status = monitor.get_status()
print(status)
# {
#   "is_running": True,
#   "check_interval_minutes": 5,
#   "registered_rules": 6,
#   "scheduler_jobs": 1
# }
```

---

## 🔗 相关文档

- [告警规则配置指南](./alert-config-guide.md) - 完整的 YAML 配置语法
- [企业微信配置](./wecom-alert-setup.md) - 通知渠道设置
- [事件响应手册](./event-response-runbook.md) - 告警处理流程
- [智能告警系统](../devs/smart_alerting_implementation.md) - ML 异常检测

---

## 📅 更新日志

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-04-13 | 初始版本，基于 APScheduler 的后台监控 |

---

## ❓ 常见问题

**Q: 监控器会在服务器重启后自动恢复吗？**  
A: 是的，每次启动服务器时都会自动加载规则并启动监控器。

**Q: 可以运行时动态添加/删除规则吗？**  
A: 可以。通过 API 注册的新规则会在下一次检查周期生效。

**Q: 如果 Langfuse API 不可用会怎样？**  
A: 监控器会捕获异常并记录日志，不会导致服务器崩溃。下一次检查会继续尝试。

**Q: 如何临时暂停监控？**  
A: 目前没有运行时暂停功能。可以设置很长的检查间隔或重启服务器时不启动监控器。

**Q: 监控器会影响服务器性能吗？**  
A: 影响极小。检查操作是异步的，且使用了缓存机制。
