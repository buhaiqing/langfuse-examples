# 企业微信告警配置 - 使用说明

## 🚀 快速开始（3 步完成）

### 第 1 步：获取企业微信 Webhook URL

1. 在企业微信群聊中点击右上角「⋮」菜单
2. 选择「添加群机器人」→「新建」
3. 设置机器人名称（如：MCP 告警助手）
4. 复制显示的 Webhook URL

```
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 第 2 步：配置环境变量

编辑项目根目录的 `.env` 文件，在末尾添加：

```bash
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY_HERE
```

**注意**: 将 `YOUR_KEY_HERE` 替换为你的实际 key。

### 第 3 步：运行配置脚本

```bash
python scripts/setup_wecom_alerts.py
```

脚本会自动：
- ✅ 验证 Webhook URL 格式
- ✅ 注册通知处理器
- ✅ 配置告警规则（成功率 < 95%，延迟 > 500ms）
- ✅ 发送测试告警到企业微信

如果看到以下输出，说明配置成功：

```
✅ 配置完成！企业微信告警已就绪
```

同时，你的企业微信群聊会收到一条测试告警消息。

---

## 📝 详细文档

- **快速配置指南**: [docs/WECOM_QUICK_START.md](WECOM_QUICK_START.md)
- **详细配置说明**: [docs/wecom-alert-setup.md](wecom-alert-setup.md)
- **事件响应手册**: [docs/event-response-runbook.md](event-response-runbook.md)

---

## 🔍 验证配置

### 方法 1: 运行配置脚本

```bash
python scripts/setup_wecom_alerts.py
```

### 方法 2: 手动触发测试告警

```python
from src.observability.alerting import check_success_rate

# 触发成功率告警（80% < 95% 阈值）
alert = check_success_rate(0.80)

if alert:
    print("✓ 告警已发送到企业微信")
```

### 方法 3: 检查告警状态

```python
from src.observability.alerting import get_alert_manager

manager = get_alert_manager()

# 查看已配置的规则
print("告警规则:", manager.list_rules())

# 查看触发的告警
alerts = manager.get_triggered_alerts()
print(f"已触发 {len(alerts)} 条告警")
```

---

## ⚙️ 自定义配置

### 修改告警阈值

编辑代码中的告警规则：

```python
from src.observability.alerting import AlertRule, AlertSeverity, AlertChannel

# 更严格的成功率告警（99%）
AlertRule(
    name="success-rate-critical",
    metric="success_rate",
    threshold=0.99,
    operator="lt",
    severity=AlertSeverity.CRITICAL,
    window_minutes=30,
    channels=[AlertChannel.WEBHOOK],
)
```

### 添加其他通知渠道

支持 Slack、Email、PagerDuty 等：

```python
from src.observability.notifiers import SlackNotifier, EmailNotifier

# Slack
manager.register_notification_handler(
    AlertChannel.SLACK,
    SlackNotifier(os.getenv("SLACK_WEBHOOK_URL"))
)

# Email
manager.register_notification_handler(
    AlertChannel.EMAIL,
    EmailNotifier(
        smtp_host="smtp.example.com",
        smtp_port=587,
        sender="alerts@example.com",
        recipients=["admin@example.com"]
    )
)
```

---

## ❓ 常见问题

### Q: 收不到告警消息？

**检查清单**:
1. Webhook URL 是否正确（无多余空格）
2. 机器人是否仍在群聊中
3. 网络连接是否正常
4. 查看 Python 控制台是否有错误信息

**调试方法**: 参考 [WECOM_QUICK_START.md](WECOM_QUICK_START.md) 中的调试章节。

### Q: 如何更换 Webhook URL？

1. 更新 `.env` 文件中的 `WECOM_WEBHOOK_URL`
2. 重启应用

### Q: 可以配置多个群聊吗？

可以！创建多个机器人，分别配置不同的 webhook URL。

### Q: 如何关闭告警？

```python
from src.observability.alerting import get_alert_manager

manager = get_alert_manager()
manager.unregister_rule("success-rate-low")
```

---

## 🔒 安全提示

1. ✅ **不要**将 `.env` 文件提交到 Git（已在 `.gitignore` 中）
2. ✅ **不要**在代码中硬编码 Webhook URL
3. ✅ **定期**检查机器人权限
4. ✅ **限制** webhook URL 的访问范围

---

## 📞 需要帮助？

- 查看详细文档: [docs/WECOM_QUICK_START.md](WECOM_QUICK_START.md)
- 企业微信官方文档: https://developer.work.weixin.qq.com/document/path/91770
- 查看示例代码: `scripts/test_alerting.py`

---

**配置完成后，你就可以通过企业微信实时接收 MCP 服务的告警通知了！** 🎉
