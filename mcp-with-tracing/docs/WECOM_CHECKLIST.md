# 企业微信告警配置 - 检查清单

## 📋 配置前准备

- [ ] 已安装企业微信客户端
- [ ] 有权限在企业微信群聊中添加机器人
- [ ] 项目代码已更新到最新版本

---

## 🔧 配置步骤检查清单

### 第 1 步：获取 Webhook URL

- [ ] 在企业微信群聊中点击右上角「⋮」菜单
- [ ] 选择「添加群机器人」
- [ ] 点击「新建」
- [ ] 设置机器人名称（建议：MCP 告警助手）
- [ ] 复制显示的 Webhook URL
- [ ] 保存 URL（格式应为：`https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx`）

**验证**: URL 应以 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=` 开头

---

### 第 2 步：配置环境变量

- [ ] 打开项目根目录的 `.env` 文件
- [ ] 找到 `WECOM_WEBHOOK_URL=` 这一行
- [ ] 在等号后粘贴你的 Webhook URL
- [ ] 保存文件

**示例**:
```bash
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**验证**:
```bash
# 运行以下命令检查配置
grep "WECOM_WEBHOOK_URL" .env
```

应该看到类似输出：
```
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx...
```

---

### 第 3 步：运行配置脚本

- [ ] 打开终端，进入项目根目录
- [ ] 激活虚拟环境（如果使用）
- [ ] 运行配置脚本：

```bash
python scripts/setup_wecom_alerts.py
```

**预期输出**:
```
============================================================
  MCP Langfuse Observability - 企业微信告警配置
============================================================

[1/4] 加载环境变量...
✓ Loaded environment from /path/to/.env

[2/4] 检查配置...
✓ 企业微信 Webhook URL 已配置
  URL: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...

[3/4] 配置告警规则...
✓ 企业微信通知处理器已注册
✓ 成功率告警规则已配置 (阈值: < 95%)
✓ 延迟告警规则已配置 (阈值: > 500ms)

[4/4] 测试通知...
📤 发送测试告警...
✓ 测试告警已触发并发送
  告警名称: success-rate-low
  严重级别: WARNING
  当前值: 0.8
  阈值: lt 0.95

✓ 请检查企业微信群聊是否收到告警消息

============================================================
✅ 配置完成！企业微信告警已就绪

下一步:
- 查看告警规则: python scripts/query_alert_rules.py
- 查看事件响应手册: docs/event-response-runbook.md
- 自定义告警规则: 参考 docs/wecom-alert-setup.md
============================================================
```

---

### 第 4 步：验证配置

#### 4.1 检查控制台输出

- [ ] 脚本运行无错误
- [ ] 显示 "✅ 配置完成！企业微信告警已就绪"

#### 4.2 检查企业微信

- [ ] 打开配置的企业微信群聊
- [ ] 看到来自机器人的测试告警消息
- [ ] 消息格式正确，包含所有字段

**测试告警消息应包含**:
- 🚨 或 ⚠️ 图标
- 告警名称
- 严重级别
- 监控指标
- 当前值
- 阈值条件
- 时间窗口
- 触发时间

#### 4.3 手动测试（可选）

```python
# 创建 test_wecom.py
from src.observability.alerting import check_success_rate

# 触发测试告警
alert = check_success_rate(0.80)

if alert:
    print("✓ 告警发送成功")
else:
    print("✗ 告警未触发")
```

运行：
```bash
python test_wecom.py
```

---

## ✅ 配置成功标志

全部满足以下条件即为配置成功：

- [x] `.env` 文件中 `WECOM_WEBHOOK_URL` 已配置
- [x] `setup_wecom_alerts.py` 脚本运行成功
- [x] 企业微信群聊收到测试告警消息
- [x] 告警消息格式正确，内容完整
- [x] 无错误信息或警告

---

## ❌ 常见问题排查

### 问题 1: 脚本提示 "未配置企业微信 Webhook URL"

**原因**: `.env` 文件中 `WECOM_WEBHOOK_URL` 为空

**解决**:
```bash
# 编辑 .env 文件
nano .env

# 添加或修改这一行
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
```

---

### 问题 2: 脚本提示 "Webhook URL 格式可能不正确"

**原因**: URL 格式错误或有多余空格

**解决**:
```bash
# 检查 URL 是否正确
grep "WECOM_WEBHOOK_URL" .env

# 确保没有多余空格
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
# 不是
WECOM_WEBHOOK_URL= https://qyapi.weixin.qq.com/...  # ❌ 有空格
```

---

### 问题 3: 脚本运行成功但收不到消息

**检查清单**:
- [ ] Webhook URL 是否正确
- [ ] 机器人是否仍在群聊中
- [ ] 网络连接是否正常
- [ ] 企业微信服务器是否正常

**调试方法**:
```python
# 直接测试 webhook
import urllib.request
import json

webhook_url = "YOUR_WEBHOOK_URL"
payload = {
    "msgtype": "text",
    "text": {"content": "测试消息"}
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    webhook_url, 
    data=data, 
    headers={"Content-Type": "application/json"}
)

try:
    response = urllib.request.urlopen(req, timeout=10)
    print("✓ 消息发送成功")
    print(response.read().decode())
except Exception as e:
    print(f"✗ 发送失败: {e}")
```

---

### 问题 4: 收到消息但格式错乱

**原因**: Markdown 语法问题

**解决**: 检查 `src/observability/notifiers.py` 中的消息格式

---

## 🔄 重新配置

如需更换 Webhook URL：

1. 在企业微信中删除旧机器人
2. 添加新机器人，获取新 URL
3. 更新 `.env` 文件
4. 重新运行配置脚本

```bash
python scripts/setup_wecom_alerts.py
```

---

## 📚 相关文档

- **快速开始**: [WECOM_QUICK_START.md](WECOM_QUICK_START.md)
- **详细说明**: [WECOM_SETUP_README.md](WECOM_SETUP_README.md)
- **高级配置**: [wecom-alert-setup.md](wecom-alert-setup.md)
- **事件响应**: [event-response-runbook.md](event-response-runbook.md)
- **配置总结**: [WECOM_CONFIG_COMPLETE.md](WECOM_CONFIG_COMPLETE.md)

---

## 🎯 配置完成后

配置成功后，系统将自动监控：

1. **成功率**: 低于 95% 时发送 WARNING 告警
2. **延迟**: P95 超过 500ms 时发送 CRITICAL 告警

你可以在代码中自定义这些阈值和规则。

---

**祝你配置顺利！** 🚀

如有问题，请查看详细文档或联系技术支持。
