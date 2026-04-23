# Agent Skill CLI with Tracing - 技术规格文档

> 创建日期：2026-04-23
> 版本：1.0.0
> 状态：技术评审

## 1. 项目概述

### 1.1 目标

创建一个基于 Langfuse 的 **Agent Skill + CLI 可观测性** 示例项目，参考 `mcp-with-tracing` 的架构模式，但使用 **Typer CLI** 替代 FastMCP 框架。

### 1.2 与 mcp-with-tracing 的关系

| 维度 | mcp-with-tracing | agent-skill-cli-with-tracing |
|------|------------------|------------------------------|
| 框架 | FastMCP | Typer |
| 入口 | MCP Server | CLI 命令行 |
| 工具定义 | @mcp.tool() | @app.command() |
| 追踪模式 | Tool 调用追踪 | Skill 执行追踪 |
| 会话管理 | SessionManager | CLI SessionContext |
| 复杂度 | Phase 1-6 完整 | Phase 1-4 + 简化 Phase 5 |

### 1.3 技术栈

- **Python**: 3.10+
- **CLI 框架**: Typer (基于 Click，类型驱动)
- **观测性**: Langfuse SDK 4.x
- **LLM 提供商**: OpenAI（示例）
- **包管理**: uv / pip
- **测试**: pytest

---

## 2. 架构设计

### 2.1 高层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Layer (Typer)                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Commands                                            │   │
│  │  - skill list                                        │   │
│  │  - skill run <name> [args]                         │   │
│  │  - skill discover                                   │   │
│  │  - feedback submit                                  │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Skill Execution Layer                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SkillRegistry                                      │   │
│  │  - 动态加载 skills/ 目录下的 Skill                  │   │
│  │  - SKILL.md 元数据解析                              │   │
│  │  - 版本管理                                          │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SkillLoader / SkillExecutor                       │   │
│  │  - 加载 Skill 实现                                  │   │
│  │  - 执行 Skill 逻辑                                  │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Observability Layer (Langfuse SDK)                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  @observe_skill 装饰器                               │   │
│  │  - 自动追踪 Skill 执行                               │   │
│  │  - session_id/user_id 传播                          │   │
│  │  - 输入/输出记录                                     │   │
│  │  - 错误捕获与状态更新                                │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Session Management                                 │   │
│  │  - CLI SessionContext                               │   │
│  │  - propagate_attributes                             │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Feedback Collection                                │   │
│  │  - accept/reject/rating/comment                     │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Alerting (简化版)                                   │   │
│  │  - 成功率 <90% 告警                                 │   │
│  │  - 延迟 >1s 告警                                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
1. 用户执行 CLI 命令
   ↓
2. Typer 解析命令和参数
   ↓
3. SkillRegistry 发现/加载 Skill
   ↓
4. @observe_skill 创建 Langfuse Trace
   ↓
5. 执行 Skill 逻辑（可能包含 LLM 调用）
   ↓
6. 记录输入/输出到 Trace
   ↓
7. 返回结果给用户
   ↓
8. (可选) 用户提交反馈 → 更新 Trace Score
```

### 2.3 组件职责

| 组件 | 职责 | 文件位置 |
|------|------|---------|
| `main.py` | Typer CLI 入口，命令注册 | `src/cli/main.py` |
| `skill.py` | skill 命令实现 | `src/cli/commands/skill.py` |
| `feedback.py` | feedback 命令实现 | `src/cli/commands/feedback.py` |
| `registry.py` | Skill 注册表管理 | `src/skills/registry.py` |
| `loader.py` | Skill 动态加载 | `src/skills/loader.py` |
| `base.py` | Skill 基类定义 | `src/skills/base.py` |
| `decorators.py` | @observe_skill 装饰器 | `src/observability/decorators.py` |
| `session.py` | 会话管理 | `src/observability/session.py` |
| `feedback.py` | 反馈收集 | `src/observability/feedback.py` |
| `alerting.py` | 告警管理 | `src/observability/alerting.py` |

---

## 3. 核心 Skill 定义

### 3.1 Skill 目录结构

```
skills/
└── <skill_name>/
    ├── SKILL.md           # Skill 元数据 (YAML Frontmatter)
    ├── skill.py           # Skill 实现
    └── requirements.txt   # Skill 依赖 (可选)
```

### 3.2 SKILL.md 格式

```yaml
---
name: hello_tracing
description: 基础追踪演示 Skill
version: 1.0.0
author: Platform Team
tags: [demo, tracing, basics]
dependencies: []
---

# Hello Tracing Skill

这是一个用于演示 Langfuse 基础追踪功能的 Skill。

## 使用方法

```bash
skill run hello_tracing --name "World"
```

## 输入参数

- `name`: 问候名称 (默认: "World")

## 输出

格式化的问候语
```

### 3.3 5 个核心 Skill 规格

#### Skill 1: hello_tracing

| 属性 | 值 |
|------|-----|
| 名称 | `hello_tracing` |
| 描述 | 基础追踪演示 |
| 演示重点 | @observe_skill 装饰器、trace 生成、成功/失败状态 |
| 复杂度 | ★☆☆☆☆ |

**实现要点**：
- 简单的字符串处理
- 自动创建 trace 并记录输入输出
- 演示基本的 span 生命周期

---

#### Skill 2: web_fetch

| 属性 | 值 |
|------|-----|
| 名称 | `web_fetch` |
| 描述 | HTTP 请求追踪 |
| 演示重点 | 外部 API 调用追踪、延迟监控、错误处理 |
| 复杂度 | ★★☆☆☆ |

**实现要点**：
- 使用 `requests` 库发送 HTTP 请求
- 记录请求 URL、method、response status
- 监控响应时间
- 错误捕获和 trace 更新

---

#### Skill 3: file_analyzer

| 属性 | 值 |
|------|-----|
| 名称 | `file_analyzer` |
| 描述 | 文件 I/O + 会话演示 |
| 演示重点 | 文件操作追踪、session_id 传播、大文件处理 |
| 复杂度 | ★★☆☆☆ |

**实现要点**：
- 读取指定文件并分析内容
- 记录文件路径、大小、行数
- 演示 session_id 在 CLI 调用间的传播
- 使用 contextvars 保持会话上下文

---

#### Skill 4: llm_summarizer

| 属性 | 值 |
|------|-----|
| 名称 | `llm_summarizer` |
| 描述 | LLM 调用 + 版本管理 |
| 演示重点 | OpenAI 调用追踪、Skill 版本管理、A/B 测试元数据 |
| 复杂度 | ★★★☆☆ |

**实现要点**：
- 调用 OpenAI API 进行文本摘要
- 记录 model、tokens、temperature 等参数
- 演示 Skill 版本管理（v1/v2）
- 支持不同版本使用不同 prompt 进行 A/B 测试

---

#### Skill 5: pipeline_demo

| 属性 | 值 |
|------|-----|
| 名称 | `pipeline_demo` |
| 描述 | 多步骤 pipeline + 反馈 |
| 演示重点 | 多步骤追踪、子 span 层级、用户反馈收集 |
| 复杂度 | ★★★★☆ |

**实现要点**：
- 多步骤处理流程（fetch → process → transform → save）
- 每个步骤创建子 span
- 演示 span 嵌套结构
- 支持 accept/reject/rating 反馈收集
- 计算端到端延迟和成功率

---

## 4. 复用分析

### 4.1 从 mcp-with-tracing 可直接复用的文件

以下文件可 **直接复用**（或微调后使用）：

| 原项目文件 | 复用方式 | 调整说明 |
|-----------|---------|---------|
| `src/observability/config.py` | ✅ 直接复制 | 字段无需调整 |
| `src/observability/instrumentation.py` | ✅ 直接复制 | 字段无需调整 |
| `src/observability/langfuse_client.py` | ✅ 直接复制 | 可简化为单例 |
| `src/observability/feedback.py` | ✅ 直接复制 | 字段无需调整 |
| `src/observability/alerting.py` | ✅ 直接复制 | 简化为阈值告警 |
| `src/observability/notifiers.py` | ✅ 直接复制 | 可保留企业微信/Slack |
| `src/observability/metrics_collector.py` | ✅ 直接复制 | 指标可简化 |

### 4.2 需要调整的文件

| 原项目文件 | 调整内容 |
|-----------|---------|
| `src/observability/decorators.py` | @observe_tool → @observe_skill，保留核心逻辑 |
| `src/observability/session.py` | SessionManager → CLI SessionContext，简化会话逻辑 |
| `src/observability/prompt_versioning.py` | Prompt Version → Skill Version，调整语义 |

### 4.3 需要新增的文件

| 新文件 | 用途 |
|--------|------|
| `src/cli/main.py` | Typer CLI 入口 |
| `src/cli/commands/skill.py` | skill 命令实现 |
| `src/cli/commands/feedback.py` | feedback 命令实现 |
| `src/skills/registry.py` | Skill 注册表 |
| `src/skills/loader.py` | Skill 加载器 |
| `src/skills/base.py` | Skill 基类 |
| `skills/*/` | 5 个示例 Skill |

---

## 5. Phase 实施计划

### Phase 1: 核心追踪

**目标**: 实现基础 Skill 执行追踪

**交付物**:
- [ ] 项目骨架搭建（pyproject.toml, requirements.txt）
- [ ] Langfuse 初始化和配置
- [ ] @observe_skill 装饰器
- [ ] hello_tracing Skill 实现
- [ ] 基础单元测试

**验证标准**:
- `skill run hello_tracing` 产生有效 Langfuse trace
- trace 包含 input、output、status 字段

---

### Phase 2: 会话管理

**目标**: 支持 session_id 传播和跨调用追踪

**交付物**:
- [ ] CLI SessionContext 实现
- [ ] `--session` 参数支持
- [ ] `--continue` 参数支持（延续上次会话）
- [ ] file_analyzer Skill 实现
- [ ] 会话追踪集成测试

**验证标准**:
- 同一 session_id 的多次调用在 Langfuse 中关联
- session_id 跨 CLI 调用持久化

---

### Phase 3: Skill 版本管理

**目标**: 支持 Skill 版本和 A/B 测试

**交付物**:
- [ ] Skill registry.json 实现
- [ ] SKILL.md 解析器
- [ ] 版本元数据注入
- [ ] llm_summarizer Skill 实现（v1/v2）
- [ ] 版本对比测试

**验证标准**:
- 可以在 trace 中区分 Skill 版本
- 支持同一 Skill 的多版本切换

---

### Phase 4: 反馈收集

**目标**: 支持用户满意度追踪

**交付物**:
- [ ] feedback 命令实现
- [ ] accept/reject/rating/comment 支持
- [ ] pipeline_demo Skill 实现
- [ ] 反馈集成测试

**验证标准**:
- 用户反馈正确关联到 trace
- Langfuse Dashboard 显示 feedback 数据

---

### Phase 5 (简化): 阈值告警

**目标**: 基本异常检测和通知

**交付物**:
- [ ] 成功率监控（<90% 触发）
- [ ] 延迟监控（>1s 触发）
- [ ] 告警日志输出
- [ ] (可选) 企业微信通知

**验证标准**:
- 模拟失败场景触发告警
- 日志显示告警信息

---

## 6. 测试策略

### 6.1 单元测试

| 测试目标 | 测试文件 | 覆盖内容 |
|---------|---------|---------|
| 装饰器 | `test_decorators.py` | @observe_skill 行为 |
| 会话 | `test_session.py` | SessionContext 传播 |
| 注册表 | `test_registry.py` | Skill 发现/加载 |
| 反馈 | `test_feedback.py` | 评分收集 |

### 6.2 集成测试

| 测试目标 | 测试文件 | 覆盖内容 |
|---------|---------|---------|
| CLI 命令 | `test_cli_commands.py` | skill list/run/discover |
| Skill 执行 | `test_skills.py` | 5 个 Skill 端到端 |
| 追踪 | `test_tracing.py` | Langfuse trace 生成 |
| 会话 | `test_session_integration.py` | session_id 传播 |

### 6.3 测试覆盖率目标

- 整体覆盖率：≥80%
- 核心模块覆盖率：≥90%

---

## 7. 附录

### 7.1 环境变量

```bash
# Langfuse 配置
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com

# OpenAI 配置
OPENAI_API_KEY=sk-xxx

# 可选：告警配置
ALERT_SUCCESS_RATE_THRESHOLD=0.9
ALERT_LATENCY_THRESHOLD_MS=1000
```

### 7.2 CLI 命令参考

```bash
# 查看可用 Skills
skill list

# 运行 Skill
skill run <skill_name> [args]

# 发现新 Skills
skill discover

# 提交反馈
feedback submit --trace-id <id> --rating 5
feedback submit --trace-id <id> --accept
feedback submit --trace-id <id> --reject --reason "not helpful"

# 会话管理
skill run <skill_name> --session <session_id>
skill run <skill_name> --continue
```

---

## 8. 审查记录

| 日期 | 版本 | 变更内容 | 审核人 |
|------|------|---------|-------|
| 2026-04-23 | 1.0.0 | 初始版本 | - |

---

*本规格文档定义了 agent-skill-cli-with-tracing 项目的技术实现方案，作为开发执行的依据。*
