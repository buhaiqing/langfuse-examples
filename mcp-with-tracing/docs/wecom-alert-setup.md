# 企业微信告警配置指南

本文档说明如何配置企业微信机器人接收 MCP 告警通知。

## 企业微信机器人配置

### 1. 创建群机器人

1. 在企业微信群聊中，点击右上角菜单
2. 选择「添加群机器人」
3. 点击「新建」
4. 设置机器人名称（如：MCP 告警助手）
5. 可选：上传机器人头像
6. 点击「添加」

### 2. 获取 Webhook URL

添加成功后，你会看到一个 Webhook URL：

```
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY_HERE
```

**重要**: 保存此 URL，后续配置需要用到！

### 3. 在告警系统中配置

```python
from src.observability.alerting import (
    get_alert_manager,
    AlertSeverity,
    AlertRule,
    AlertChannel,
)
from src.observability.notifiers import WeComNotifier

# 获取告警管理器
manager = get_alert_manager()

# 配置成功率告警
manager.register_rule(AlertRule(
    name="success-rate-low",
    metric="success_rate",
    threshold=0.95,
    operator="lt",
    severity=AlertSeverity.WARNING,
    channels=[AlertChannel.WEBHOOK],
))

# 注册企业微信通知处理器
wecom_webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
manager.register_notification_handler(
    AlertChannel.WEBHOOK,
    WeComNotifier(wecom_webhook)
)
```

### 4. 测试告警

```python
from src.observability.alerting import check_success_rate

# 触发测试告警
alert = check_success_rate(0.80)

if alert:
    print(f"✓ 告警已触发，企业微信机器人已通知")
```

---

## 告警消息格式

企业微信机器人发送的告警消息格式如下：

```markdown
🚨 告警通知

告警名称：success-rate-low
严重级别: WARNING
监控指标：success_rate
当前值  : 0.80
阈值条件：< 0.95
时间窗口：60 分钟
触发时间：2026-04-08T10:30:00

详细信息：[告警详情消息]
```

---

## 示例：完整配置

```python
# config/alerting_config.py

from src.observability.alerting import (
    get_alert_manager,
    AlertSeverity,
    AlertRule,
    AlertChannel,
)
from src.observability.notifiers import WeComNotifier

def setup_wecom_alerts(wecom_webhook: str):
    """设置企业微信告警配置。"""
    
    manager = get_alert_manager()
    
    # 注册通知处理器
    manager.register_notification_handler(
        AlertChannel.WEBHOOK,
        WeComNotifier(wecom_webhook)
    )
    
    # 配置告警规则
    manager.register_rule(AlertRule(
        name="success-rate-low",
        metric="success_rate",
        threshold=0.95,
        operator="lt",
        severity=AlertSeverity.WARNING,
        window_minutes=60,
        channels=[AlertChannel.WEBHOOK],
    ))
    
    manager.register_rule(AlertRule(
        name="latency-high",
        metric="latency_p95_ms",
        threshold=500,
        operator="gt",
        severity=AlertSeverity.CRITICAL,
        window_minutes=30,
        channels=[AlertChannel.WEBHOOK],
    ))
    
    print("✓ 企业微信告警配置完成")
```

---

## 最佳实践

### 1. 敏感信息保护

**不要**将 webhook URL 硬编码到代码中：

```python
# ❌ 错误做法
wecom_webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abc123"

# ✅ 正确做法
import os
wecom_webhook = os.getenv("WECOM_WEBHOOK_URL")
```

### 2. 告警频率控制

为避免告警风暴，建议设置合理的告警间隔：

```python
AlertRule(
    name="success-rate-low",
    window_minutes=60,  # 60 分钟内只告警一次
    severity=AlertSeverity.WARNING,
)
```

### 3. 分级告警

根据严重程度选择不同的通知策略：

```python
# INFO - 仅记录，不通知
AlertRule(severity=AlertSeverity.INFO, channels=[])

# WARNING - 发送企业微信
AlertRule(severity=AlertSeverity.WARNING, channels=[AlertChannel.WEBHOOK])

# CRITICAL - 企微 + 邮件 + 电话
AlertRule(
    severity=AlertSeverity.CRITICAL,
    channels=[AlertChannel.WEBHOOK, AlertChannel.EMAIL]
)
```

---

## 常见问题

### Q: 机器人收不到消息？

**检查清单**:
1. 确认 webhook URL 正确
2. 确认机器人未被移除或禁用
3. 检查网络连接
4. 查看企业微信管理后台是否有错误日志

### Q: 消息格式错乱？

企业微信支持 markdown 格式，确保：
- 使用正确的 markdown 语法
- 中文字符使用 UTF-8 编码
- 特殊字符需要转义

### Q: 如何@特定成员？

在 payload 中添加 `mentioned_list`：

```python
payload = {
    "msgtype": "markdown",
    "markdown": {"content": "告警内容..."},
    "mentioned_list": ["user1", "user2"],  # 企业微信用户 ID
}
```

---

## 参考文档

- [企业微信群机器人文档](https://developer.work.weixin.qq.com/document/path/91770)
- [企业微信 Markdown 格式](https://developer.work.weixin.qq.com/document/path/90856)
- [MCP 告警配置指南](event-response-runbook.md)
