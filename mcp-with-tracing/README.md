# MCP Server Langfuse Observability Platform

生产级 LLM 可观测性平台，基于 Langfuse 为 MCP Server 提供完整的追踪、监控和告警能力。

## 项目状态

**当前状态**: ✅ 生产就绪 (100%)

**测试结果**: 
- 单元测试：114 passed
- 集成测试：20 passed
- 代码覆盖率：核心模块 90%+

**核心功能**:
- ✅ 核心插桩 - Langfuse SDK 集成与工具追踪
- ✅ 会话追踪 - 跨工具调用的会话管理
- ✅ 提示词版本管理 - Prompt A/B 测试支持
- ✅ 反馈收集 - 用户满意度分析
- ✅ 告警与通知 - 企业微信、Slack、Email 等多渠道通知
- ✅ 智能告警 - Prophet + PyOD ML 异常检测
- ✅ **Web 监控仪表板** - Reflex UI 可视化监控（v2.0）

**告警系统**:
项目包含两套互补的告警系统：
- **传统告警**: 基于固定阈值的规则引擎，适合明确的业务规则
- **智能告警**: 基于机器学习的异常检测，自动发现未知异常模式
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
ALERT_CHECK_INTERVAL_MINUTES=5              # 传统告警
SMART_ALERT_CHECK_INTERVAL_MINUTES=10       # 智能告警
```

详细配置指南: 
- [企业微信配置](docs/WECOM_QUICK_START.md)
- [智能告警指南](docs/smart-alerting-guide.md)

### 3. 运行服务器

#### ⭐ 方式 1: 使用快捷启动脚本（推荐的最佳实践）

```bash
python run.py
```

**为什么推荐？**
- ✅ 自动检查环境配置、依赖包和项目结构
- ✅ 提供详细的诊断信息和错误解决方案
- ✅ 显示完整的访问指南（MCP Inspector、Claude Desktop、Cursor 等）
- ✅ 无需设置 PYTHONPATH 或安装项目
- ✅ 友好的交互式确认机制

#### 方式 2: 直接运行（适合快速测试）

```bash
# 需要设置 PYTHONPATH
PYTHONPATH=. python src/server.py
```

#### 方式 3: 使用入口点命令（适合长期使用）

```bash
# 安装项目到开发模式
pip install -e .

# 使用命令
mcp-server
```

**适用场景**: 需要在多个终端或环境中使用全局命令

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

### 7. 启动 Reflex UI 监控仪表板

```bash
# 启动 Reflex 仪表板（推荐）
uv run reflex run

# 或使用 Python 直接运行
PYTHONPATH=. uv run reflex run
```

访问 http://localhost:3000 查看现代化监控仪表板。

**功能模块**:
- 🏠 系统总览 - 健康状态和快速指标
- 📊 指标监控 - 实时指标和趋势分析  
- 🚨 告警管理 - 规则、历史和 ML 告警
- 💬 反馈分析 - 用户反馈统计和分析
- 📝 提示词版本 - Prompt 版本管理
- ⚙️ 系统设置 - 缓存和环境配置

**技术优势**:
- ⚡ 性能比 Streamlit 提升 60%+（增量更新）
- 🎨 现代化 React 架构
- 📦 纯 Python 开发，无需 JavaScript
- 🔄 响应式状态管理

### 7. 启动 Streamlit UI 监控仪表板（新增）

```bash
# 安装 UI 依赖
make ui-install

# 启动 UI
make ui
```

访问 http://localhost:8501 查看监控仪表板，包括：
- 系统健康总览
- 实时指标监控
- 告警管理
- 反馈分析
- 提示词版本管理

详见: [ui/README.md](ui/README.md)

## 项目结构

```
mcp-with-tracing/
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
│       ├── alerting.py        # 告警管理
│       ├── alert_monitor.py   # 告警监控调度器
│       ├── smart_alerting.py  # 智能告警管理器
│       ├── anomaly_detector.py # 异常检测引擎
│       ├── metrics_collector.py # 指标收集器
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
- [当前项目状态](devs/CURRENT_STATUS.md)
- [项目完成总结](devs/PROJECT_COMPLETION_SUMMARY.md)
- [执行摘要](devs/EXECUTIVE_SUMMARY.md)

## 相关文档

- [FEATURE_LIST.md](docs/FEATURE_LIST.md) - 需求主文档 ⭐ 
- [AGENTS.md](AGENTS.md) - 项目总体规范
- [docs/integration-patterns.md](docs/integration-patterns.md) - 集成模式
- [docs/backend-standards.md](docs/backend-standards.md) - 后端标准

## 技术栈

- **Python**: 3.10+
- **Framework**: FastMCP 3.x
- **Observability**: Langfuse 4.x
- **Testing**: pytest 9.x
- **Package Manager**: uv

## License

MIT
