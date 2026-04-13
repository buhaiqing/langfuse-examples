# 告警规则配置指南

> **版本**: 1.0.0  
> **最后更新**: 2026-04-13

---

## 📋 概述

本系统支持通过 **YAML 配置文件** 在应用启动时自动加载告警规则，无需手动调用 API。

### 优势对比

| 方式 | 优点 | 缺点 |
|------|------|------|
| **配置文件** (✅ 推荐) | • 声明式配置，易于管理<br>• 版本控制友好<br>• 重启后自动恢复<br>• 支持环境隔离 | • 需要重启生效 |
| **API 动态注册** | • 运行时动态调整<br>• 无需重启 | • 重启后丢失<br>• 难以追踪变更历史 |
| **脚本初始化** | • 批量配置方便 | • 仍需手动执行<br>• 不如配置文件直观 |

**最佳实践**: 使用配置文件定义基础规则 + API 动态调整为辅。

---

## 🚀 快速开始

### 1. 配置文件位置

```
mcp-with-tracing/
├── config/
│   └── alerts.yaml          # 告警规则配置文件
├── .env                      # 通知渠道配置（webhook URL 等）
└── src/
    └── server.py             # 启动时自动加载 alerts.yaml
```

### 2. 编辑配置文件

打开 `config/alerts.yaml`，根据需要修改或添加规则：

```yaml
alerts:
  - name: "success-rate-low"
    description: "成功率低于阈值"
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

### 3. 启动服务器

```bash
python -m src.server
```

启动时会看到：

```
============================================================
Loading alert rules...
============================================================
✓ Registered alert rule: success-rate-low-warning
✓ Registered alert rule: latency-p95-high-warning
✓ Registered alert rule: success-rate-critical

✅ Loaded 3 alert rule(s) from /path/to/config/alerts.yaml
============================================================
```

---

## 📖 配置语法详解

### 完整示例

```yaml
alerts:
  - name: "unique-rule-name"           # 必需：唯一规则名称
    description: "Rule description"    # 可选：规则描述
    metric: "success_rate"             # 必需：监控指标
    threshold: 0.95                    # 必需：阈值
    operator: "lt"                     # 必需：运算符
    severity: "warning"                # 必需：严重级别
    window_minutes: 60                 # 可选：时间窗口（默认 60）
    channels:                          # 可选：通知渠道
      - "wecom"
      - "slack"
    enabled: true                      # 可选：是否启用（默认 true）
    metadata:                          # 可选：额外元数据
      team: "backend"
      runbook_url: "https://..."
```

### 字段说明

#### 1. `name` (必需)
- **类型**: 字符串
- **要求**: 全局唯一，建议使用小写和连字符
- **示例**: `"success-rate-low"`, `"latency-p95-critical"`

#### 2. `metric` (必需)
- **类型**: 字符串
- **说明**: 要监控的指标名称
- **内置指标**:
  - `success_rate`: 成功率 (0.0 - 1.0)
  - `latency_p95_ms`: P95 延迟 (毫秒)
  - `latency_p99_ms`: P99 延迟 (毫秒)
  - `avg_rating`: 平均用户评分 (1-5)
  - `error_rate`: 错误率 (0.0 - 1.0)
- **自定义**: 可以定义任意指标，但需确保有对应的检查逻辑

#### 3. `threshold` (必需)
- **类型**: 数字
- **说明**: 触发告警的阈值
- **示例**: `0.95`, `500`, `1000`

#### 4. `operator` (必需)
- **类型**: 字符串
- **可选值**:
  - `gt`: 大于 (>)
  - `lt`: 小于 (<)
  - `gte`: 大于等于 (>=)
  - `lte`: 小于等于 (<=)
  - `eq`: 等于 (==)
- **示例**: 
  - 成功率告警: `operator: "lt"` (低于阈值)
  - 延迟告警: `operator: "gt"` (高于阈值)

#### 5. `severity` (必需)
- **类型**: 字符串
- **可选值**:
  - `info`: 信息级别（蓝色 ℹ️）
  - `warning`: 警告级别（黄色 ⚠️）
  - `critical`: 严重级别（红色 🚨）
- **建议**:
  - INFO: 常规监控、趋势变化
  - WARNING: 性能下降、需要关注
  - CRITICAL: 服务中断、立即处理

#### 6. `window_minutes` (可选)
- **类型**: 整数
- **默认值**: `60`
- **说明**: 计算指标的时间窗口（分钟）
- **示例**:
  - 短期波动: `15` 或 `30`
  - 长期趋势: `60` 或 `120`

#### 7. `channels` (可选)
- **类型**: 字符串数组
- **可选值**:
  - `wecom`: 企业微信
  - `slack`: Slack
  - `email`: 邮件
  - `pagerduty`: PagerDuty
  - `webhook`: 自定义 Webhook
- **示例**:
  ```yaml
  channels:
    - "wecom"
    - "slack"
    - "email"
  ```

#### 8. `enabled` (可选)
- **类型**: 布尔值
- **默认值**: `true`
- **用途**: 临时禁用规则而无需删除配置
- **示例**:
  ```yaml
  enabled: false  # 维护期间禁用
  ```

#### 9. `metadata` (可选)
- **类型**: 键值对对象
- **用途**: 附加上下文信息，便于告警处理和自动化
- **常见字段**:
  ```yaml
  metadata:
    team: "backend"                    # 负责团队
    escalation_policy: "on-call"       # 升级策略
    runbook_url: "https://..."         # 处理手册链接
    auto_rollback: true                # 是否自动回滚
    impact: "User experience"          # 影响范围
  ```

---

## 🎯 常见场景示例

### 场景 1: 多级成功率告警

```yaml
alerts:
  # 第一级：警告
  - name: "success-rate-warning"
    metric: "success_rate"
    threshold: 0.95
    operator: "lt"
    severity: "warning"
    window_minutes: 60
    channels:
      - "wecom"
      - "slack"
    metadata:
      action: "Monitor closely"

  # 第二级：严重
  - name: "success-rate-critical"
    metric: "success_rate"
    threshold: 0.90
    operator: "lt"
    severity: "critical"
    window_minutes: 30
    channels:
      - "wecom"
      - "pagerduty"
      - "email"
    metadata:
      action: "Immediate investigation required"
      auto_escalate_after_minutes: 15
```

### 场景 2: 延迟分级告警

```yaml
alerts:
  # P95 延迟警告
  - name: "latency-p95-warning"
    metric: "latency_p95_ms"
    threshold: 500
    operator: "gt"
    severity: "warning"
    window_minutes: 60
    channels:
      - "slack"
    metadata:
      impact: "Minor user experience degradation"

  # P95 延迟严重
  - name: "latency-p95-critical"
    metric: "latency_p95_ms"
    threshold: 1000
    operator: "gt"
    severity: "critical"
    window_minutes: 30
    channels:
      - "wecom"
      - "pagerduty"
    metadata:
      impact: "Severe user experience impact"

  # P99 尾延迟监控
  - name: "latency-p99-monitoring"
    metric: "latency_p99_ms"
    threshold: 2000
    operator: "gt"
    severity: "warning"
    window_minutes: 60
    channels:
      - "slack"
    enabled: false  # 默认禁用，按需启用
    metadata:
      purpose: "SLA compliance monitoring"
```

### 场景 3: 环境隔离配置

**开发环境** (`config/alerts-dev.yaml`):
```yaml
alerts:
  - name: "dev-success-rate"
    metric: "success_rate"
    threshold: 0.80  # 更宽松的阈值
    operator: "lt"
    severity: "info"
    channels:
      - "slack"
    metadata:
      environment: "development"
```

**生产环境** (`config/alerts-prod.yaml`):
```yaml
alerts:
  - name: "prod-success-rate"
    metric: "success_rate"
    threshold: 0.99  # 严格的阈值
    operator: "lt"
    severity: "critical"
    channels:
      - "wecom"
      - "pagerduty"
      - "email"
    metadata:
      environment: "production"
      escalation_policy: "immediate-page"
```

启动时指定配置文件：
```bash
# 开发环境
ALERT_CONFIG_PATH=config/alerts-dev.yaml python -m src.server

# 生产环境
ALERT_CONFIG_PATH=config/alerts-prod.yaml python -m src.server
```

### 场景 4: 临时禁用规则

```yaml
alerts:
  - name: "legacy-metric-alert"
    metric: "old_metric"
    threshold: 100
    operator: "gt"
    severity: "warning"
    enabled: false  # 临时禁用，保留配置
    metadata:
      reason: "Metric deprecated, keeping for reference"
      disabled_date: "2026-04-13"
```

---

## 🔧 高级用法

### 1. 环境变量覆盖

可以在 `.env` 中设置配置文件路径：

```bash
# .env
ALERT_CONFIG_PATH=config/alerts-custom.yaml
```

### 2. 多配置文件合并（未来扩展）

当前版本支持单个配置文件，未来可扩展为：

```yaml
# config/alerts-base.yaml (基础规则)
alerts:
  - name: "base-rule-1"
    ...

# config/alerts-env.yaml (环境特定规则)
alerts:
  - name: "env-specific-rule"
    ...
```

### 3. 动态重载（未来扩展）

提供 API 端点重新加载配置：

```python
POST /api/alerts/reload
{
  "config_path": "config/alerts-updated.yaml"
}
```

---

## 📊 配置验证

### 启动时验证

服务器启动时会自动验证配置文件：

```
✓ Registered alert rule: success-rate-low-warning
✓ Registered alert rule: latency-p95-high-warning
❌ Failed to register rule 'invalid-rule': Missing required field 'metric'

✅ Loaded 2 alert rule(s) from config/alerts.yaml
```

### 手动验证

使用 Python 脚本验证配置：

```python
from src.observability.alert_config_loader import AlertConfigLoader

loader = AlertConfigLoader("config/alerts.yaml")
try:
    count = loader.load_and_register()
    print(f"✅ Valid configuration: {count} rules loaded")
except Exception as e:
    print(f"❌ Invalid configuration: {e}")
```

---

## 🐛 故障排查

### 问题 1: 配置文件未找到

**错误**:
```
⚠️  Alert config file not found: /path/to/config/alerts.yaml
No alert rules will be loaded.
```

**解决**:
1. 确认文件存在: `ls config/alerts.yaml`
2. 检查路径是否正确
3. 使用绝对路径或从项目根目录启动

### 问题 2: YAML 语法错误

**错误**:
```
❌ Failed to parse alert config file: mapping values are not allowed here
```

**解决**:
1. 使用 YAML 验证器检查语法: `yamllint config/alerts.yaml`
2. 检查缩进（必须使用空格，不能用 Tab）
3. 确保冒号后有空格

### 问题 3: 无效的字段值

**错误**:
```
❌ Failed to register rule 'my-rule': Invalid severity 'high'. Must be one of: ['info', 'warning', 'critical']
```

**解决**:
1. 检查字段值是否在允许范围内
2. 参考本文档的"字段说明"部分
3. 注意大小写（全部小写）

### 问题 4: 通知渠道未配置

**现象**: 告警触发但未收到通知

**解决**:
1. 检查 `.env` 中是否配置了对应的 webhook URL
2. 运行测试脚本: `python scripts/setup_wecom_alerts.py`
3. 查看日志确认通知发送状态

---

## 📝 最佳实践

### 1. 命名规范

```yaml
# ✅ 推荐
name: "success-rate-low-warning"
name: "latency-p95-critical"

# ❌ 避免
name: "rule1"
name: "Success Rate Alert"  # 不要使用空格和大写
```

### 2. 分级告警

```yaml
# ✅ 推荐：多级告警
- name: "success-rate-warning"
  threshold: 0.95
  severity: "warning"
  
- name: "success-rate-critical"
  threshold: 0.90
  severity: "critical"

# ❌ 避免：单一阈值
- name: "success-rate-alert"
  threshold: 0.95
  severity: "critical"
```

### 3. 合理的窗口时间

```yaml
# ✅ 推荐：根据指标特性选择窗口
- name: "short-term-spike"
  window_minutes: 15  # 短期波动
  
- name: "long-term-trend"
  window_minutes: 120  # 长期趋势

# ❌ 避免：所有规则使用相同窗口
```

### 4. 元数据丰富化

```yaml
# ✅ 推荐：提供足够的上下文
metadata:
  team: "backend"
  runbook_url: "https://wiki/runbooks/success-rate"
  escalation_policy: "page-on-call"
  auto_rollback: true

# ❌ 避免：缺少元数据
metadata: {}
```

### 5. 版本控制

```bash
# ✅ 推荐：将配置文件纳入 Git
git add config/alerts.yaml
git commit -m "Add success rate alert rules"

# ❌ 避免：忽略配置文件
echo "config/alerts.yaml" >> .gitignore
```

---

## 📚 完整配置参考

### 所有支持的字段

```yaml
alerts:
  - name: "rule-name"                    # 必需：唯一标识符
    description: "Rule description"      # 可选：规则描述
    metric: "success_rate"               # 必需：监控指标名称
    threshold: 0.95                      # 必需：触发阈值（数字）
    operator: "lt"                       # 必需：比较运算符
    severity: "warning"                  # 必需：严重级别
    window_minutes: 60                   # 可选：时间窗口（分钟），默认 60
    channels:                            # 可选：通知渠道列表
      - "wecom"
      - "slack"
      - "email"
      - "pagerduty"
      - "webhook"
    enabled: true                        # 可选：是否启用，默认 true
    metadata:                            # 可选：额外元数据
      key: "value"
```

### 字段详细说明

#### 1. `name` (必需)
- **类型**: 字符串
- **要求**: 
  - 全局唯一
  - 只能包含字母、数字、连字符(-)和下划线(_)
  - 不能为空
- **示例**: 
  - ✅ `"success-rate-low"`
  - ✅ `"latency_p95_critical"`
  - ❌ `"Success Rate"` (包含空格)
  - ❌ `""` (空字符串)

#### 2. `metric` (必需)
- **类型**: 字符串
- **说明**: 要监控的指标名称
- **内置指标**:
  
  | 指标名称 | 说明 | 取值范围 | 单位 |
  |---------|------|---------|------|
  | `success_rate` | 成功率 | 0.0 - 1.0 | 比率 |
  | `latency_p95_ms` | P95 延迟 | 0+ | 毫秒 |
  | `latency_p99_ms` | P99 延迟 | 0+ | 毫秒 |
  | `avg_rating` | 平均用户评分 | 1.0 - 5.0 | 分数 |
  | `error_rate` | 错误率 | 0.0 - 1.0 | 比率 |

- **自定义指标**: 可以定义任意名称，但需要在代码中实现对应的采集逻辑

#### 3. `threshold` (必需)
- **类型**: 数字 (整数或浮点数)
- **说明**: 触发告警的阈值
- **示例**:
  - `0.95` (成功率)
  - `500` (延迟毫秒)
  - `3.5` (评分)

#### 4. `operator` (必需)
- **类型**: 字符串
- **可选值**:
  
  | 运算符 | 含义 | 使用场景 |
  |--------|------|----------|
  | `gt` | 大于 (>) | 延迟过高、错误率过高 |
  | `lt` | 小于 (<) | 成功率过低、评分过低 |
  | `gte` | 大于等于 (>=) | - |
  | `lte` | 小于等于 (<=) | - |
  | `eq` | 等于 (==) | 精确匹配 |

- **示例**:
  ```yaml
  # 成功率低于 95%
  operator: "lt"
  threshold: 0.95
  
  # 延迟高于 500ms
  operator: "gt"
  threshold: 500
  ```

#### 5. `severity` (必需)
- **类型**: 字符串
- **可选值**:
  
  | 级别 | 说明 | Emoji | 颜色 | 使用场景 |
  |------|------|-------|------|----------|
  | `info` | 信息 | ℹ️ | 蓝色 | 常规监控、趋势变化 |
  | `warning` | 警告 | ⚠️ | 黄色 | 性能下降、需要关注 |
  | `critical` | 严重 | 🚨 | 红色 | 服务中断、立即处理 |

#### 6. `window_minutes` (可选)
- **类型**: 整数
- **默认值**: `60`
- **要求**: 必须为正整数
- **说明**: 计算指标的时间窗口（分钟）
- **建议**:
  - 短期波动监测: `15` 或 `30`
  - 常规监控: `60`
  - 长期趋势: `120` 或更长

#### 7. `channels` (可选)
- **类型**: 字符串数组
- **可选值**:
  
  | 渠道 | 说明 | 配置要求 |
  |------|------|----------|
  | `wecom` | 企业微信 | 需配置 `WECOM_WEBHOOK_URL` |
  | `slack` | Slack | 需配置 `SLACK_WEBHOOK_URL` |
  | `email` | 邮件 | 需配置 SMTP 参数 |
  | `pagerduty` | PagerDuty | 需配置 `PAGERDUTY_ROUTING_KEY` |
  | `webhook` | 自定义 Webhook | 需配置 `CUSTOM_WEBHOOK_URL` |

- **示例**:
  ```yaml
  channels:
    - "wecom"
    - "slack"
  ```

#### 8. `enabled` (可选)
- **类型**: 布尔值
- **默认值**: `true`
- **说明**: 是否启用该规则
- **用途**: 临时禁用规则而无需删除配置

#### 9. `metadata` (可选)
- **类型**: 键值对对象
- **说明**: 附加上下文信息
- **常见字段**:
  ```yaml
  metadata:
    team: "backend"                    # 负责团队
    description: "Rule description"    # 规则描述
    runbook_url: "https://..."         # 处理手册链接
    escalation_policy: "on-call"       # 升级策略
    auto_rollback: true                # 是否自动回滚
    impact: "User experience"          # 影响范围
  ```

---

## 🔍 配置验证

### 方法 1: 使用验证脚本（推荐）

```bash
# 验证默认配置文件
python scripts/validate_alert_config.py

# 验证指定文件
python scripts/validate_alert_config.py config/alerts-prod.yaml
```

输出示例：
```
======================================================================
Alert Configuration Validation Report
======================================================================

📄 Configuration file: config/alerts.yaml
----------------------------------------------------------------------

📊 Summary:
   Total rules:     8
   Enabled rules:   6
   Disabled rules:  2

✅ No errors found

======================================================================
✅ VALIDATION PASSED
======================================================================
```

### 方法 2: 启动时自动验证

服务器启动时会自动验证配置文件，如果有错误会显示详细信息：

```bash
$ python -m src.server

❌ Failed to register rule 'invalid-rule': Invalid operator 'greater'. Must be one of: ['gt', 'lt', 'gte', 'lte', 'eq']
```

### 方法 3: Python API 验证

```python
from src.observability.alert_config_loader import validate_alert_config

result = validate_alert_config("config/alerts.yaml")

if result['valid']:
    print(f"✅ Valid: {result['enabled_rules']} rules ready")
else:
    print(f"❌ Errors: {result['errors']}")
```

### 验证内容

验证脚本会检查：

1. ✅ **文件存在性** - 配置文件是否存在
2. ✅ **YAML 语法** - YAML 格式是否正确
3. ✅ **必需字段** - 是否包含所有必需字段
4. ✅ **字段类型** - 字段类型是否正确
5. ✅ **字段值范围** - 枚举值是否在允许范围内
6. ✅ **规则名称唯一性** - 是否有重复的规则名称
7. ✅ **命名规范** - 规则名称是否符合规范

### 常见验证错误

#### 错误 1: 缺少必需字段
```
❌ Rule 'my-rule': Missing required field 'metric' in alert rule config
```
**解决**: 添加缺失的字段

#### 错误 2: 无效的运算符
```
❌ Rule 'my-rule': Invalid operator 'greater'. Must be one of: ['gt', 'lt', 'gte', 'lte', 'eq']
```
**解决**: 使用正确的运算符缩写

#### 错误 3: 无效的通知渠道
```
⚠️  Unknown channel 'wechat', skipping. Valid channels: ['wecom', 'slack', 'email', 'pagerduty', 'webhook']
```
**解决**: 使用正确的渠道名称（`wecom` 而非 `wechat`）

#### 错误 4: 重复的规则名称
```
❌ Rule 'success-rate-low': Duplicate rule name
```
**解决**: 确保每个规则有唯一的名称

#### 错误 5: 无效的阈值类型
```
❌ Rule 'my-rule': Threshold must be a number, got: high
```
**解决**: 阈值必须是数字

---

## 🔗 相关资源

- [告警系统架构](../devs/alert_implementation_analysis.md)
- [企业微信配置指南](./wecom-alert-setup.md)
- [事件响应手册](./event-response-runbook.md)
- [通知渠道配置](./notification-channels-setup.md)

---

## 📅 更新日志

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-04-13 | 初始版本，支持 YAML 配置文件加载 |
