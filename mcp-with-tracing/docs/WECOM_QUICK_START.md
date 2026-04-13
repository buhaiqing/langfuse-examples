# 企业微信 Webhook URL 快速配置指南

## 📋 前置条件

- 已安装企业微信客户端
- 有权限在企业微信群聊中添加机器人

---

## 🔧 配置步骤（3 分钟完成）

### 步骤 1: 创建群机器人

1. 打开企业微信，进入需要接收告警的群聊
2. 点击右上角「⋮」菜单按钮
3. 选择「添加群机器人」
4. 点击「新建」按钮
5. 设置机器人信息：
   - **名称**: MCP 告警助手（或自定义）
   - **头像**: 可选上传
6. 点击「添加」

### 步骤 2: 获取 Webhook URL

添加成功后，系统会显示一个 Webhook URL，格式如下：

```
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**⚠️ 重要提示**:
- 此 URL 包含敏感密钥，请妥善保管
- 不要将完整 URL 提交到代码仓库
- 建议截图保存或复制到安全的地方

### 步骤 3: 配置到项目

#### 方法 A: 使用配置脚本（推荐）

```bash
# 1. 编辑 .env 文件，填入你的 Webhook URL
nano .env

# 在文件末尾添加：
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY_HERE

# 2. 运行配置脚本
python scripts/setup_wecom_alerts.py
```

脚本会自动：
- ✅ 验证 Webhook URL 格式
- ✅ 注册通知处理器
- ✅ 配置告警规则
- ✅ 发送测试告警

#### 方法 B: 手动配置

编辑 `.env` 文件：

```bash
# Langfuse Configuration
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com

# Notification Channels - WeCom (企业微信)
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY_HERE
```

然后在代码中使用：

```python
import os
from src.observability.alerting import get_alert_manager, AlertChannel
from src.observability.notifiers import WeComNotifier

# 获取 Webhook URL
wecom_url = os.getenv("WECOM_WEBHOOK_URL")

# 注册通知处理器
manager = get_alert_manager()
manager.register_notification_handler(
    AlertChannel.WEBHOOK,
    WeComNotifier(wecom_url)
)
```

---

## ✅ 验证配置

### 测试告警发送

```bash
python scripts/setup_wecom_alerts.py
```

如果配置正确，你会看到：

```
✓ 企业微信 Webhook URL 已配置
✓ 企业微信通知处理器已注册
✓ 成功率告警规则已配置 (阈值: < 95%)
✓ 延迟告警规则已配置 (阈值: > 500ms)
📤 发送测试告警...
✓ 测试告警已触发并发送

✅ 配置完成！企业微信告警已就绪
```

同时，企业微信群聊中会收到一条测试告警消息。

### 手动触发测试

```python
from src.observability.alerting import check_success_rate

# 触发成功率告警（80% < 95% 阈值）
alert = check_success_rate(0.80)

if alert:
    print("告警已发送到企业微信")
```

---

## 📨 告警消息示例

企业微信机器人发送的消息格式：

```markdown
🚨 告警通知

告警名称: success-rate-low
严重级别: WARNING
监控指标: success_rate
当前值: `0.80`
阈值条件: `< 0.95`
时间窗口: 60 分钟
触发时间: 2026-04-08T10:30:00+00:00

详细信息: Alert 'success-rate-low': success_rate = 0.80 (threshold: lt 0.95)
```

---

## ⚙️ 自定义配置

### 修改告警阈值

```python
from src.observability.alerting import get_alert_manager, AlertRule, AlertSeverity, AlertChannel

manager = get_alert_manager()

# 自定义成功率阈值（更严格）
manager.register_rule(AlertRule(
    name="success-rate-critical",
    metric="success_rate",
    threshold=0.99,  # 99% 成功率
    operator="lt",
    severity=AlertSeverity.CRITICAL,
    window_minutes=30,
    channels=[AlertChannel.WEBHOOK],
))
```

### 添加多个通知渠道

```python
from src.observability.notifiers import WeComNotifier, SlackNotifier

# 同时发送到企业微信和 Slack
manager.register_notification_handler(
    AlertChannel.WEBHOOK,
    WeComNotifier(os.getenv("WECOM_WEBHOOK_URL"))
)

manager.register_notification_handler(
    AlertChannel.SLACK,
    SlackNotifier(os.getenv("SLACK_WEBHOOK_URL"))
)
```

### @特定成员

编辑 `src/observability/notifiers.py` 中的 `WeComNotifier` 类：

```python
payload = {
    "msgtype": "markdown",
    "markdown": {"content": content},
    "mentioned_list": ["user1", "user2"],  # 企业微信用户 ID
}
```

---

## ❓ 常见问题

### Q1: 收不到告警消息？

**检查清单**:
1. ✅ Webhook URL 是否正确（无多余空格）
2. ✅ 机器人是否仍在群聊中
3. ✅ 网络连接是否正常
4. ✅ 告警规则是否已注册
5. ✅ 查看 Python 控制台是否有错误信息

**调试方法**:

```python
# 测试直接发送
from src.observability.notifiers import WeComNotifier
import os

notifier = WeComNotifier(os.getenv("WECOM_WEBHOOK_URL"))

# 创建测试告警
from src.observability.alerting import Alert, AlertRule, AlertSeverity
from datetime import datetime, timezone

test_alert = Alert(
    rule=AlertRule(
        name="test",
        metric="test_metric",
        threshold=1.0,
        operator="gt",
        severity=AlertSeverity.INFO,
    ),
    triggered_at=datetime.now(timezone.utc).isoformat(),
    value=1.5,
    message="测试消息",
)

notifier(test_alert)
print("测试消息已发送")
```

### Q2: 如何更换 Webhook URL？

1. 在企业微信中删除旧机器人
2. 重新添加新机器人，获取新 URL
3. 更新 `.env` 文件中的 `WECOM_WEBHOOK_URL`
4. 重启应用

### Q3: 可以配置多个群聊吗？

可以！创建多个机器人，分别配置：

```python
# .env
WECOM_WEBHOOK_DEV=https://qyapi.weixin.qq.com/...key=dev_key
WECOM_WEBHOOK_PROD=https://qyapi.weixin.qq.com/...key=prod_key

# 代码中
manager.register_notification_handler(
    "wecom_dev",
    WeComNotifier(os.getenv("WECOM_WEBHOOK_DEV"))
)
```

### Q4: 如何关闭告警？

```python
from src.observability.alerting import get_alert_manager

manager = get_alert_manager()

# 禁用特定规则
rule = manager.get_rule("success-rate-low")
if rule:
    rule.enabled = False

# 或删除规则
manager.unregister_rule("success-rate-low")
```

---

## 📚 相关文档

- [企业微信官方文档](https://developer.work.weixin.qq.com/document/path/91770)
- [MCP 告警配置指南](wecom-alert-setup.md)
- [事件响应手册](event-response-runbook.md)
- [告警测试脚本](../scripts/test_alerting.py)

---

## 🔒 安全提示

1. **不要**将 `.env` 文件提交到 Git
2. **不要**在代码中硬编码 Webhook URL
3. **定期**检查机器人权限
4. **限制** webhook URL 的访问范围

`.gitignore` 已包含 `.env`，确保它不会被意外提交。

---

**配置完成后，你就可以通过企业微信实时接收 MCP 服务的告警通知了！** 🎉
