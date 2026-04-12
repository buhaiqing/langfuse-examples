# 项目文档索引

> **项目**: MCP Langfuse Observability Platform  
> **更新日期**: 2026-04-13  
> **状态**: ✅ 全部完成 (5/5 Phase)

---

## 📁 文档目录结构

```
mcp-with-tracing/
├── docs/                          # 技术文档
│   ├── backend-standards.md       # 后端开发标准
│   ├── frontend-standards.md      # 前端开发标准
│   ├── testing-guide.md           # 测试指南
│   ├── testing-organization.md    # 测试组织指南 ⭐ NEW
│   ├── concurrent-testing-guide.md # 并发测试配置 ⭐ NEW
│   ├── code-review-guide.md       # 代码审查指南
│   ├── security-guide.md          # 安全指南
│   ├── integration-patterns.md    # 集成模式
│   ├── session-view-guide.md      # 会话查看指南
│   ├── prompt-effectiveness-dashboard.md      # 提示词效果仪表板
│   ├── satisfaction-dashboard-guide.md        # 满意度仪表板指南
│   ├── monitoring-guide.md        # 监控指南
│   ├── event-response-runbook.md  # 事件响应手册
│   ├── wecom-alert-setup.md       # 企业微信告警配置
│   └── best-practices.md          # 最佳实践
│
├── devs/                          # 开发文档
│   ├── PROJECT_COMPLETION_SUMMARY.md  # 项目完成总结 ⭐ MOVED
│   ├── TEST_SEPARATION_SUMMARY.md     # 测试分离总结 ⭐ NEW
│   ├── TESTING_QUICK_REFERENCE.md     # 测试快速参考 ⭐ NEW (root)
│   ├── phase1/
│   │   ├── phase1_plan.md
│   │   └── phase1_progress.md
│   ├── phase2/
│   │   ├── phase2_plan.md
│   │   └── phase2_progress.md
│   ├── phase3/
│   │   └── phase3_plan.md
│   ├── phase4/
│   │   └── phase4_plan.md
│   ├── phase5/
│   │   ├── phase5_plan.md
│   │   ├── phase5_completion_report.md
│   │   └── PHASE5_CHECKLIST.md
│   ├── DEVELOPMENT_PLAN.md
│   ├── REQUIREMENT_ALIGNMENT_AND_TASKS.md
│   ├── DETAILED_TASK_BREAKDOWN.md
│   ├── EXECUTIVE_SUMMARY.md
│   ├── WORK_SUMMARY.md
│   ├── COMPLETION_SUMMARY.md
│   ├── QUICK_REFERENCE.md
│   └── DOCUMENT_INDEX.md
│
├── manuals/                       # 用户手册
│   ├── README.md
│   ├── 快速入门.md
│   ├── API 参考.md
│   └── 用户手册.md
│
├── Makefile                       # 构建和测试命令
├── pytest.ini                     # pytest 配置
├── .env.example                   # 环境变量模板
└── README.md                      # 项目说明
```

---

## 📚 文档分类

### 🎯 快速开始

| 文档 | 路径 | 说明 |
|------|------|------|
| 项目README | [README.md](../README.md) | 项目概述和快速开始 |
| 测试快速参考 | [TESTING_QUICK_REFERENCE.md](../TESTING_QUICK_REFERENCE.md) | 测试命令速查 ⭐ |
| 快速入门 | [manuals/快速入门.md](../manuals/快速入门.md) | 用户快速入门指南 |

---

### 🏗️ 架构和设计

| 文档 | 路径 | 说明 |
|------|------|------|
| 项目完成总结 | [devs/PROJECT_COMPLETION_SUMMARY.md](PROJECT_COMPLETION_SUMMARY.md) | 完整的项目总结 ⭐ |
| 集成模式 | [docs/integration-patterns.md](../docs/integration-patterns.md) | 系统集成模式 |
| 后端标准 | [docs/backend-standards.md](../docs/backend-standards.md) | 后端开发规范 |
| 前端标准 | [docs/frontend-standards.md](../docs/frontend-standards.md) | 前端开发规范 |

---

### 🧪 测试相关

| 文档 | 路径 | 说明 |
|------|------|------|
| 测试组织指南 | [docs/testing-organization.md](../docs/testing-organization.md) | 测试结构和最佳实践 ⭐ |
| 并发测试配置 | [docs/concurrent-testing-guide.md](../docs/concurrent-testing-guide.md) | 并发执行配置 ⭐ |
| 测试分离总结 | [devs/TEST_SEPARATION_SUMMARY.md](TEST_SEPARATION_SUMMARY.md) | 测试分离完成报告 ⭐ |
| 测试指南 | [docs/testing-guide.md](../docs/testing-guide.md) | 测试编写指南 |
| 代码审查指南 | [docs/code-review-guide.md](../docs/code-review-guide.md) | 代码审查标准 |

---

### 🔧 开发和运维

| 文档 | 路径 | 说明 |
|------|------|------|
| 事件响应手册 | [docs/event-response-runbook.md](../docs/event-response-runbook.md) | 告警响应流程 |
| 企业微信配置 | [docs/wecom-alert-setup.md](../docs/wecom-alert-setup.md) | WeCom 告警配置 |
| 监控指南 | [docs/monitoring-guide.md](../docs/monitoring-guide.md) | 监控配置和使用 |
| 安全指南 | [docs/security-guide.md](../docs/security-guide.md) | 安全最佳实践 |
| 最佳实践 | [docs/best-practices.md](../docs/best-practices.md) | 通用最佳实践 |

---

### 📊 功能和特性

| 文档 | 路径 | 说明 |
|------|------|------|
| 会话查看指南 | [docs/session-view-guide.md](../docs/session-view-guide.md) | Session 追踪使用 |
| 提示词效果仪表板 | [docs/prompt-effectiveness-dashboard.md](../docs/prompt-effectiveness-dashboard.md) | Prompt 分析 |
| 满意度仪表板指南 | [docs/satisfaction-dashboard-guide.md](../docs/satisfaction-dashboard-guide.md) | 反馈分析 |

---

### 📋 项目规划

| 文档 | 路径 | 说明 |
|------|------|------|
| 开发计划 | [devs/DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) | 整体开发计划 |
| 需求对齐 | [devs/REQUIREMENT_ALIGNMENT_AND_TASKS.md](REQUIREMENT_ALIGNMENT_AND_TASKS.md) | 需求和任务拆分 |
| 任务分解 | [devs/DETAILED_TASK_BREAKDOWN.md](DETAILED_TASK_BREAKDOWN.md) | 详细任务分解 |
| 执行摘要 | [devs/EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | 高层摘要 |
| 工作总结 | [devs/WORK_SUMMARY.md](WORK_SUMMARY.md) | 工作总结 |
| 完成摘要 | [devs/COMPLETION_SUMMARY.md](COMPLETION_SUMMARY.md) | 完成摘要 |
| 快速参考 | [devs/QUICK_REFERENCE.md](QUICK_REFERENCE.md) | 开发快速参考 |

---

### 📈 Phase 进度报告

#### Phase 1: 核心插桩
- [Phase 1 计划](phase1/phase1_plan.md)
- [Phase 1 进度](phase1/phase1_progress.md)

#### Phase 2: 会话追踪
- [Phase 2 计划](phase2/phase2_plan.md)
- [Phase 2 进度](phase2/phase2_progress.md)

#### Phase 3: 提示词版本管理
- [Phase 3 计划](phase3/phase3_plan.md)

#### Phase 4: 反馈收集
- [Phase 4 计划](phase4/phase4_plan.md)

#### Phase 5: 告警与通知
- [Phase 5 计划](phase5/phase5_plan.md)
- [Phase 5 完成报告](phase5/phase5_completion_report.md)
- [Phase 5 检查清单](phase5/PHASE5_CHECKLIST.md)

---

### 📖 用户手册

| 文档 | 路径 | 说明 |
|------|------|------|
| 手册首页 | [manuals/README.md](../manuals/README.md) | 用户手册索引 |
| 快速入门 | [manuals/快速入门.md](../manuals/快速入门.md) | 快速开始指南 |
| API 参考 | [manuals/API 参考.md](../manuals/API%20参考.md) | API 文档 |
| 用户手册 | [manuals/用户手册.md](../manuals/用户手册.md) | 完整用户指南 |

---

## 🔍 按主题查找

### 新手入门
1. [README.md](../README.md) - 了解项目
2. [manuals/快速入门.md](../manuals/快速入门.md) - 快速开始
3. [TESTING_QUICK_REFERENCE.md](../TESTING_QUICK_REFERENCE.md) - 测试命令

### 开发人员
1. [docs/backend-standards.md](../docs/backend-standards.md) - 开发规范
2. [docs/testing-organization.md](../docs/testing-organization.md) - 测试指南
3. [docs/concurrent-testing-guide.md](../docs/concurrent-testing-guide.md) - 并发测试
4. [devs/PROJECT_COMPLETION_SUMMARY.md](PROJECT_COMPLETION_SUMMARY.md) - 项目总结

### 运维人员
1. [docs/event-response-runbook.md](../docs/event-response-runbook.md) - 事件响应
2. [docs/wecom-alert-setup.md](../docs/wecom-alert-setup.md) - 告警配置
3. [docs/monitoring-guide.md](../docs/monitoring-guide.md) - 监控指南

### 测试人员
1. [docs/testing-organization.md](../docs/testing-organization.md) - 测试组织
2. [docs/testing-guide.md](../docs/testing-guide.md) - 测试编写
3. [devs/TEST_SEPARATION_SUMMARY.md](TEST_SEPARATION_SUMMARY.md) - 测试分离

### 架构师
1. [devs/PROJECT_COMPLETION_SUMMARY.md](PROJECT_COMPLETION_SUMMARY.md) - 完整架构
2. [docs/integration-patterns.md](../docs/integration-patterns.md) - 集成模式
3. [docs/best-practices.md](../docs/best-practices.md) - 最佳实践

---

## 📊 文档统计

| 类别 | 数量 | 总大小 |
|------|------|--------|
| 技术文档 (docs/) | 15 | ~80 KB |
| 开发文档 (devs/) | 20+ | ~150 KB |
| 用户手册 (manuals/) | 4 | ~30 KB |
| **总计** | **40+** | **~260 KB** |

---

## 🎯 推荐阅读路径

### 路径 1: 快速上手 (15 分钟)
1. [README.md](../README.md) (5 min)
2. [manuals/快速入门.md](../manuals/快速入门.md) (5 min)
3. [TESTING_QUICK_REFERENCE.md](../TESTING_QUICK_REFERENCE.md) (5 min)

### 路径 2: 深入开发 (1 小时)
1. [docs/backend-standards.md](../docs/backend-standards.md) (15 min)
2. [docs/testing-organization.md](../docs/testing-organization.md) (15 min)
3. [docs/concurrent-testing-guide.md](../docs/concurrent-testing-guide.md) (15 min)
4. [devs/PROJECT_COMPLETION_SUMMARY.md](PROJECT_COMPLETION_SUMMARY.md) (15 min)

### 路径 3: 运维部署 (30 分钟)
1. [docs/event-response-runbook.md](../docs/event-response-runbook.md) (10 min)
2. [docs/wecom-alert-setup.md](../docs/wecom-alert-setup.md) (10 min)
3. [docs/monitoring-guide.md](../docs/monitoring-guide.md) (10 min)

---

## 🔗 外部资源

- [Langfuse 官方文档](https://langfuse.com/docs)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [FastMCP Python SDK](https://github.com/jlowin/fastmcp)
- [pytest 文档](https://docs.pytest.org/)
- [Python 最佳实践](https://docs.python-guide.org/)

---

## 📝 更新历史

| 日期 | 版本 | 变更说明 |
|------|------|----------|
| 2026-04-13 | 1.1.0 | 添加测试相关文档，移动项目总结到 devs/ |
| 2026-04-13 | 1.0.0 | 初始版本，整理所有文档 |

---

**文档索引完成！** 📚

使用 `Ctrl+F` 或 `Cmd+F` 快速搜索文档。
