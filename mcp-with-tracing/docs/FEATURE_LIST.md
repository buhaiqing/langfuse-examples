# MCP Langfuse 可观测性平台 - 功能清单

> **版本**: v1.0  
> **更新日期**: 2026-04-13  
> **项目状态**: ✅ 生产就绪 (95% 完成)

---

## 📋 目录

1. [核心功能概览](#核心功能概览)
2. [详细功能列表](#详细功能列表)
3. [技术架构](#技术架构)
4. [API 接口](#api-接口)
5. [配置项](#配置项)
6. [测试覆盖](#测试覆盖)
7. [文档资源](#文档资源)

---

## 🎯 核心功能概览

| 功能模块 | 状态 | 说明 |
|---------|------|------|
| 🔍 追踪插桩 | ✅ 完成 | 自动追踪所有 MCP 工具调用 |
| 👥 会话管理 | ✅ 完成 | 端到端用户会话追踪 |
| 📝 提示词版本 | ✅ 完成 | A/B 测试和版本对比 |
| 💬 反馈收集 | ✅ 完成 | 用户满意度信号采集 |
| 🚨 告警通知 | ✅ 完成 | 多通道实时告警 |
| 📊 数据查询 | ✅ 完成 | 脚本化数据检索 |

---

## 📦 详细功能列表

### 1. 追踪插桩 (Tracing & Instrumentation)

#### 1.1 基础追踪
- ✅ **自动工具追踪**: `@observe_tool` 装饰器自动捕获工具执行
- ✅ **请求/响应日志**: 记录输入参数、输出结果、执行时间
- ✅ **错误捕获**: 自动捕获异常并记录堆栈信息
- ✅ **性能监控**: 追踪每个工具的延迟和吞吐量
- ✅ **Token 使用统计**: 记录 LLM 调用的 token 消耗

**相关文件**:
- `src/observability/decorators.py` - 装饰器实现
- `src/observability/langfuse_client.py` - Langfuse 客户端封装
- `tests/test_instrumentation.py` - 单元测试

#### 1.2 成功/失败追踪
- ✅ **成功率计算**: 自动统计工具调用成功率
- ✅ **失败分类**: 区分不同类型的错误（超时、异常、验证失败等）
- ✅ **错误详情**: 记录完整的错误信息和上下文

**示例**:
```python
@observe_tool(name="my_tool")
def my_function(arg1, arg2):
    # 自动追踪成功/失败
    return result
```

---

### 2. 会话追踪 (Session Tracing)

#### 2.1 会话管理
- ✅ **会话 ID 生成**: 自动生成或手动设置 session_id
- ✅ **用户标识**: 绑定 user_id 到会话
- ✅ **会话传播**: 跨多个工具调用保持会话上下文
- ✅ **会话隔离**: 支持多租户场景的会话隔离

#### 2.2 会话视图
- ✅ **会话重放**: 在 Langfuse 中查看完整会话流程
- ✅ **用户旅程**: 追踪用户通过多个工具的交互路径
- ✅ **会话聚合**: 按会话维度统计分析

**相关文件**:
- `src/observability/session.py` - 会话管理器
- `docs/session-view-guide.md` - 使用指南
- `tests/test_session.py` - 单元测试

**示例**:
```python
from src.observability import set_session

set_session(
    session_id="user-123-session",
    user_id="user-123"
)
```

---

### 3. 提示词版本管理 (Prompt Versioning)

#### 3.1 版本追踪
- ✅ **版本元数据**: 为每次调用附加 prompt 版本信息
- ✅ **版本比较**: 对比不同版本的性能和成功率
- ✅ **A/B 测试**: 支持同时运行多个 prompt 版本

#### 3.2 版本分析
- ✅ **版本查询脚本**: `query_prompt_versions.py` 查询历史版本
- ✅ **效果仪表板**: 文档指导创建版本对比仪表板
- ✅ **版本演进**: 追踪 prompt 的历史变更

**相关文件**:
- `src/observability/prompt_versioning.py` - 版本管理器
- `scripts/query_prompt_versions.py` - 查询脚本
- `docs/prompt-effectiveness-dashboard.md` - 仪表板指南

**示例**:
```python
from src.observability import track_prompt_version

@track_prompt_version(prompt_id="greeting", version="v2.1")
def greet_user(name):
    return f"Hello, {name}!"
```

---

### 4. 反馈收集 (Feedback Collection)

#### 4.1 反馈类型
- ✅ **接受/拒绝**: 记录用户对结果的 accept/reject
- ✅ **评分系统**: 支持 1-5 星评分
- ✅ **评论反馈**: 可选的文字评论
- ✅ **自定义标签**: 支持添加自定义反馈标签

#### 4.2 反馈处理
- ✅ **反馈聚合**: 按工具、会话、用户维度聚合反馈
- ✅ **满意度计算**: 自动计算用户满意度指标
- ✅ **MCP 反馈工具**: 提供标准的 feedback MCP 工具

**相关文件**:
- `src/observability/feedback.py` - 反馈收集器
- `src/tools/feedback_tool.py` - MCP 反馈工具
- `scripts/query_feedback.py` - 查询脚本
- `docs/satisfaction-dashboard-guide.md` - 仪表板指南

**示例**:
```python
from src.observability.feedback import record_acceptance, record_rejection

# 用户接受
record_acceptance(trace_id="trace-123", comment="Great response!")

# 用户拒绝
record_rejection(trace_id="trace-123", reason="Incorrect answer")
```

---

### 5. 告警与通知 (Alerting & Notification)

#### 5.1 告警规则
- ✅ **成功率告警**: 当成功率低于阈值时触发
- ✅ **延迟告警**: 当 P95/P99 延迟超过阈值时触发
- ✅ **自定义规则**: 支持自定义监控指标和阈值
- ✅ **多级严重性**: INFO / WARNING / CRITICAL

#### 5.2 通知渠道
- ✅ **企业微信**: WeCom 机器人 webhook 通知
- ✅ **Slack**: Slack webhook 集成（代码已完成）
- ✅ **Email**: SMTP 邮件通知（代码已完成）
- ✅ **PagerDuty**: PagerDuty 事件集成（代码已完成）
- ✅ **通用 Webhook**: 支持任意 webhook 端点

#### 5.3 告警管理
- ✅ **告警管理器**: AlertManager 统一管理告警规则
- ✅ **告警历史**: 记录和查询已触发的告警
- ✅ **告警统计**: 按严重性、规则维度统计
- ✅ **事件响应手册**: 完整的告警处理流程文档

**相关文件**:
- `src/observability/alerting.py` - 告警管理器
- `src/observability/notifiers.py` - 通知渠道实现
- `scripts/setup_wecom_alerts.py` - 企业微信配置脚本
- `scripts/test_alerting.py` - 告警测试
- `docs/WECOM_QUICK_START.md` - 企业微信快速配置
- `docs/event-response-runbook.md` - 事件响应手册

**示例**:
```python
from src.observability.alerting import configure_success_rate_alert, AlertChannel

# 配置成功率告警
configure_success_rate_alert(
    threshold=0.95,  # 低于 95% 触发
    channels=[AlertChannel.WEBHOOK]
)
```

---

### 6. 配置管理 (Configuration)

#### 6.1 环境变量
- ✅ **Langfuse 配置**: PUBLIC_KEY, SECRET_KEY, HOST
- ✅ **应用配置**: APP_ENV, LOG_LEVEL
- ✅ **通知配置**: WECOM_WEBHOOK_URL, SLACK_WEBHOOK_URL 等

#### 6.2 配置类
- ✅ **ObservabilityConfig**: Pydantic 配置类
- ✅ **类型安全**: 完整的类型注解和验证
- ✅ **默认值**: 合理的默认配置

**相关文件**:
- `src/observability/config.py` - 配置管理
- `.env.example` - 配置模板
- `.env` - 实际配置（需用户填写）

---

### 7. MCP 工具示例

#### 7.1 内置工具
- ✅ **echo**: 回显工具（示例）
- ✅ **calculate**: 数学计算工具（示例）
- ✅ **submit_feedback_accept**: 接受反馈工具
- ✅ **submit_feedback_reject**: 拒绝反馈工具
- ✅ **submit_feedback_rating**: 评分反馈工具
- ✅ **submit_feedback_comment**: 评论反馈工具

#### 7.2 工具特性
- ✅ **自动追踪**: 所有工具自动启用追踪
- ✅ **错误处理**: 完善的异常捕获
- ✅ **参数验证**: Pydantic 模型验证

**相关文件**:
- `src/server.py` - MCP 服务器和工具定义
- `src/tools/feedback_tool.py` - 反馈工具

---

### 8. 数据查询与分析

#### 8.1 查询脚本
- ✅ **提示词版本查询**: `query_prompt_versions.py`
- ✅ **反馈数据查询**: `query_feedback.py`
- ✅ **连接测试**: `test_langfuse_connection.py`

#### 8.2 数据分析
- ✅ **成功率统计**: 按工具、时间段统计
- ✅ **延迟分析**: P50/P95/P99 延迟分布
- ✅ **反馈聚合**: 满意度趋势分析

---

## 🏗️ 技术架构

### 核心组件

```
MCP Client
    ↓
FastMCP Server (src/server.py)
    ↓
Instrumentation Layer (src/observability/)
    ├── decorators.py - 追踪装饰器
    ├── session.py - 会话管理
    ├── prompt_versioning.py - 版本管理
    ├── feedback.py - 反馈收集
    ├── alerting.py - 告警管理
    └── notifiers.py - 通知渠道
    ↓
Langfuse SDK
    ↓
Langfuse Cloud
```

### 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| **语言** | Python | 3.10+ |
| **框架** | FastMCP | 2.12.0 |
| **可观测性** | Langfuse | 2.0+ |
| **配置** | python-dotenv | 1.0+ |
| **验证** | Pydantic | 2.0+ |
| **测试** | pytest | 7.4+ |
| **代码质量** | black, ruff, isort | 最新 |

---

## 🔌 API 接口

### 装饰器 API

```python
# 工具追踪
@observe_tool(name="tool_name", as_type="span")

# 会话追踪
@track_session(session_id="xxx", user_id="xxx")

# 提示词版本
@track_prompt_version(prompt_id="xxx", version="v1.0")
```

### 函数 API

```python
# 初始化
init_observability(config: ObservabilityConfig)

# 会话管理
set_session(session_id: str, user_id: str)
clear_session()

# 反馈收集
record_acceptance(trace_id: str, comment: str = None)
record_rejection(trace_id: str, reason: str = None)
record_score(trace_id: str, score: float, comment: str = None)

# 告警配置
configure_success_rate_alert(threshold: float, channels: list)
configure_latency_alert(threshold_ms: float, channels: list)
```

---

## ⚙️ 配置项

### 必需配置

```bash
# Langfuse API Keys
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 可选配置

```bash
# 应用设置
APP_ENV=development
LOG_LEVEL=INFO

# 通知渠道
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

---

## 🧪 测试覆盖

### 单元测试 (56 tests)

| 测试文件 | 测试数 | 覆盖率 |
|---------|--------|--------|
| test_instrumentation.py | 11 | ✅ |
| test_session.py | 11 | ✅ |
| test_prompt_versioning.py | 14 | ✅ |
| test_feedback.py | 16 | ✅ |
| test_alerting.py | 4 | ✅ |
| **总计** | **56** | **70%+** |

### 集成测试 (14 tests)

| 测试脚本 | 测试数 | 状态 |
|---------|--------|------|
| test_langfuse_connection.py | 1 | ✅ |
| test_session_tracing.py | 4 | ✅ |
| test_prompt_versioning.py | 5 | ✅ |
| test_alerting.py | 4 | ✅ |
| **总计** | **14** | **✅ 全部通过** |

---

## 📚 文档资源

### 用户文档
- [快速入门](manuals/快速入门.md) - 5 分钟上手
- [用户手册](manuals/用户手册.md) - 完整使用指南
- [API 参考](manuals/API\ 参考.md) - API 文档

### 开发文档
- [后端标准](docs/backend-standards.md) - 后端开发规范
- [前端标准](docs/frontend-standards.md) - 前端开发规范（预留）
- [测试指南](docs/testing-guide.md) - 测试最佳实践
- [安全指南](docs/security-guide.md) - 安全规范
- [代码审查](docs/code-review-guide.md) - 代码审查指南

### 功能文档
- [会话追踪指南](docs/session-view-guide.md)
- [提示词效果仪表板](docs/prompt-effectiveness-dashboard.md)
- [满意度仪表板](docs/satisfaction-dashboard-guide.md)
- [企业微信配置](docs/WECOM_QUICK_START.md)
- [事件响应手册](docs/event-response-runbook.md)

### 集成文档
- [集成模式](docs/integration-patterns.md)
- [监控指南](docs/monitoring-guide.md)
- [企业微信告警](docs/wecom-alert-setup.md)

---

## 📊 功能完成度

| 功能模块 | 完成度 | 说明 |
|---------|--------|------|
| 追踪插桩 | ✅ 100% | 全部完成 |
| 会话管理 | ✅ 100% | 全部完成 |
| 版本管理 | ✅ 100% | 全部完成 |
| 反馈收集 | ✅ 100% | 全部完成 |
| 告警系统 | ✅ 100% | 代码完成 |
| 通知渠道 | ✅ 80% | 代码完成，需配置凭证 |
| 文档 | ✅ 100% | 全部完成 |
| 测试 | ✅ 100% | 70 个测试全部通过 |

**总体完成度**: **95%**

---

## 🚀 部署状态

### 生产就绪检查

- ✅ 代码开发完成
- ✅ 单元测试覆盖充足
- ✅ 集成测试全部通过
- ✅ 文档完整齐全
- ✅ 代码质量达标 (black, ruff)
- ⏳ Langfuse API keys 配置（用户需提供）
- ⏳ 企业微信 Webhook URL 配置（用户需提供）

### 已知限制

1. **无前端界面**: 依赖 Langfuse Cloud UI 查看数据
2. **通知凭证**: 需要用户自行配置第三方服务凭证
3. **自定义告警**: 需要根据实际需求调整阈值

---

## 📈 性能指标

### 目标指标

| 指标 | 目标值 | 当前状态 |
|------|--------|----------|
| 工具调用成功率 | > 99.5% | 待生产验证 |
| P95 延迟 | < 500ms | 待生产验证 |
| 用户接受率 | > 85% | 待生产验证 |
| 追踪完整性 | 100% | ✅ 已实现 |
| 插桩开销 | < 5% | ✅ 已优化 |

---

## 🔮 未来规划

### 短期 (Phase 6+)
- [ ] 自定义 Web Dashboard
- [ ] 更多 MCP 工具示例
- [ ] 高级告警规则（动态阈值）
- [ ] 数据导出功能

### 中期
- [ ] 多 Langfuse 实例支持
- [ ] 自定义插件系统
- [ ] 性能优化建议引擎
- [ ] 成本分析功能

### 长期
- [ ] AI 驱动的异常检测
- [ ] 自动化根因分析
- [ ] 预测性告警
- [ ] 多租户 SaaS 化

---

## 📞 支持与联系

- **问题反馈**: 提交 GitHub Issue
- **文档**: 查看 `docs/` 目录
- **示例代码**: 参考 `scripts/` 和 `tests/` 目录

---

**最后更新**: 2026-04-13  
**维护者**: MCP Langfuse Observability Team
