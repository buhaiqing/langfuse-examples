# Makefile 启动指令使用指南

## 快速启动命令

### 1. 仅启动 MCP Server（后端）

```bash
make start
```

**启动后会显示：**
```
═══════════════════════════════════════════════════════════════
🚀 Starting MCP Langfuse Observability Server...
═══════════════════════════════════════════════════════════════

📋 Server Information:
  • Backend: MCP Server (FastMCP)
  • Transport: Stdio (JSON-RPC 2.0)
  • Logs: Will show in this terminal

🌐 Access Points:
  • MCP Inspector: http://localhost:5173 (for testing)
  • Langfuse Dashboard: https://cloud.langfuse.com

💡 Tips:
  • Press Ctrl+C to stop the server
  • Use MCP Inspector to test all tools interactively
  • Check Langfuse dashboard for real-time observability data

═══════════════════════════════════════════════════════════════
```

### 2. 同时启动 MCP Server + Streamlit UI（后端 + 前端）⭐ 推荐

```bash
make start-all
```

**启动后会显示：**
```
═══════════════════════════════════════════════════════════════
🚀 Starting MCP Langfuse Observability Platform...
═══════════════════════════════════════════════════════════════

📋 Starting Components:
  ✓ Backend: MCP Server (FastMCP)
  ✓ Frontend: Streamlit UI Dashboard

═══════════════════════════════════════════════════════════════
🌐 Access Points:
═══════════════════════════════════════════════════════════════

  📊 Streamlit UI Dashboard:
     → URL: http://localhost:8501
     → Features:
       • System health overview
       • Real-time metrics monitoring
       • Alert management
       • Feedback analysis
       • Prompt version management
       • System settings

  🔌 MCP Server (Backend):
     → Transport: Stdio (JSON-RPC 2.0)
     → MCP Inspector: http://localhost:5173
     → Available Tools:
       • health_check
       • submit_feedback_accept
       • submit_feedback_reject
       • submit_feedback_rating
       • submit_feedback_comment

  📈 Langfuse Dashboard:
     → URL: https://cloud.langfuse.com
     → View traces, sessions, and metrics

═══════════════════════════════════════════════════════════════
💡 Usage Tips:
═══════════════════════════════════════════════════════════════

  • Both services will run in this terminal
  • Press Ctrl+C to stop all services
  • Open http://localhost:8501 for the UI dashboard
  • Use MCP Inspector to test backend tools
  • Check logs below for server activity

═══════════════════════════════════════════════════════════════
```

### 3. 仅启动 Streamlit UI（前端）

```bash
make ui
```

**启动后会显示：**
```
═══════════════════════════════════════════════════════════════
📊 Starting Streamlit UI Dashboard...
═══════════════════════════════════════════════════════════════

🌐 Access Point:
  → URL: http://localhost:8501

📋 Features:
  • System health overview
  • Real-time metrics monitoring
  • Alert management
  • Feedback analysis
  • Prompt version management
  • System settings

💡 Tips:
  • Press Ctrl+C to stop the UI
  • The UI will auto-reload on code changes
  • Requires MCP Server to be running for data

═══════════════════════════════════════════════════════════════
```

## 完整命令列表

运行 `make help` 查看所有可用命令：

```bash
make help
```

**输出：**
```
MCP Langfuse Observability - Available Commands

🚀 Quick Start:
  make start          - Start MCP Server only (backend)
  make start-all      - Start MCP Server + Streamlit UI (backend + frontend)

Testing:
  make test           - Run all tests (unit + integration)
  make test-unit      - Run unit tests only
  make test-integration - Run integration tests only
  make test-cov       - Run tests with coverage report
  make test-html      - Run tests and open HTML coverage report
  make test-fast      - Run tests without coverage (fastest)

Development:
  make lint           - Run linters (ruff, black)
  make format         - Format code with black and isort
  make type-check     - Run type checking with mypy
  make clean          - Clean up temporary files

Streamlit UI:
  make ui             - Start Streamlit UI dashboard only
  make ui-install     - Install UI dependencies

Installation:
  make install        - Install all dependencies
  make install-dev    - Install development dependencies

Documentation:
  make docs           - View documentation index
```

## 使用场景

### 场景 1：首次使用

```bash
# 1. 安装所有依赖
make install

# 2. 安装 UI 依赖
make ui-install

# 3. 启动完整平台（后端 + 前端）
make start-all
```

### 场景 2：仅开发后端

```bash
# 启动 MCP Server
make start
```

### 场景 3：仅开发前端 UI

```bash
# 确保后端已在另一个终端运行
# 然后启动 UI
make ui
```

### 场景 4：开发调试

```bash
# 快速测试（仅运行单元测试）
make dev

# 运行所有测试
make test

# 代码格式化
make format

# 代码检查
make lint
```

## 停止服务

在任何终端中按 `Ctrl+C` 即可停止所有服务。

## 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| Streamlit UI | http://localhost:8501 | Web 监控仪表板 |
| MCP Inspector | http://localhost:5173 | MCP 工具测试界面 |
| Langfuse Dashboard | https://cloud.langfuse.com | 可观测性数据平台 |

## 故障排查

### 问题 1：端口被占用

如果看到端口占用错误：

```bash
# 查找占用端口的进程
lsof -i :8501  # UI 端口
lsof -i :5173  # Inspector 端口

# 杀死进程
kill -9 <PID>
```

### 问题 2：依赖未安装

```bash
# 重新安装依赖
make install
make ui-install
```

### 问题 3：环境变量未配置

```bash
# 检查 .env 文件
cp .env.example .env
# 编辑 .env 填入实际的 API Keys
```

---

**最后更新**: 2026-04-30  
**版本**: v1.0
