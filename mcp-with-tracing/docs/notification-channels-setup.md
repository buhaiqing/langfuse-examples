# 通知渠道配置指南 (Notification Channels Setup Guide)

本文档说明如何配置各种通知渠道以接收告警通知。

## 📋 目录

1. [企业微信 (WeCom)](#企业微信-wecom)
2. [Slack](#slack)
3. [Email (SMTP)](#email-smtp)
4. [PagerDuty](#pagerduty)
5. [Webhook (通用)](#webhook-通用)
6. [测试配置](#测试配置)

---

## 企业微信 (WeCom)

### 1. 创建群机器人

1. 在企业微信群聊中，点击右上角菜单
2. 选择「添加群机器人」
3. 点击「新建」
4. 设置机器人名称（如：MCP 告警助手）
5. 点击「添加」

### 2. 获取 Webhook URL

添加成功后，复制 Webhook URL：
```
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY_HERE
```

### 3. 配置环境变量

在 `.env` 文件中添加：
```env
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY_HERE
```

### 4. 代码中使用

```python
from src.observability.notifiers import WeComNotifier
from src.observability.alerting import get_alert_manager, AlertChannel
import os

# 从环境变量读取
wecom_url = os.getenv("WECOM_WEBHOOK_URL")
if wecom_url:
    manager = get_alert_manager()
    manager.register_notification_handler(
        AlertChannel.WEBHOOK,
        WeComNotifier(wecom_url)
    )
```

---

## Slack

### 1. 创建 Incoming Webhook

1. 访问 https://api.slack.com/apps
2. 点击「Create New App」→ 「From scratch」
3. 设置 App 名称和工作区
4. 在左侧菜单选择「Incoming Webhooks」
5. 激活 Incoming Webhooks
6. 点击「Add New Webhook to Workspace」
7. 选择要发送消息的频道
8. 复制 Webhook URL

### 2. 配置环境变量

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 3. 代码中使用

```python
from src.observability.notifiers import SlackNotifier
from src.observability.alerting import get_alert_manager, AlertChannel
import os

slack_url = os.getenv("SLACK_WEBHOOK_URL")
if slack_url:
    manager = get_alert_manager()
    manager.register_notification_handler(
        AlertChannel.SLACK,
        SlackNotifier(slack_url)
    )
```

---

## Email (SMTP)

### 1. 准备 SMTP 服务器信息

常用邮箱 SMTP 配置：

**Gmail:**
- Host: smtp.gmail.com
- Port: 587 (TLS) 或 465 (SSL)
- 需要开启「允许不够安全的应用」或使用应用专用密码

**QQ 邮箱:**
- Host: smtp.qq.com
- Port: 587 (TLS) 或 465 (SSL)
- 需要使用授权码（不是登录密码）

**163 邮箱:**
- Host: smtp.163.com
- Port: 587 (TLS) 或 465 (SSL)
- 需要使用授权码

**公司邮箱:**
- 联系 IT 部门获取 SMTP 服务器信息

### 2. 配置环境变量

```env
ALERT_EMAIL_SMTP_HOST=smtp.example.com
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_SENDER=alerts@example.com
ALERT_EMAIL_PASSWORD=your-email-password-or-app-password
ALERT_EMAIL_RECIPIENTS=admin@example.com,ops@example.com
```

### 3. 代码中使用

```python
from src.observability.notifiers import EmailNotifier
from src.observability.alerting import get_alert_manager, AlertChannel
import os

smtp_host = os.getenv("ALERT_EMAIL_SMTP_HOST")
smtp_port = int(os.getenv("ALERT_EMAIL_SMTP_PORT", "587"))
sender = os.getenv("ALERT_EMAIL_SENDER")
recipients = os.getenv("ALERT_EMAIL_RECIPIENTS", "").split(",")

if all([smtp_host, sender, recipients]):
    manager = get_alert_manager()
    manager.register_notification_handler(
        AlertChannel.EMAIL,
        EmailNotifier(smtp_host, smtp_port, sender, recipients)
    )
```

---

## PagerDuty

### 1. 创建 Service 和 Integration

1. 登录 PagerDuty (https://www.pagerduty.com)
2. 进入「Services」→「Service Directory」
3. 点击「+ New Service」
4. 填写服务信息
5. 在「Integrations」标签页，点击「+ Add Integration」
6. 选择「Events API v2」
7. 复制 Integration Key (Routing Key)

### 2. 配置环境变量

```env
PAGERDUTY_ROUTING_KEY=your-pagerduty-routing-key-here
```

### 3. 代码中使用

```python
from src.observability.notifiers import PagerDutyNotifier
from src.observability.alerting import get_alert_manager, AlertChannel
import os

routing_key = os.getenv("PAGERDUTY_ROUTING_KEY")
if routing_key:
    manager = get_alert_manager()
    manager.register_notification_handler(
        AlertChannel.PAGERDUTY,
        PagerDutyNotifier(routing_key)
    )
```

---

## Webhook (通用)

### 1. 准备 Webhook URL

任何支持 POST 请求的 HTTP 端点都可以作为 webhook 接收器。

常见用途：
- 自定义告警处理系统
- Discord/Teams 通知
- 内部监控平台
- Zapier/IFTTT 自动化

### 2. 配置环境变量

```env
CUSTOM_WEBHOOK_URL=https://your-webhook-endpoint.com/alerts
CUSTOM_WEBHOOK_AUTH_TOKEN=optional-auth-token
```

### 3. 代码中使用

```python
from src.observability.notifiers import WebhookNotifier
from src.observability.alerting import get_alert_manager, AlertChannel
import os

webhook_url = os.getenv("CUSTOM_WEBHOOK_URL")
if webhook_url:
    headers = {}
    auth_token = os.getenv("CUSTOM_WEBHOOK_AUTH_TOKEN")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    manager = get_alert_manager()
    manager.register_notification_handler(
        AlertChannel.WEBHOOK,
        WebhookNotifier(webhook_url, headers=headers)
    )
```

---

## 测试配置

### 方法 1: 使用测试脚本

运行提供的测试脚本验证配置：

```bash
# 测试所有已配置的通知渠道
python scripts/test_notification_channels.py
```

### 方法 2: 手动测试

```python
from src.observability.alerting import (
    get_alert_manager,
    AlertRule,
    AlertSeverity,
    AlertChannel,
)
from src.observability.notifiers import WeComNotifier, SlackNotifier
import os

# 初始化告警管理器
manager = get_alert_manager()

# 注册通知渠道（根据实际配置）
if os.getenv("WECOM_WEBHOOK_URL"):
    manager.register_notification_handler(
        AlertChannel.WEBHOOK,
        WeComNotifier(os.getenv("WECOM_WEBHOOK_URL"))
    )

# 创建测试规则
manager.register_rule(AlertRule(
    name="test-notification",
    metric="test_metric",
    threshold=100,
    operator="gt",
    severity=AlertSeverity.INFO,
    channels=[AlertChannel.WEBHOOK],  # 根据需要修改
))

# 触发测试告警
alert = manager.check_rule("test-notification", 150)
if alert:
    print("✓ 告警已触发，请检查通知渠道")
else:
    print("✗ 告警未触发")
```

---

## 🔒 安全最佳实践

### 1. 不要硬编码凭证

❌ **错误做法**:
```python
webhook_url = "https://hooks.slack.com/services/xxx"
```

✅ **正确做法**:
```python
import os
webhook_url = os.getenv("SLACK_WEBHOOK_URL")
```

### 2. 保护 .env 文件

确保 `.env` 文件已添加到 `.gitignore`:
```bash
# .gitignore
.env
.env.local
*.env
```

### 3. 使用不同的环境配置

为不同环境使用不同的配置文件：
```
.env.development    # 开发环境
.env.staging        # 测试环境
.env.production     # 生产环境
```

### 4. 定期轮换密钥

- 定期更新 webhook URLs
- 定期更换 email 密码
- 定期轮换 PagerDuty keys

---

## 🐛 故障排查

### 问题 1: 收不到通知

**检查清单**:
1. 确认 webhook URL 正确
2. 检查网络连接
3. 查看应用日志中的错误信息
4. 验证通知渠道已正确注册
5. 检查告警规则是否触发

**调试命令**:
```bash
# 测试 webhook 连通性
curl -X POST https://your-webhook-url \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

### 问题 2: Email 发送失败

**常见原因**:
1. SMTP 服务器地址或端口错误
2. 用户名或密码错误
3. 防火墙阻止 SMTP 连接
4. 邮箱服务商限制（需要授权码）

**解决方案**:
```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 问题 3: Slack 消息格式错误

**检查**:
1. 确认使用正确的 Block Kit 格式
2. 验证 JSON 结构
3. 检查特殊字符转义

---

## 📊 监控通知状态

### 查看告警历史

```python
from src.observability.alerting import get_alert_manager

manager = get_alert_manager()

# 查看所有触发的告警
all_alerts = manager.get_triggered_alerts()
print(f"总告警数: {len(all_alerts)}")

# 查看特定规则的告警
rule_alerts = manager.get_triggered_alerts(rule_name="success-rate-low")
print(f"成功率告警数: {len(rule_alerts)}")

# 查看统计信息
stats = manager.get_alert_statistics()
print(f"告警统计: {stats}")
```

---

## 📚 相关文档

- [事件响应手册](event-response-runbook.md)
- [企业微信配置指南](wecom-alert-setup.md)
- [告警系统完成报告](../devs/phase5/phase5_completion_report.md)

---

**最后更新**: 2026-04-13  
**维护者**: Platform Team
