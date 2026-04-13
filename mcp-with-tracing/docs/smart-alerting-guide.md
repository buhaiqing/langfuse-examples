# 智能告警系统使用指南

> **基于机器学习的异常检测**  
> 使用 Prophet 和 PyOD 实现智能化的监控告警

---

## 📋 目录

1. [系统概述](#系统概述)
2. [架构设计](#架构设计)
3. [快速开始](#快速开始)
4. [配置指南](#配置指南)
5. [使用示例](#使用示例)
6. [故障排查](#故障排查)
7. [性能优化](#性能优化)

---

## 系统概述

### 什么是智能告警?

智能告警系统（Phase 6）是在传统阈值告警（Phase 5）基础上的**增强层**，使用机器学习算法自动检测异常模式，无需手动设置固定阈值。

**核心优势**:
- 🤖 **自动学习**: 从历史数据中学习正常模式
- 📊 **多维分析**: 同时监控多个指标的关联异常
- ⚡ **实时检测**: 近实时监控(5-10分钟窗口)
- 🎯 **减少误报**: 基于统计显著性判断异常

### 与传统告警的关系

项目中有**两套并行的告警系统**：

| 特性 | 传统告警 (Phase 5) | 智能告警 (Phase 6) |
|------|-------------------|-------------------|
| **检测方式** | 固定阈值规则 | ML 模型自动学习 |
| **配置方式** | 手动设置阈值 | 自动训练，无需配置 |
| **适用场景** | 明确的业务规则 | 未知异常模式发现 |
| **检测指标** | 可自定义任意指标 | 成功率、延迟、流量、满意度 |
| **误报率** | 较高（需人工调优） | 较低（自适应调整） |
| **启动方式** | AlertMonitorScheduler | SmartAlertManager |
| **检测间隔** | 默认 5 分钟 | 默认 10 分钟 |
| **依赖** | 无额外依赖 | prophet, pyod, pandas, numpy, sklearn |

**两者关系**:
- ✅ **互补而非替代**: 传统告警处理已知规则，智能告警发现未知异常
- ✅ **并行运行**: 两个系统独立运行，互不干扰
- ✅ **共享通知渠道**: 都使用相同的 AlertChannel 和 Notifier
- ✅ **统一告警存储**: 所有告警都存储在 AlertManager._alerts 中

**推荐配置**:
```python
# 传统告警: 明确的业务规则
# 例如: 成功率 < 95% 立即告警
manager.add_rule(AlertRule(
    name="critical_success_rate",
    metric="success_rate",
    threshold=0.95,
    operator="lt",
    severity=AlertSeverity.CRITICAL
))

# 智能告警: 自动发现异常模式
# 例如: 检测到成功率突然下降 20%，即使仍高于 95%
smart_manager.start_monitoring()  # 自动运行
```

### 支持的指标

| 指标 | 说明 | 检测方法 |
|------|------|----------|
| 成功率 (Success Rate) | API/工具调用成功率 | Prophet + Isolation Forest |
| P95 延迟 (Latency) | 响应时间的 95 分位数 | Prophet + Isolation Forest |
| 请求率 (Request Rate) | 每秒请求数 (QPS) | Prophet + Isolation Forest |
| 用户满意度 (Satisfaction) | 平均用户评分 | Isolation Forest |

---

## 架构设计

### 组件图

```
┌─────────────────────────────────────────────┐
│         SmartAlertManager                    │
│  (智能告警管理器 - 后台监控线程)              │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌─────▼──────────┐
│ Metrics     │  │ Anomaly        │
│ Collector   │  │ Detector       │
│ (指标收集器) │  │ (异常检测引擎)  │
└──────┬──────┘  └─────┬──────────┘
       │                │
       │         ┌──────┴──────────┐
       │         │                 │
       │    ┌────▼─────┐   ┌──────▼──────┐
       │    │ Time     │   │ Multivariate│
       │    │ Series   │   │ Detector    │
       │    │Detector  │   │ (PyOD)      │
       │    │(Prophet) │   │             │
       │    └──────────┘   └─────────────┘
       │
┌──────▼──────────────────────┐
│   Langfuse API              │
│   (Traces & Scores)         │
└─────────────────────────────┘
```

### 工作流程

1. **数据收集**: MetricsCollector 从 Langfuse API 获取历史数据
2. **模型训练**: 
   - Prophet 为每个指标训练时间序列模型
   - PyOD 训练多维异常检测模型
3. **异常检测**: 
   - 单变量检测: 检查每个指标是否偏离预测范围
   - 多变量检测: 检查指标组合是否异常
4. **告警触发**: 检测到异常时创建 Alert 并发送通知

---

## 快速开始

### 1. 安装依赖

```bash
# macOS (需要 C++ 编译器)
brew install libomp

# 安装 Python 依赖
pip install prophet pyod pandas numpy scikit-learn

# 或使用项目依赖
cd mcp-with-tracing
pip install -e .
```

### 2. 基本用法

**注意**: 智能告警已集成到服务器启动流程中，无需手动启动！

服务器启动时会自动初始化智能告警：

```bash
python -m src.server
```

你会看到以下日志：
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

#### 手动测试（可选）

如果需要在代码中手动测试：

```python
from src.observability.smart_alerting import SmartAlertManager

# 创建智能告警管理器
manager = SmartAlertManager(detection_interval_minutes=10)

# 启动监控(后台线程)
manager.start_monitoring()

# 保持运行
import time
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    manager.stop_monitoring()
```

### 3. 运行演示脚本

```bash
python scripts/test_smart_alerting.py
```

---

## 配置指南

### 调整检测间隔

```python
# 更频繁的检测(5分钟)
manager = SmartAlertManager(detection_interval_minutes=5)

# 较宽松的检测(30分钟)
manager = SmartAlertManager(detection_interval_minutes=30)
```

**建议**:
- 生产环境: 10-15 分钟
- 开发测试: 5 分钟
- 低流量系统: 30 分钟

### 配置通知渠道

```python
from src.observability.alerting import AlertChannel
from src.observability.notifiers import WeComNotifier, SlackNotifier

# 注册企业微信通知
wecom_notifier = WeComNotifier(
    webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
)
manager.register_notification_handler(AlertChannel.WEBHOOK, wecom_notifier)

# 注册 Slack 通知
slack_notifier = SlackNotifier(
    webhook_url="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
)
manager.register_notification_handler(AlertChannel.SLACK, slack_notifier)
```

### 调整模型参数

#### Prophet 参数

```python
from src.observability.anomaly_detector import TimeSeriesAnomalyDetector

detector = TimeSeriesAnomalyDetector(
    uncertainty_samples=200  # 增加采样数提高精度(默认100)
)
```

**关键参数**:
- `uncertainty_samples`: 不确定性采样数 (默认100)
  - 更高 = 更准确但更慢
  - 推荐: 100-500

#### PyOD 参数

```python
from src.observability.anomaly_detector import MultivariateAnomalyDetector

# Isolation Forest
detector = MultivariateAnomalyDetector(
    method='iforest',
    contamination=0.05  # 预期异常比例(默认0.05)
)

# Local Outlier Factor
detector = MultivariateAnomalyDetector(
    method='lof',
    contamination=0.05
)
```

**关键参数**:
- `contamination`: 预期异常比例 (默认0.05 = 5%)
  - 调高 = 更敏感(更多告警)
  - 调低 = 更保守(更少告警)
  - 推荐: 0.01-0.10

- `method`: 检测方法
  - `'iforest'`: 快速,适合高维数据
  - `'lof'`: 更准确,但较慢

### 历史数据时长

```python
# 使用 48 小时历史数据训练(默认24小时)
manager.anomaly_detector.train_all_models(hours_of_history=48)
```

**建议**:
- 稳定系统: 24 小时
- 有周期性模式: 7天 (168小时)
- 新系统: 至少需要 50 个数据点

---

## 使用示例

### 示例 1: 手动执行检测

```python
from src.observability.smart_alerting import SmartAlertManager

manager = SmartAlertManager()

# 执行单次检测
manager._run_detection_cycle()

# 查看结果
stats = manager.get_ml_alert_statistics()
print(f"检测到 {stats['total_ml_alerts']} 个异常")

# 查看详细告警
for alert in manager._alerts:
    print(f"\n{alert.rule.name}:")
    print(f"  严重程度: {alert.rule.severity.value}")
    print(f"  消息: {alert.message}")
```

### 示例 2: 持续监控

```python
import time
from src.observability.smart_alerting import SmartAlertManager

manager = SmartAlertManager(detection_interval_minutes=10)

# 注册通知
from src.observability.notifiers import WeComNotifier
manager.register_notification_handler(
    AlertChannel.WEBHOOK,
    WeComNotifier("YOUR_WEBHOOK_URL")
)

# 启动监控
print("启动智能监控...")
manager.start_monitoring()

# 定期检查统计
try:
    while True:
        time.sleep(300)  # 每5分钟检查一次
        
        stats = manager.get_ml_alert_statistics()
        if stats['total_ml_alerts'] > 0:
            print(f"⚠️  检测到 {stats['total_ml_alerts']} 个异常!")
            
except KeyboardInterrupt:
    print("\n停止监控")
    manager.stop_monitoring()
```

### 示例 3: 与现有告警系统集成

```python
from src.observability.alerting import (
    get_alert_manager,
    configure_success_rate_alert,
    AlertSeverity
)
from src.observability.smart_alerting import SmartAlertManager

# 配置传统阈值告警
configure_success_rate_alert(
    threshold=0.95,
    severity=AlertSeverity.WARNING
)

# 同时启用智能告警
smart_manager = SmartAlertManager()
smart_manager.start_monitoring()

# 两种方式互补:
# - 传统告警: 明确的业务阈值
# - 智能告警: 发现未知异常模式
```

### 示例 4: 查询告警统计

```python
from src.observability.smart_alerting import SmartAlertManager

manager = SmartAlertManager()
manager._run_detection_cycle()

# ML 告警统计
ml_stats = manager.get_ml_alert_statistics()
print("ML 告警统计:")
print(f"  总数: {ml_stats['total_ml_alerts']}")
print(f"  按类型: {ml_stats['by_type']}")
print(f"  按指标: {ml_stats['by_metric']}")

# 总体告警统计(包含传统告警)
overall_stats = manager.get_alert_statistics()
print("\n总体告警统计:")
print(f"  总数: {overall_stats['total_alerts']}")
print(f"  按严重程度: {overall_stats['by_severity']}")
```

---

## 故障排查

### 问题 1: Prophet 安装失败

**症状**:
```
ERROR: Could not build wheels for prophet
```

**解决方案**:
```bash
# macOS
brew install libomp
pip install prophet

# Linux (Ubuntu/Debian)
sudo apt-get install build-essential
pip install prophet

# 使用 conda (推荐)
conda install -c conda-forge prophet
```

### 问题 2: 数据不足无法训练

**症状**:
```
Warning: Insufficient data for success_rate (30 points, need at least 50)
```

**解决方案**:
1. 等待更多数据积累
2. 降低检测间隔以增加数据点密度
3. 使用更短的历史窗口:
   ```python
   # 使用 12 小时而非 24 小时
   manager.anomaly_detector.train_all_models(hours_of_history=12)
   ```

### 问题 3: 误报过多

**症状**: 频繁收到告警,但实际系统正常

**解决方案**:
1. 调整 PyOD contamination 参数:
   ```python
   # 降低敏感度(从 0.05 到 0.02)
   from src.observability.anomaly_detector import MultivariateAnomalyDetector
   detector = MultivariateAnomalyDetector(contamination=0.02)
   ```

2. 增加 Prophet 置信区间:
   ```python
   # 在 anomaly_detector.py 中修改
   model = Prophet(interval_width=0.99)  # 从 0.95 改为 0.99
   ```

3. 增加检测间隔:
   ```python
   manager = SmartAlertManager(detection_interval_minutes=30)
   ```

### 问题 4: Langfuse API 调用失败

**症状**:
```
Failed to fetch traces: Connection error
```

**解决方案**:
1. 检查环境变量配置:
   ```bash
   echo $LANGFUSE_PUBLIC_KEY
   echo $LANGFUSE_SECRET_KEY
   ```

2. 验证网络连接:
   ```python
   from src.observability.langfuse_client import get_langfuse_client
   client = get_langfuse_client()
   print(client.client.ping())
   ```

3. 检查 API 速率限制:
   - Langfuse 可能有 API 调用频率限制
   - 考虑增加检测间隔

### 问题 5: 监控线程无法停止

**症状**: 调用 `stop_monitoring()` 后线程仍在运行

**解决方案**:
```python
# 强制停止(不推荐,仅用于紧急情况)
import threading
for thread in threading.enumerate():
    if thread.name == "SmartAlertMonitor":
        print(f"Found monitoring thread: {thread}")
        # 线程是 daemon,会在主进程退出时自动停止
```

**正确做法**: 等待线程自然停止(最多30秒)
```python
manager.stop_monitoring()  # 会自动等待
```

---

## 性能优化

### 1. 减少 API 调用频率

```python
# 增加检测间隔
manager = SmartAlertManager(detection_interval_minutes=30)

# 或在 MetricsCollector 中实现缓存
class CachedMetricsCollector(MetricsCollector):
    def __init__(self, *args, cache_ttl_seconds=300, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_ttl = cache_ttl_seconds
        self._cache = {}
        self._cache_time = {}
```

### 2. 并行模型训练

```python
# 当前实现是串行的,可以改为并行
from concurrent.futures import ThreadPoolExecutor

def train_all_models_parallel(self, hours_of_history=24):
    metrics = ['success_rate', 'latency_p95', 'request_rate']
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for metric in metrics:
            historical_data = self.metrics_collector.get_historical_data(
                metric, hours=hours_of_history
            )
            if len(historical_data) >= 50:
                future = executor.submit(
                    self.ts_detector.train, metric, historical_data
                )
                futures.append(future)
        
        for future in futures:
            future.result()  # Wait for completion
```

### 3. 增量模型更新

Prophet 支持增量训练,避免每次都从头训练:

```python
# 保留旧模型,仅用新数据更新
# 这需要修改 TimeSeriesAnomalyDetector.train() 方法
```

### 4. 数据采样

对于高流量系统,可以对数据进行采样:

```python
# 在 MetricsCollector 中实现采样
def get_historical_data(self, metric_name, hours=24, sample_rate=0.1):
    df = self._fetch_raw_data(metric_name, hours)
    if sample_rate < 1.0:
        df = df.sample(frac=sample_rate)
    return df
```

### 5. 资源监控

监控智能告警系统本身的资源使用:

```python
import psutil
import os

def check_resource_usage():
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    cpu_percent = process.cpu_percent()
    
    print(f"内存使用: {memory_mb:.2f} MB")
    print(f"CPU 使用: {cpu_percent:.2f}%")
    
    # 如果资源使用过高,可以考虑:
    # 1. 减少模型数量
    # 2. 降低 uncertainty_samples
    # 3. 增加检测间隔
```

---

## 最佳实践

### ✅ 推荐做法

1. **渐进式部署**: 先在测试环境运行,观察误报率
2. **结合传统告警**: ML 告警作为补充,而非替代
3. **定期审查**: 每周检查告警历史,调整参数
4. **文档化**: 记录每次参数调整的原因和效果
5. **监控监控**: 确保智能告警系统本身正常运行

### ❌ 避免的做法

1. **不要设置过短的检测间隔**: < 5分钟会导致过多 API 调用
2. **不要忽略误报**: 及时调整参数减少噪音
3. **不要在生产环境直接调整参数**: 先在测试环境验证
4. **不要依赖单一检测方法**: 结合单变量和多变量检测

---

## 相关文档

- [Phase 5: 告警与通知完成报告](../devs/phase5/phase5_completion_report.md)
- [事件响应手册](event-response-runbook.md)
- [企业微信配置指南](wecom-alert-setup.md)
- [后端开发规范](backend-standards.md)

---

## 后续优化方向

1. **自适应阈值**: 根据历史告警反馈自动调整灵敏度
2. **根因分析**: 自动分析异常的可能原因
3. **告警关联**: 识别多个相关异常的关联性
4. **预测性告警**: 提前预测未来可能出现的异常
5. **可视化仪表板**: Web UI 展示异常检测结果和趋势

---

**最后更新**: 2026-04-13  
**版本**: 1.0.0
