# MCP Server Langfuse Observability Platform

生产级 LLM 可观测性平台，基于 Langfuse 为 MCP Server 提供完整的追踪、监控和告警能力。

## 项目状态

**当前阶段**: Phase 6 ✅ 已完成 (100%)

**测试结果**: 
- 单元测试：114 passed
- 集成测试：20 passed
- 代码覆盖率：核心模块 90%+

**完成功能**:
- ✅ Phase 1: 核心插桩
- ✅ Phase 2: 会话追踪
- ✅ Phase 3: 提示词版本管理
- ✅ Phase 4: 反馈收集
- ✅ Phase 5: 告警与通知（企业微信、Slack、Email等）
- ✅ Phase 6: 智能告警(ML) - Prophet+PyOD异常检测

**告警系统**:
项目包含两套并行的告警系统：
- **传统告警 (Phase 5)**: 基于固定阈值的规则引擎，适合明确的业务规则
- **智能告警 (Phase 6)**: 基于机器学习的异常检测，自动发现未知异常模式
- 两者互补运行，共享通知渠道，统一告警存储

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

**可选**: 配置告警通知

```bash
# 企业微信 Webhook URL
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY

# 告警检查间隔（分钟）
ALERT_CHECK_INTERVAL_MINUTES=5              # 传统告警（Phase 5）
SMART_ALERT_CHECK_INTERVAL_MINUTES=10       # 智能告警（Phase 6）
```

详细配置指南: 
- [企业微信配置](docs/WECOM_QUICK_START.md)
- [智能告警快速启动](docs/phase6-quick-start.md)

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
python scripts/test_session_tracing.py
python scripts/test_prompt_versioning.py
python scripts/test_alerting.py
```

### 6. 配置企业微信告警（可选）

```bash
# 快速配置和测试
python scripts/setup_wecom_alerts.py
```

详见: [docs/WECOM_QUICK_START.md](docs/WECOM_QUICK_START.md)

## 项目结构

```
example2/
├── src/
│   ├── server.py              # MCP 主服务器
│   ├── tools/                 # MCP 工具模块
│   │   └── feedback_tool.py   # 反馈收集工具
│   └── observability/         # Langfuse 插桩模块
│       ├── config.py          # 配置管理
│       ├── instrumentation.py # 初始化工具
│       ├── decorators.py      # 装饰器
│       ├── langfuse_client.py # Langfuse 客户端
│       ├── session.py         # 会话追踪
│       ├── prompt_versioning.py # 提示词版本管理
│       ├── feedback.py        # 反馈收集
│       ├── alerting.py        # 告警管理 (Phase 5)
│       ├── alert_monitor.py   # 告警监控调度器 (Phase 5)
│       ├── smart_alerting.py  # 智能告警管理器 (Phase 6)
│       ├── anomaly_detector.py # 异常检测引擎 (Phase 6)
│       ├── metrics_collector.py # 指标收集器 (Phase 6)
│       └── notifiers.py       # 通知渠道（企业微信、Slack等）
├── tests/                     # 单元测试
├── scripts/                   # 测试和配置脚本
│   ├── setup_wecom_alerts.py  # 企业微信配置脚本
│   ├── test_*.py             # 集成测试
│   └── query_*.py            # 数据查询脚本
├── docs/                      # 文档
│   ├── WECOM_QUICK_START.md   # 企业微信快速配置
│   ├── wecom-alert-setup.md   # 企业微信详细指南
│   ├── event-response-runbook.md # 事件响应手册
│   └── ...                    # 其他文档
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
- 示例工具 (echo, calculate)

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
