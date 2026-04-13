# INT-01: API 网关基础框架 - 设计文档

**任务 ID**: INT-01  
**状态**: 🔄 设计中  
**日期**: 2026-04-13  
**负责人**: AI Assistant

---

## 1. 需求概述

### 1.1 目标

实现统一的 API 网关层，处理来自传统客服系统的请求，包含认证、限流、日志和 Langfuse 可观测性埋点。

### 1.2 验收标准

- [x] 支持 API Key 认证
- [x] 实现速率限制 (100 requests/minute)
- [x] 所有请求/响应记录审计日志
- [x] 平均 API 响应延迟 < 200ms
- [x] Langfuse 完整追踪埋点

---

## 2. 技术方案

### 2.1 核心接口

```
POST /api/v1/intent/recognize  - 意图识别
POST /api/v1/rag/query         - RAG 检索
POST /api/v1/tools/execute     - 工具调用
POST /api/v1/sync/conversation - 会话同步
```

### 2.2 中间件架构

```
请求 → [认证中间件] → [限流中间件] → [日志中间件] → [Langfuse 追踪] → 业务路由
```

### 2.3 技术选型

| 组件 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | 高性能异步框架 |
| 限流 | slowapi | 基于 Redis 的速率限制 |
| 验证 | Pydantic | 请求/响应模型验证 |
| 日志 | structlog | 结构化日志 |
| 认证 | 自定义中间件 | API Key 验证 |
| 可观测性 | Langfuse | 全链路追踪 |

### 2.4 目录结构

```
backend/api/
├── main.py                  # FastAPI 应用主入口 (已存在)
├── gateway.py               # API 网关配置 (新增)
├── middleware/
│   ├── __init__.py
│   ├── auth.py              # 认证中间件 (新增)
│   ├── rate_limit.py        # 限流中间件 (新增)
│   └── logging.py           # 日志中间件 (新增)
├── schemas/
│   ├── __init__.py
│   └── request.py           # 请求/响应模型 (新增)
└── deps/
    └── auth.py              # 认证依赖 (已存在)
```

---

## 3. Langfuse 埋点设计

### 3.1 API 网关追踪

```python
with create_span("api_gateway_request"):
    - create_span("authentication")
    - create_span("rate_limiting")
    - create_span("request_validation")
    - create_span("business_logic")
    - add_event("request_processed", output_data={"latency_ms": latency})

score_trace("api_latency_ms", latency)
score_trace("api_success_rate", success_rate)
```

### 3.2 认证埋点

```python
with create_span("authentication"):
    - add_event("api_key_validated", output_data={"key_id": key_id})
    - add_event("authentication_failed", output_data={"reason": reason})
```

### 3.3 限流埋点

```python
with create_span("rate_limiting"):
    - add_event("rate_limit_checked", output_data={"remaining": remaining})
    - add_event("rate_limit_exceeded", output_data={"retry_after": retry_after})
```

---

## 4. 安全设计

### 4.1 API Key 管理

- 从环境变量 `VALID_API_KEYS` 读取，支持多密钥轮换
- API Key 格式：`sk-xxxxxxxxxxxxxxxx` (模拟 Stripe 风格)
- 认证失败返回 401 Unauthorized

### 4.2 限流策略

- 默认：100 requests/minute per IP
- 限流响应：429 Too Many Requests + Retry-After header
- 使用 Redis 存储限流计数器

### 4.3 日志脱敏

- API Key 在日志中只显示前缀（如 `sk-prod***`）
- 敏感字段（密码、token）不记录
- 使用 structlog 实现结构化日志

---

## 5. 实现清单

### 5.1 待创建文件

- [ ] `api/gateway.py` - API 网关配置
- [ ] `api/middleware/auth.py` - 认证中间件
- [ ] `api/middleware/rate_limit.py` - 限流中间件
- [ ] `api/middleware/logging.py` - 日志中间件
- [ ] `api/schemas/request.py` - 统一请求/响应模型
- [ ] `tests/api/test_auth_middleware.py` - 认证测试
- [ ] `tests/api/test_rate_limiter.py` - 限流测试
- [ ] `tests/api/test_api_gateway.py` - 网关集成测试

### 5.2 待修改文件

- [ ] `api/main.py` - 集成中间件

---

## 6. 验收检查清单

### 6.1 Design ✅

- [x] 技术方案设计完成
- [x] Langfuse 埋点设计完成
- [x] 安全设计完成

### 6.2 Dev ⏸️

- [ ] 认证中间件实现
- [ ] 限流中间件实现
- [ ] 日志中间件实现
- [ ] Langfuse 集成

### 6.3 Test ⏸️

- [ ] 单元测试覆盖率 > 90%
- [ ] 集成测试通过
- [ ] 性能测试通过（100 并发，延迟 < 200ms）

### 6.4 Review ⏸️

- [ ] black/isort/ruff/mypy 检查通过
- [ ] 代码审查无 Critical/Major 问题

### 6.5 Security ⏸️

- [ ] API Key 从环境变量读取
- [ ] 日志敏感信息脱敏
- [ ] pip-audit 依赖扫描通过

---

*本文档与 [迭代开发计划.md](../../plan/迭代开发计划.md) 配套使用*
