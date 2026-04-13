# 用户文档中心

> MCP Langfuse 可观测平台官方用户手册

---

## 📚 文档目录

### 🚀 入门指南

| 文档 | 用途 | 阅读时间 |
|------|------|----------|
| [快速入门](快速入门.md) | 5 分钟开始使用 | 5 分钟 |
| [用户手册](用户手册.md) | 完整使用指南 | 30 分钟 |

### 📖 API 文档

| 文档 | 用途 |
|------|------|
| [API 参考](API 参考.md) | API 接口完整参考 |

### 🔧 配置指南

| 文档 | 用途 |
|------|------|
| [Langfuse 配置](../docs/session-view-guide.md) | Langfuse 账号配置 |
| [企业微信配置](../docs/wecom-alert-setup.md) | 企业微信机器人配置 |

### 📊 分析指南

| 文档 | 用途 |
|------|------|
| [会话分析](../docs/session-view-guide.md) | 用户行为分析 |
| [版本对比](../docs/prompt-effectiveness-dashboard.md) | Prompt A/B 测试 |
| [反馈分析](../docs/satisfaction-dashboard-guide.md) | 用户满意度分析 |

### 🚨 运维指南

| 文档 | 用途 |
|------|------|
| [告警配置](../docs/wecom-alert-setup.md) | 配置告警通知 |
| [事件响应](../docs/event-response-runbook.md) | 告警处理流程 |

---

## 🎯 快速导航

### 我是新手，从哪里开始？

1. 阅读 [快速入门](快速入门.md)
2. 配置 Langfuse API Keys
3. 运行测试验证

### 我想配置告警通知

1. 阅读 [企业微信配置指南](../docs/wecom-alert-setup.md)
2. 获取企业微信 Webhook URL
3. 配置到代码中

### 我想分析用户行为

1. 使用 `set_session()` 开始会话追踪
2. 访问 Langfuse 控制台查看 Sessions
3. 阅读 [会话分析指南](../docs/session-view-guide.md)

### 我想做 A/B 测试

1. 使用 `register_prompt_version()` 注册版本
2. 使用 `set_active_prompt_version()` 切换版本
3. 阅读 [版本对比指南](../docs/prompt-effectiveness-dashboard.md)

### 收到告警怎么办？

查看 [事件响应手册](../docs/event-response-runbook.md)

---

## 📞 获取帮助

### 遇到问题？

1. 检查 [常见问题](用户手册.md#常见问题)
2. 运行测试脚本验证配置
3. 查看日志输出

### 技术支持

- **项目文档**: `/docs/` 目录
- **开发文档**: `/devs/` 目录
- **Jira**: 提交 DOPS 工单

---

## 📝 文档更新记录

| 日期 | 更新内容 |
|------|----------|
| 2026-04-08 | 初始版本，包含完整用户手册 |

---


