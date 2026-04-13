# Phase 6 智能告警快速启动指南

> **状态**: ✅ 已集成到主应用  
> **版本**: v1.0  
> **更新日期**: 2026-04-13

---

## 🎯 概述

Phase 6 智能告警系统现已**完全集成**到 MCP Server 中，提供基于机器学习的异常检测能力。系统会在服务器启动时自动运行，无需额外配置。

### 核心功能

- 🤖 **自动异常检测**: 使用 Prophet 和 PyOD 算法
- 📊 **多维度监控**: 成功率、延迟、流量、满意度
- 🔔 **智能告警**: 自动发现传统阈值无法检测的异常
- ⚡ **后台运行**: 独立的监控线程，不影响主服务

---

## 🚀 快速开始

### 1. 确认依赖已安装

```bash
# 检查 ML 依赖
pip list | grep -E "prophet|pyod|pandas|numpy|scikit-learn"

# 如果缺失，安装依赖
pip install prophet pyod pandas numpy scikit-learn
```

**macOS 用户注意**:
```bash
brew install libomp  # Prophet 需要 OpenMP 支持
```

### 2. 配置环境变量（可选）

编辑 `.env` 文件：

```bash
# 智能告警检测间隔（默认 10 分钟）
SMART_ALERT_CHECK_INTERVAL_MINUTES=10

# 基础告警检测间隔（默认 5 分钟）
ALERT_CHECK_INTERVAL_MINUTES=5
```

**推荐配置**:
- 生产环境: `SMART_ALERT_CHECK_INTERVAL_MINUTES=10-15`
- 测试环境: `SMART_ALERT_CHECK_INTERVAL_MINUTES=5`

### 3. 启动服务器

```bash
# 标准启动方式
python -m src.server

# 或使用 Makefile
make run
```

### 4. 观察启动日志

成功启动后，你应该看到类似输出：

```
============================================================
Starting smart ML-based anomaly detection...
============================================================
✅ Smart ML anomaly detection enabled (every 10 minutes)
   - Prophet time series forecasting
   - PyOD multivariate anomaly detection
   - Auto-detects: success_rate, latency_p95, request_rate, satisfaction
============================================================
```

---

## 📊 工作原理

### 启动流程

```
服务器启动
    ↓
加载基础告警规则 (Phase 5)
    ↓
启动智能告警监控 (Phase 6) ← 新增
    ↓
初始化 MetricsCollector
    ↓
创建 AnomalyDetector
    ↓
启动后台监控线程
    ↓
等待首次检测周期
```

### 检测周期

每个检测周期（默认 10 分钟）执行以下步骤：

1. **数据收集**: 从 Langfuse API 获取最新指标
2. **模型训练**: 
   - 首次运行: 训练所有模型（需要 24 小时历史数据）
   - 后续: 每小时重新训练一次
3. **异常检测**:
   - 单变量检测 (Prophet): 成功率、延迟、流量
   - 多变量检测 (PyOD): 综合特征分析
4. **告警触发**: 发现异常时发送通知

### 检测的指标

| 指标 | 说明 | 检测方法 |
|------|------|---------|
| `success_rate` | 工具调用成功率 | Prophet + PyOD |
| `latency_p95` | P95 响应延迟 | Prophet + PyOD |
| `request_rate` | 每秒请求数 (QPS) | Prophet + PyOD |
| `satisfaction` | 用户满意度评分 | PyOD (多变量) |

---

## 🔍 验证集成

### 方法 1: 运行验证脚本

```bash
python scripts/verify_phase6_integration.py
```

预期输出：
```
🎉 All integration tests passed!
```

### 方法 2: 检查服务器日志

启动服务器后，查找以下日志：

```
✅ Smart ML anomaly detection enabled (every 10 minutes)
```

### 方法 3: 查看运行中的线程

```python
import threading
[thread.name for thread in threading.enumerate()]
# 应该包含: 'SmartAlertMonitor'
```

---

## 📈 监控智能告警

### 查看告警统计

在代码中访问：

```python
from src.observability.smart_alerting import SmartAlertManager

# 获取全局实例（需要在服务器启动后）
# 注意：当前实现中 smart_manager 是局部变量
# 建议添加全局访问方法或 API 端点
```

### 告警消息示例

#### 单变量异常

```
🤖 ML检测到单指标异常
指标: success_rate
当前值: 0.70
预期范围: 0.90 - 1.00
偏离分数: 3.00
严重程度: CRITICAL
```

#### 多变量异常

```
🤖 ML检测到多维异常
异常分数: 0.90
成功率: 70.00%
P95延迟: 800.00ms
请求率: 2.00/s
满意度: 2.00
严重程度: CRITICAL
```

---

## ⚙️ 高级配置

### 调整检测参数

编辑 `src/server.py` 中的初始化代码：

```python
# 更频繁的检测（5 分钟）
smart_manager = SmartAlertManager(detection_interval_minutes=5)

# 较宽松的检测（30 分钟）
smart_manager = SmartAlertManager(detection_interval_minutes=30)
```

### 配置通知渠道

智能告警继承自 `AlertManager`，支持所有通知渠道：

```python
from src.observability.notifiers import WeComNotifier, SlackNotifier
from src.observability.alerting import AlertChannel

# 企业微信
wecom_notifier = WeComNotifier(
    webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
)
smart_manager.register_notification_handler(AlertChannel.WEBHOOK, wecom_notifier)

# Slack
slack_notifier = SlackNotifier(
    webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK"
)
smart_manager.register_notification_handler(AlertChannel.SLACK, slack_notifier)
```

### 调整模型参数

修改 `src/observability/anomaly_detector.py`：

```python
# Prophet 参数
ts_detector = TimeSeriesAnomalyDetector(
    uncertainty_samples=200  # 增加采样数提高精度（默认 100）
)

# PyOD 参数
mv_detector = MultivariateAnomalyDetector(
    method='iforest',        # 或 'lof'
    contamination=0.05       # 预期异常比例（默认 0.05）
)
```

---

## 🐛 故障排查

### 问题 1: 导入失败

**错误**: `ModuleNotFoundError: No module named 'prophet'`

**解决**:
```bash
pip install prophet pyod pandas numpy scikit-learn
```

### 问题 2: macOS libomp 错误

**错误**: `Library not loaded: @rpath/libomp.dylib`

**解决**:
```bash
brew install libomp
```

### 问题 3: 模型训练失败

**错误**: `Insufficient data for training`

**原因**: 历史数据不足 50 个数据点

**解决**:
- 等待系统运行至少 24 小时
- 或降低检测间隔以更快积累数据
- 检查 Langfuse API 连接是否正常

### 问题 4: 检测周期失败

**错误**: `Detection cycle failed: ...`

**解决**:
- 检查 Langfuse API 凭证
- 验证网络连接
- 查看详细错误日志

**注意**: 单次失败不会中断监控线程，系统会自动重试。

---

## 📊 性能影响

| 指标 | 值 | 说明 |
|------|-----|------|
| CPU 占用 | 5-10% | 模型训练期间 |
| 内存占用 | 200-500MB | 取决于历史数据量 |
| API 调用频率 | 每 10 分钟 | 可配置 |
| 检测延迟 | < 1 秒 | 单次检测时间 |
| 训练时间 | 5-10 秒 | 24 小时数据，3 个指标 |

---

## 🎓 最佳实践

### 1. 初期观察期

部署后的前 24-48 小时：
- ✅ 监控系统资源使用情况
- ✅ 观察误报率
- ✅ 不要立即调整参数
- ✅ 记录正常基线行为

### 2. 参数调优

根据实际运行情况调整：

**高误报率** (> 20%):
- 增加 `contamination` 参数 (0.05 → 0.10)
- 增加检测间隔 (10min → 15min)
- 增加 `uncertainty_samples` (100 → 200)

**漏报率高**:
- 减少 `contamination` 参数 (0.05 → 0.02)
- 减少检测间隔 (10min → 5min)
- 尝试 LOF 算法代替 Isolation Forest

### 3. 通知策略

避免告警疲劳：
- 优先配置关键渠道（如 PagerDuty）
- 设置告警分组和去重
- 区分 INFO/WARNING/CRITICAL 级别

### 4. 与其他告警共存

智能告警与基础告警可以同时运行：
- **基础告警**: 明确的阈值规则（如成功率 < 95%）
- **智能告警**: 发现未知异常模式
- 两者互补，不冲突

---

## 🔄 停止智能告警

如需临时禁用：

### 方法 1: 注释代码

编辑 `src/server.py`：

```python
# 注释掉这部分
# smart_manager = SmartAlertManager(...)
# smart_manager.start_monitoring()
```

### 方法 2: 环境变量控制

添加环境变量：

```bash
DISABLE_SMART_ALERTING=true
```

然后在 `server.py` 中添加条件判断：

```python
if not os.getenv("DISABLE_SMART_ALERTING"):
    smart_manager = SmartAlertManager(...)
    smart_manager.start_monitoring()
```

### 方法 3: 运行时停止

```python
smart_manager.stop_monitoring()
```

---

## 📚 相关文档

- [智能告警详细指南](../docs/smart-alerting-guide.md)
- [事件响应手册](../docs/event-response-runbook.md)
- [企业微信配置](../docs/wecom-alert-setup.md)
- [Phase 6 完成报告](../devs/phase6/phase6_completion_report.md)

---

## ✨ 总结

Phase 6 智能告警现已**完全集成**到 MCP Server 中：

- ✅ 自动启动，无需手动干预
- ✅ 与基础告警系统并存
- ✅ 完整的错误处理和容错机制
- ✅ 详细的日志输出
- ✅ 灵活的环境变量配置

**下一步**:
1. 启动服务器并观察日志
2. 等待 24 小时积累训练数据
3. 根据需要调整检测间隔
4. 配置通知渠道接收告警

---

**最后更新**: 2026-04-13  
**维护者**: AI Assistant  
**版本**: v1.0
