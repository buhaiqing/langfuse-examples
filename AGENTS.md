# Langfuse 示例项目 - Agent 指令

> **仓库类型**: 生产级 Langfuse 示例应用  
> **技术栈**: Python 3.10-3.11 + FastAPI + Langfuse SDK 3.x-4.x  
> **核心领域**: LLM 可观测性、追踪、RAG、智能客服

---

## 快速开始命令

### 环境设置
```bash
# 根目录设置(创建 .env,安装依赖)
make setup

# 手动安装
uv sync  # 或: pip install -r requirements.txt
```

### 运行示例
```bash
make verify         # 验证设置和 API 密钥
make run-basic      # 基础追踪示例
make run-demo       # 完整客服演示
make run-tech       # 技术支持演示
make run-failure    # 失败分析演示
```

### 测试
```bash
make test                      # 运行所有测试(仅后端)
make test-cov                  # 运行测试并生成覆盖率报告
uv run pytest backend/tests/   # 直接执行 pytest
```

### 开发工作流
```bash
make lint           # 运行 ruff linter
make format         # 使用 black + ruff fix 格式化
make type-check     # 运行 mypy 类型检查
make check-all      # 运行全部: lint + format + type-check + test
make clean          # 清理缓存文件和构建产物
```

---

## 项目结构

```
langfuse-examples/
├── mcp-with-tracing/           # MCP Server 可观测性平台
│   ├── src/server.py          # FastMCP 服务器入口
│   ├── tests/                 # pytest 测试(114 个通过)
│   └── pyproject.toml         # Python 3.11+, FastMCP 3.x
│
└── smart-customer-service/     # 智能客服系统
    ├── backend/
    │   ├── api/main.py        # FastAPI 入口
    │   ├── core/              # Langfuse 追踪核心
    │   ├── modules/           # 业务逻辑(RAG、工具等)
    │   ├── tests/             # 后端测试
    │   └── Dockerfile         # uvicorn api.main:app
    ├── frontend/              # React + TypeScript + Vite
    │   ├── package.json       # Node 依赖
    │   └── src/               # UI 组件
    ├── pyproject.toml         # Python 3.10+
    ├── Makefile               # 根目录编排
    └── requirements.txt       # Python 依赖
```

**根目录不包含**: `package.json`、`pnpm-workspace.yaml`、`.cursorrules` 或 `opencode.json`

---

## Langfuse 集成模式

### 核心概念
- **Trace**: 完整的用户会话,包含 `session_id` 和 `user_id`
- **Observation**: 基于 OpenTelemetry 的 span(span、generation、event、tool)
- **Score**: NUMERIC(0-1)、BOOLEAN(0/1) 或 CATEGORICAL 评分
- **Masking**: 全局 `mask=` 函数用于移除 PII(电话、邮箱、身份证)

### Python 模式 (v3.x-4.x)
```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    mask=mask_sensitive_data  # 全局 PII 脱敏
)

# 上下文管理器模式
with langfuse.start_as_current_observation(
    as_type="span", 
    name="intent_recognition",
    user_id="user_123",
    session_id="session_abc"
) as span:
    result = recognize_intent(query)
    span.end(output_data={"intent": result})
```

### 装饰器模式
```python
from core.tracing import trace_customer_service

@trace_customer_service(
    name="api_error_troubleshooting",
    session_id="session_123",
    user_id="user_456",
    tags=["technical_support", "api_issue"]
)
async def handle_customer_query(query: str):
    # 自动追踪到 Langfuse
    pass
```

### 评分体系
| 评分名称 | 类型 | 范围 | 用途 |
|-----------|------|-------|---------|
| `intent_confidence` | NUMERIC | 0-1 | 意图识别置信度 |
| `retrieval_relevance` | NUMERIC | 0-1 | RAG 检索质量 |
| `issue_resolved` | BOOLEAN | 0/1 | 问题解决状态 |
| `user_satisfaction` | NUMERIC | 1-5 | 用户满意度评分 |
| `failure_type` | CATEGORICAL | - | 失败分类 |

---

## 代码规范

### Python 要求
- **Python 版本**: 3.10+ (smart-customer-service), 3.11+ (mcp-with-tracing)
- **格式化工具**: `black` (行长度: 100)
- **Linter**: `ruff` (选择: E, W, F, I, B, C4, UP)
- **类型检查器**: `mypy` (严格模式可选)
- **测试运行器**: `pytest` 配合 `pytest-asyncio`

### 强制规则
- ✅ 所有公共函数必须有类型注解
- ✅ 所有公共类/函数必须有 Google 风格的 docstrings
- ✅ 使用 `uv` 包管理器(推荐)或 `pip`
- ✅ 永远不要提交 `.env` 文件(始终使用 `.env.example` 模板)
- ✅ 永远不要硬编码 API 密钥或机密信息
- ✅ 永远不要在未记录日志的情况下抑制异常
- ✅ 始终对敏感数据使用 PII 脱敏

### 测试标准
- **最低覆盖率**: 整体 90%,关键路径 95%
- **测试模式**: `test_*.py` 文件,`Test*` 类,`test_*` 函数
- **Fixtures**: 使用 `conftest.py` 共享测试 fixtures
- **Mocking**: 始终 mock 外部依赖(Langfuse、OpenAI、数据库)

---

## 环境配置

### 必需变量 (.env)
```bash
# Langfuse 配置
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxxxxxx
LANGFUSE_HOST=https://cloud.langfuse.com  # 可选,默认为 cloud

# OpenAI 配置
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

# 可选配置
ENVIRONMENT=development  # development, staging, production
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
```

### 验证
设置后始终运行 `make verify` 以验证:
- Langfuse API 连接性
- OpenAI API 连接性
- 环境变量配置

---

## Docker 与基础设施

### 后端服务
```bash
make docker-up      # 启动所有容器(Redis、PostgreSQL、ChromaDB、MinIO)
make docker-down    # 停止容器
make docker-logs    # 查看容器日志
make db-migrate     # 运行数据库迁移
```

**暴露的服务:**
- API: `http://localhost:8000`
- Redis: `localhost:6379`
- PostgreSQL: `localhost:5432`
- ChromaDB: `localhost:8001`
- MinIO Console: `http://localhost:9001`

### 容器入口点
```dockerfile
# 后端 Dockerfile
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 常见问题

### 追踪问题
**问题**: Traces 未出现在 Langfuse 仪表板中  
**解决方案**: 
1. 验证 API 密钥是否正确
2. 调用 `langfuse.flush()` 强制发送待处理的 traces
3. 检查到 `https://cloud.langfuse.com` 的网络连接
4. 确保设置了 session_id 和 user_id

### 测试失败
**问题**: 测试失败,提示 "module not found"  
**解决方案**: 
1. 确保虚拟环境已激活
2. 运行 `uv sync` 安装依赖
3. 检查是否从 backend/ 目录运行测试

### 数据脱敏
**问题**: 敏感数据未被脱敏  
**解决方案**:
1. 确保在 Langfuse 客户端中设置了 `mask=mask_sensitive_data`
2. 验证字段名匹配预期模式(phone、email 等)
3. 在记录任何请求/响应数据之前使用 `sanitize_for_logging()`

---

## 参考资料

- [Langfuse Python SDK](https://langfuse.com/docs/sdk/python)
- [Langfuse JavaScript SDK](https://langfuse.com/docs/sdk/typescript)
- [Langfuse 文档](https://langfuse.com/docs)
- [Langfuse 示例仓库](https://github.com/langfuse/langfuse-examples)
- 项目特定开发规则: `.lingma/rules/开发规范.md`

---

**最后更新**: 2026-04-13  
**维护者**: 平台团队  
**版本**: 1.0.0
