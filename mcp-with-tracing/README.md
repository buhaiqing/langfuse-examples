# MCP Server Langfuse Observability Platform

生产级 LLM 可观测性平台，基于 Langfuse 为 MCP Server 提供完整的追踪、监控和告警能力。

## 项目状态

**当前阶段**: Phase 1 ✅ 已完成 (100%)

**测试结果**: 
- 单元测试：11 passed
- 集成测试：3/3 passed
- 代码覆盖率：70%

## 快速开始

### 1. 安装依赖

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `.env` 文件配置 Langfuse API keys：

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 3. 运行服务器

```bash
python src/server.py
```

### 4. 运行测试

```bash
pytest tests/ -v
```

### 5. 运行集成测试

```bash
python scripts/test_langfuse_connection.py
python scripts/test_success_failure_tracking.py
```

## 项目结构

```
example2/
├── src/
│   ├── server.py              # MCP 主服务器
│   ├── tools/                 # MCP 工具模块
│   └── observability/         # Langfuse 插桩模块
│       ├── config.py          # 配置管理
│       ├── instrumentation.py # 初始化工具
│       ├── decorators.py      # 装饰器
│       └── langfuse_client.py # Langfuse 客户端
├── tests/                     # 单元测试
├── scripts/                   # 测试脚本
├── devs/                      # 开发文档
└── requirements.txt           # Python 依赖
```

## Phase 1 完成功能

### ✅ 任务 1.1: Langfuse SDK 配置
- requirements.txt 配置
- pyproject.toml 项目配置
- .env.example 环境变量模板
- ObservabilityConfig 配置类

### ✅ 任务 1.2: 插桩模块
- init_observability() 初始化函数
- get_langfuse_client() 客户端获取
- Session context 上下文管理
- LangfuseObserver 观测器类
- 三个核心装饰器

### ✅ 任务 1.3: 工具装饰器
- @observe_tool - 工具执行追踪
- @track_session - 会话元数据
- @track_prompt_version - 提示词版本
- 示例工具 (echo, calculate, greet)

### ✅ 任务 1.4: Langfuse 控制台验证
- Langfuse 连接测试通过
- 追踪数据成功提交
- Observation ID 正常生成
- 查看测试：`python scripts/test_langfuse_connection.py`

### ✅ 任务 1.5: 成功/失败追踪
- 错误捕获机制
- 成功/失败标记
- 完整测试覆盖
- 查看测试：`python scripts/test_success_failure_tracking.py`

## 测试结果

### 单元测试
```
tests/test_instrumentation.py: 11 passed
Coverage: 70% overall
```

### 集成测试
```
scripts/test_langfuse_connection.py: PASSED
scripts/test_success_failure_tracking.py: 3/3 passed
```

## 开发文档

- [整体开发计划](devs/DEVELOPMENT_PLAN.md)
- [Phase 1 详细计划](devs/phase1/phase1_plan.md)
- [Phase 1 进度追踪](devs/phase1/phase1_progress.md)

## 相关文档

- [AGENTS.md](AGENTS.md) - 项目总体规范
- [docs/integration-patterns.md](docs/integration-patterns.md) - 集成模式
- [docs/backend-standards.md](docs/backend-standards.md) - 后端标准

## 技术栈

- **Python**: 3.11+
- **Framework**: FastMCP 3.x
- **Observability**: Langfuse 4.x
- **Testing**: pytest 9.x
- **Package Manager**: uv

## License

MIT
