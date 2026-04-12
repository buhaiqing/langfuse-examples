# Phase 5: 通知渠道配置快速开始

## 📖 概述

Phase 5 告警与通知系统已完成，支持 5 种通知渠道：
- ✅ 企业微信 (WeCom)
- ✅ Slack
- ✅ Email (SMTP)
- ✅ PagerDuty
- ✅ 通用 Webhook

## 🚀 快速开始

### 1. 选择通知渠道

根据团队需求选择一个或多个通知渠道。推荐配置：
- **国内团队**: 企业微信 + Email
- **国际团队**: Slack + Email + PagerDuty
- **混合团队**: 企业微信 + Slack + Email

### 2. 获取凭证

#### 企业微信
1. 在企业微信群聊中添加机器人
2. 复制 Webhook URL
3. 格式: `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx`

#### Slack
1. 访问 https://api.slack.com/apps
2. 创建 App 并启用 Incoming Webhooks
3. 复制 Webhook URL
4. 格式: `https://hooks.slack.com/services/xxx`

#### Email
准备 SMTP 服务器信息：
- Gmail: smtp.gmail.com:587 (需要应用专用密码)
- QQ 邮箱: smtp.qq.com:587 (需要授权码)
- 163 邮箱: smtp.163.com:587 (需要授权码)

#### PagerDuty
1. 登录 PagerDuty
2. 创建 Service 和 Integration
3. 复制 Routing Key

### 3. 配置环境变量

编辑 `.env` 文件：

```bash
# 复制模板
cp .env.example .env

# 编辑 .env 文件
vim .env  # 或使用你喜欢的编辑器
```

添加配置（示例）：

```env
# 企业微信
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Email
ALERT_EMAIL_SMTP_HOST=smtp.qq.com
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_SENDER=alerts@qq.com
ALERT_EMAIL_PASSWORD=your-auth-code
ALERT_EMAIL_RECIPIENTS=admin@example.com,ops@example.com

# PagerDuty
PAGERDUTY_ROUTING_KEY=your-pagerduty-routing-key
```

### 4. 测试配置

运行测试脚本验证配置：

```bash
python scripts/test_notification_channels.py
```

预期输出：

```
============================================================
Notification Channels Configuration Test
============================================================

Found 2 configured channel(s):
  ✓ WECOM
  ✓ EMAIL

============================================================
Testing WeCom Notification
============================================================
✓ WeCom notification sent successfully

============================================================
Testing Email Notification
============================================================
✓ Email notification sent successfully

============================================================
Test Summary
============================================================
WeCom                ✓ PASS
Email                ✓ PASS

Total: 2/2 tests passed

🎉 All notification channels are working correctly!
```

### 5. 集成到应用

在应用启动时初始化通知渠道：

```python
from examples.notification_channels_example import setup_notification_channels

# 一键配置所有通知渠道
if setup_notification_channels():
    print("✓ 通知渠道配置成功")
else:
    print("✗ 通知渠道配置失败，请检查 .env 文件")
```

### 6. 触发测试告警

```python
from src.observability.alerting import check_success_rate

# 触发测试告警（成功率低于 95%）
alert = check_success_rate(0.80)

if alert:
    print(f"✓ 告警已触发: {alert.message}")
    print("请检查你的通知渠道是否收到消息")
```

## 📚 详细文档

- **配置指南**: [docs/notification-channels-setup.md](../docs/notification-channels-setup.md)
- **事件响应**: [docs/event-response-runbook.md](../docs/event-response-runbook.md)
- **企业微信**: [docs/wecom-alert-setup.md](../docs/wecom-alert-setup.md)
- **完成报告**: [devs/phase5/phase5_completion_report.md](../devs/phase5/phase5_completion_report.md)

## 🔧 故障排查

### 问题：收不到通知

**检查清单**:
1. ✅ 确认 `.env` 文件中配置正确
2. ✅ 确认环境变量已加载 (`echo $WECOM_WEBHOOK_URL`)
3. ✅ 运行测试脚本 (`python scripts/test_notification_channels.py`)
4. ✅ 检查网络连接
5. ✅ 查看应用日志

### 问题：测试脚本报错

**常见错误**:
- `No notification channels configured`: 检查 `.env` 文件是否存在且配置正确
- `Connection refused`: 检查网络和防火墙设置
- `Authentication failed`: 检查凭证是否正确（特别是 Email 需要使用授权码）

## 🔒 安全提示

1. **不要提交 `.env` 文件到 Git**
   ```bash
   # 确认 .gitignore 包含 .env
   cat .gitignore | grep ".env"
   ```

2. **定期轮换凭证**
   - Webhook URLs: 每 6 个月
   - Email 密码: 每 3 个月
   - PagerDuty Keys: 每 6 个月

3. **使用强密码**
   - Email 使用应用专用密码或授权码
   - 不要使用登录密码

## 💡 最佳实践

### 1. 分级告警

```python
# WARNING: 发送到企业微信
configure_success_rate_alert(
    threshold=0.95,
    severity=AlertSeverity.WARNING,
    channels=[AlertChannel.WEBHOOK]
)

# CRITICAL: 发送到所有渠道
configure_latency_alert(
    threshold_ms=500,
    severity=AlertSeverity.CRITICAL,
    channels=[AlertChannel.WEBHOOK, AlertChannel.EMAIL, AlertChannel.PAGERDUTY]
)
```

### 2. 多渠道冗余

重要告警配置多个渠道，确保不遗漏：

```python
channels = [AlertChannel.WEBHOOK, AlertChannel.EMAIL]
configure_success_rate_alert(channels=channels)
```

### 3. 测试环境隔离

为不同环境使用不同的 webhook：

```env
# .env.development
WECOM_WEBHOOK_URL=https://qyapi...key=DEV_KEY

# .env.production
WECOM_WEBHOOK_URL=https://qyapi...key=PROD_KEY
```

## 📊 监控告警状态

查看告警历史：

```python
from src.observability.alerting import get_alert_manager

manager = get_alert_manager()

# 查看所有告警
all_alerts = manager.get_triggered_alerts()
print(f"总告警数: {len(all_alerts)}")

# 查看统计
stats = manager.get_alert_statistics()
print(f"告警统计: {stats}")
```

## 🎯 下一步

1. ✅ 配置通知渠道
2. ✅ 测试配置
3. ✅ 集成到应用
4. 📝 制定告警响应流程
5. 📊 监控告警效果
6. 🔄 持续优化阈值

## ❓ 需要帮助？

- 查看详细文档: [docs/notification-channels-setup.md](../docs/notification-channels-setup.md)
- 查看示例代码: [examples/notification_channels_example.py](../examples/notification_channels_example.py)
- 查看常见问题: [docs/notification-channels-setup.md#故障排查](../docs/notification-channels-setup.md#-故障排查)

---

**最后更新**: 2026-04-13  
**版本**: 1.0.0
