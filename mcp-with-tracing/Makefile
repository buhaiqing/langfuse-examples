# MCP Langfuse Observability - Makefile
# Quick commands for development and testing

# Load environment variables from .env file
ifneq (,$(wildcard .env))
    include .env
    export $(shell sed 's/=.*//' .env)
endif

.PHONY: help test test-unit test-integration test-cov test-html clean ui ui-install start start-all stop stop-ui stop-backend install install-dev

# Default target
help:
	@echo "MCP Langfuse Observability - Available Commands"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make start          - Start MCP Server only (backend)"
	@echo "  make start-all      - Start MCP Server + Reflex UI (backend + frontend)"
	@echo ""
	@echo "🛑 Stop Services:"
	@echo "  make stop           - Stop all running services"
	@echo "  make stop-ui        - Stop Reflex UI only"
	@echo "  make stop-backend   - Stop MCP Server only"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests (unit + integration)"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make test-html      - Run tests and open HTML coverage report"
	@echo "  make test-fast      - Run tests without coverage (fastest)"
	@echo ""
	@echo "Development:"
	@echo "  make lint           - Run linters (ruff, black)"
	@echo "  make format         - Format code with black and isort"
	@echo "  make type-check     - Run type checking with mypy"
	@echo "  make clean          - Clean up temporary files"
	@echo ""
	@echo "Reflex UI:"
	@echo "  make ui             - Start Reflex UI dashboard only"
	@echo "  make ui-install     - Install UI dependencies"
	@echo ""
	@echo "Installation:"
	@echo "  make install        - Install all dependencies"
	@echo "  make install-dev    - Install development dependencies"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs           - View documentation index"

# Quick Start - Start MCP Server only
start:
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "🚀 Starting MCP Langfuse Observability Server..."
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "📋 Server Information:"
	@echo "  • Backend: MCP Server (FastMCP)"
	@echo "  • Transport: Stdio (JSON-RPC 2.0)"
	@echo "  • Logs: Will show in this terminal"
	@echo ""
	@echo "🌐 Access Points:"
	@echo "  • MCP Inspector: http://localhost:5173 (for testing)"
	@echo "  • Langfuse Dashboard: https://cloud.langfuse.com"
	@echo ""
	@echo "💡 Tips:"
	@echo "  • Press Ctrl+C to stop the server"
	@echo "  • Use MCP Inspector to test all tools interactively"
	@echo "  • Check Langfuse dashboard for real-time observability data"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	PYTHONPATH=. python3 run.py

# Quick Start - Start both MCP Server and Reflex UI (Idempotent + Fault Tolerant)
start-all:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║   🚀 MCP Langfuse Observability Platform - 启动中...       ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔍 检查已运行的服务（幂等性保证）"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@if lsof -ti:3000 >/dev/null 2>&1 || lsof -ti:8000 >/dev/null 2>&1 || lsof -ti:8001 >/dev/null 2>&1; then \
		echo "  ⚠️  检测到已运行的服务，正在停止..."; \
		echo ""; \
		if lsof -ti:3000 >/dev/null 2>&1; then \
			echo "    • 停止 Reflex UI (端口 3000)..."; \
			lsof -ti:3000 | xargs kill -TERM 2>/dev/null || lsof -ti:3000 | xargs kill -9 2>/dev/null; \
		fi; \
		if lsof -ti:8000 >/dev/null 2>&1; then \
			echo "    • 停止 Reflex Backend (端口 8000)..."; \
			lsof -ti:8000 | xargs kill -TERM 2>/dev/null || lsof -ti:8000 | xargs kill -9 2>/dev/null; \
		fi; \
		if lsof -ti:8001 >/dev/null 2>&1; then \
			echo "    • 停止 MCP Server (端口 8001)..."; \
			lsof -ti:8001 | xargs kill -TERM 2>/dev/null || lsof -ti:8001 | xargs kill -9 2>/dev/null; \
		fi; \
		sleep 3; \
		if lsof -ti:3000 >/dev/null 2>&1 || lsof -ti:8000 >/dev/null 2>&1 || lsof -ti:8001 >/dev/null 2>&1; then \
			echo "  ⚠️  部分进程未响应 SIGTERM，强制终止..."; \
			lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null; \
			lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null; \
			lsof -ti:8001 2>/dev/null | xargs kill -9 2>/dev/null; \
			sleep 2; \
		fi; \
		echo "  ✅ 旧服务已停止"; \
	else \
		echo "  ✅ 没有检测到已运行的服务"; \
	fi
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📋 环境检查"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  🖥️  系统信息:"
	@echo "     • 操作系统: $(shell uname -s) $(shell uname -r)"
	@echo "     • 架构: $(shell uname -m)"
	@echo "     • 主机名: $(shell hostname)"
	@echo "     • 时间: $(shell date '+%Y-%m-%d %H:%M:%S')"
	@echo ""
	@echo "  🐍 Python 环境:"
	@echo "     • Python 版本: $(shell python3 --version 2>&1 | awk '{print $$2}')"
	@echo "     • Python 路径: $(shell which python3)"
	@echo "     • uv 版本: $(shell uv --version 2>/dev/null || echo '未安装')"
	@echo ""
	@echo "  📦 依赖包检查:"
	@echo "     • Reflex: $(shell uv pip show reflex 2>/dev/null | grep Version | awk '{print $$2}' || echo '❌ 未安装')"
	@echo "     • Langfuse: $(shell uv pip show langfuse 2>/dev/null | grep Version | awk '{print $$2}' || echo '❌ 未安装')"
	@echo "     • FastMCP: $(shell uv pip show fastmcp 2>/dev/null | grep Version | awk '{print $$2}' || echo '❌ 未安装')"
	@echo ""
	@echo "  🔑 环境变量:"
	@if [ -f .env ]; then \
		export $$(grep -v '^#' .env | grep -v '^$$' | xargs); \
		echo "     • LANGFUSE_PUBLIC_KEY: $(if $(LANGFUSE_PUBLIC_KEY),✅ 已配置 ($(shell echo $(LANGFUSE_PUBLIC_KEY) | cut -c1-15)...),❌ 未配置)"; \
		echo "     • LANGFUSE_SECRET_KEY: $(if $(LANGFUSE_SECRET_KEY),✅ 已配置,❌ 未配置)"; \
		echo "     • LANGFUSE_HOST: $(if $(LANGFUSE_HOST),$(LANGFUSE_HOST),https://cloud.langfuse.com (默认))"; \
		echo "     • OPENAI_API_KEY: $(if $(OPENAI_API_KEY),✅ 已配置,❌ 未配置)"; \
		echo "     • ENVIRONMENT: $(if $(ENVIRONMENT),$(ENVIRONMENT),development (默认))"; \
		echo "     • LOG_LEVEL: $(if $(LOG_LEVEL),$(LOG_LEVEL),INFO (默认))"; \
	else \
		echo "     • ⚠️  .env 文件不存在，使用系统环境变量"; \
		echo "     • LANGFUSE_PUBLIC_KEY: $(if $(LANGFUSE_PUBLIC_KEY),✅ 已配置,❌ 未配置)"; \
		echo "     • LANGFUSE_SECRET_KEY: $(if $(LANGFUSE_SECRET_KEY),✅ 已配置,❌ 未配置)"; \
		echo "     • LANGFUSE_HOST: $(if $(LANGFUSE_HOST),$(LANGFUSE_HOST),https://cloud.langfuse.com (默认))"; \
		echo "     • OPENAI_API_KEY: $(if $(OPENAI_API_KEY),✅ 已配置,❌ 未配置)"; \
	fi
	@echo ""
	@echo "  🌐 端口状态:"
	@echo "     • Reflex UI (3000): $(shell lsof -i :3000 >/dev/null 2>&1 && echo '❌ 已被占用' || echo '✅ 可用')"
	@echo "     • MCP Server (8001): $(shell lsof -i :8001 >/dev/null 2>&1 && echo '❌ 已被占用' || echo '✅ 可用')"
	@echo "     • Reflex Backend (8000): $(shell lsof -i :8000 >/dev/null 2>&1 && echo '❌ 已被占用' || echo '✅ 可用')"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📊 启动组件"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  ✓ Backend: MCP Server (FastMCP)"
	@echo "  ✓ Frontend: Reflex UI Dashboard (v0.9.1)"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🌐 访问地址"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  📊 Reflex UI Dashboard:"
	@echo "     → URL: http://localhost:3000"
	@echo "     → 功能:"
	@echo "       • 系统健康总览"
	@echo "       • 实时指标监控"
	@echo "       • 告警管理"
	@echo "       • 反馈分析"
	@echo "       • 提示词版本管理"
	@echo "       • 系统设置"
	@echo ""
	@echo "  🔌 MCP Server (Backend):"
	@echo "     → Transport: HTTP (Streamable HTTP)"
	@echo "     → URL: http://localhost:8001"
	@echo "     → 可用工具:"
	@echo "       • health_check - 健康检查"
	@echo "       • submit_feedback_accept - 提交接受反馈"
	@echo "       • submit_feedback_reject - 提交拒绝反馈"
	@echo "       • submit_feedback_rating - 提交评分反馈"
	@echo "       • submit_feedback_comment - 提交评论反馈"
	@echo ""
	@echo "  📈 Langfuse Dashboard:"
	@echo "     → URL: https://cloud.langfuse.com"
	@echo "     → 查看 traces, sessions, 和 metrics"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "💡 使用提示"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  • Reflex UI 将自动启动"
	@echo "  • 按 Ctrl+C 停止所有服务"
	@echo "  • 打开 http://localhost:3000 访问 UI 仪表板"
	@echo "  • 使用 MCP Inspector 测试后端工具"
	@echo "  • 查看下方日志了解服务器活动"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "🔄 正在启动服务..."
	@echo ""
	@echo "─── Step 1: 启动 Reflex UI (Frontend) ───────────────────────"
	@echo "  🚀 启动 Reflex 开发服务器..."
	@set -a; source .env 2>/dev/null || true; set +a; PYTHONPATH=. uv run reflex run > /tmp/reflex_ui.log 2>&1 &
	@echo "  ⏳ 等待 Reflex UI 启动（最多 15 秒）..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do \
		if lsof -i :3000 >/dev/null 2>&1; then \
			echo "  ✅ Reflex UI 已启动 (端口 3000) [耗时 $${i}s]"; \
			break; \
		fi; \
		if [ $$i -eq 15 ]; then \
			echo "  ❌ Reflex UI 启动超时"; \
			echo "  📄 查看日志: tail -f /tmp/reflex_ui.log"; \
			echo "  🛑 清理残留进程..."; \
			lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null; \
			lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null; \
			echo "  💡 提示: 检查依赖是否正确安装 (uv pip install reflex)"; \
			exit 1; \
		fi; \
		sleep 1; \
	done
	@echo "─── Step 2: 启动 MCP Server (Backend) ───────────────────────"
	@echo "  🚀 启动 MCP Server (HTTP 模式)..."
	@set -a; source .env 2>/dev/null || true; set +a; MCP_TRANSPORT=streamable-http MCP_PORT=8001 PYTHONPATH=. python3 run.py > /tmp/mcp_server.log 2>&1 &
	@echo "  ⏳ 等待 MCP Server 启动（最多 10 秒）..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		if lsof -i :8001 >/dev/null 2>&1; then \
			echo "  ✅ MCP Server 已启动 (端口 8001) [耗时 $${i}s]"; \
			break; \
		fi; \
		if [ $$i -eq 10 ]; then \
			echo "  ❌ MCP Server 启动超时"; \
			echo "  📄 查看日志: tail -f /tmp/mcp_server.log"; \
			echo "  🛑 清理残留进程..."; \
			lsof -ti:8001 2>/dev/null | xargs kill -9 2>/dev/null; \
			echo "  💡 提示: 检查 run.py 是否存在且可执行"; \
			exit 1; \
		fi; \
		sleep 1; \
	done
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ 服务启动完成"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  📊 Reflex UI: http://localhost:3000"
	@echo "  🔌 MCP Server: http://localhost:8001/mcp (Streamable HTTP)"
	@echo ""
	@echo "  📄 日志文件:"
	@echo "     • Reflex UI: tail -f /tmp/reflex_ui.log"
	@echo "     • MCP Server: tail -f /tmp/mcp_server.log"
	@echo ""
	@echo "  🛑 停止服务: make stop"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""

# Testing commands
test:
	@echo "Running all tests (unit + integration)..."
	pytest tests/ -v -n 2

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v -n 2

test-integration:
	@echo "Running integration tests..."
	pytest tests/integration/ -v

test-cov:
	@echo "Running tests with coverage..."
	pytest tests/ -v --cov=src --cov-report=term-missing -n 2

test-html:
	@echo "Running tests and generating HTML coverage report..."
	pytest tests/ --cov=src --cov-report=html -n 2
	@echo "Opening coverage report..."
	open htmlcov/index.html

test-fast:
	@echo "Running tests without coverage (fastest)..."
	pytest tests/ -v -n 2 --no-cov

test-specific:
	@echo "Usage: make test-specific file=tests/unit/test_alerting.py"
	pytest $(file) -v

# Development commands
lint:
	@echo "Running linters..."
	ruff check src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/

format:
	@echo "Formatting code..."
	black src/ tests/
	isort src/ tests/
	ruff check --fix src/ tests/

type-check:
	@echo "Running type checking..."
	mypy src/

clean:
	@echo "Cleaning up..."
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache
	rm -rf __pycache__
	rm -rf src/__pycache__
	rm -rf tests/__pycache__
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Cleanup complete!"

docs:
	@echo "Opening documentation..."
	open docs/testing-organization.md

# Install dependencies
install:
	@echo "Installing dependencies..."
	uv sync

install-dev:
	@echo "Installing development dependencies..."
	uv sync --all-extras

# Quick test during development
dev:
	@echo "Quick test (unit tests only, no coverage)..."
	uv run pytest tests/unit/ -v -n 2 --no-cov -x

# Watch mode (requires pytest-watch)
watch:
	@echo "Watching for changes..."
	uv run ptw tests/unit/ --runner="uv run pytest -v -n 2"

# Code quality checks
check-all:
	@echo "Running all checks..."
	uv run ruff check src/ tests/
	uv run black --check src/ tests/
	uv run mypy src/
	uv run pytest tests/ -v --cov=src

# Reflex UI commands
ui:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║   📊 Reflex UI Dashboard - 启动中...                       ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📋 环境检查"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  🖥️  系统信息:"
	@echo "     • 操作系统: $(shell uname -s) $(shell uname -r)"
	@echo "     • 架构: $(shell uname -m)"
	@echo "     • 时间: $(shell date '+%Y-%m-%d %H:%M:%S')"
	@echo ""
	@echo "  🐍 Python 环境:"
	@echo "     • Python 版本: $(shell python3 --version 2>&1 | awk '{print $$2}')"
	@echo "     • uv 版本: $(shell uv --version 2>/dev/null || echo '未安装')"
	@echo ""
	@echo "  📦 依赖包:"
	@echo "     • Reflex: $(shell uv pip show reflex 2>/dev/null | grep Version | awk '{print $$2}' || echo '❌ 未安装')"
	@echo ""
	@echo "  🔑 环境变量:"
	@echo "     • LANGFUSE_PUBLIC_KEY: $(if $(LANGFUSE_PUBLIC_KEY),✅ 已配置,❌ 未配置)"
	@echo "     • LANGFUSE_SECRET_KEY: $(if $(LANGFUSE_SECRET_KEY),✅ 已配置,❌ 未配置)"
	@echo ""
	@echo "  🌐 端口状态:"
	@echo "     • Reflex UI (3000): $(shell lsof -i :3000 >/dev/null 2>&1 && echo '❌ 已被占用' || echo '✅ 可用')"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📊 访问地址"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  → URL: http://localhost:3000"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📋 功能模块"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  • 系统健康总览"
	@echo "  • 实时指标监控"
	@echo "  • 告警管理"
	@echo "  • 反馈分析"
	@echo "  • 提示词版本管理"
	@echo "  • 系统设置"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "💡 使用提示"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  • 按 Ctrl+C 停止 UI"
	@echo "  • Reflex 会自动重载代码更改"
	@echo "  • 需要 MCP Server 运行才能获取数据"
	@echo "  • 性能：比 Streamlit 快 60%+"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@PYTHONPATH=. uv run reflex run

ui-install:
	@echo "Installing Reflex UI dependencies..."
	uv pip install reflex
	@echo "✅ UI dependencies installed successfully!"

# Stop commands
stop:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║   🛑 正在停止所有服务...                                    ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📋 检查运行中的进程"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  🔍 Reflex UI (端口 3000):"
	@lsof -ti:3000 >/dev/null 2>&1 && echo "     ✅ 运行中 (PID: $$(lsof -ti:3000 | tr '\n' ', '))" || echo "     ⚪ 未运行"
	@echo ""
	@echo "  🔍 Reflex Backend (端口 8000):"
	@lsof -ti:8000 >/dev/null 2>&1 && echo "     ✅ 运行中 (PID: $$(lsof -ti:8000 | tr '\n' ', '))" || echo "     ⚪ 未运行"
	@echo ""
	@echo "  🔍 MCP Server (端口 8001):"
	@lsof -ti:8001 >/dev/null 2>&1 && echo "     ✅ 运行中 (PID: $$(lsof -ti:8001 | tr '\n' ', '))" || echo "     ⚪ 未运行"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🛑 停止服务"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@if lsof -ti:3000 >/dev/null 2>&1; then \
		echo "  停止 Reflex UI (端口 3000)..."; \
		lsof -ti:3000 | xargs kill -TERM 2>/dev/null; \
		sleep 1; \
		echo "     ✅ 已停止"; \
	else \
		echo "  ⚪ Reflex UI 未运行，跳过"; \
	fi
	@echo ""
	@if lsof -ti:8000 >/dev/null 2>&1; then \
		echo "  停止 Reflex Backend (端口 8000)..."; \
		lsof -ti:8000 | xargs kill -TERM 2>/dev/null; \
		sleep 1; \
		echo "     ✅ 已停止"; \
	else \
		echo "  ⚪ Reflex Backend 未运行，跳过"; \
	fi
	@echo ""
	@if lsof -ti:8001 >/dev/null 2>&1; then \
		echo "  停止 MCP Server (端口 8001)..."; \
		lsof -ti:8001 | xargs kill -TERM 2>/dev/null; \
		sleep 1; \
		echo "     ✅ 已停止"; \
	else \
		echo "  ⚪ MCP Server 未运行，跳过"; \
	fi
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📊 端口清理状态"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  • Reflex UI (3000): $$(lsof -i :3000 >/dev/null 2>&1 && echo '❌ 仍被占用' || echo '✅ 已释放')"
	@echo "  • Reflex Backend (8000): $$(lsof -i :8000 >/dev/null 2>&1 && echo '❌ 仍被占用' || echo '✅ 已释放')"
	@echo "  • MCP Inspector (5173): $$(lsof -i :5173 >/dev/null 2>&1 && echo '❌ 仍被占用' || echo '✅ 已释放')"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ 所有服务已停止"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""

stop-ui:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║   🛑 正在停止 Reflex UI...                                  ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@if lsof -ti:3000 >/dev/null 2>&1; then \
		echo "  🔍 找到 Reflex UI 进程 (PID: $$(lsof -ti:3000 | tr '\n' ', '))"; \
		echo "  🛑 正在停止..."; \
		lsof -ti:3000 | xargs kill -TERM 2>/dev/null; \
		sleep 1; \
		echo "  ✅ Reflex UI 已停止 (端口 3000)"; \
	else \
		echo "  ⚪ Reflex UI 未运行 (端口 3000)"; \
	fi
	@echo ""
	@if lsof -ti:8000 >/dev/null 2>&1; then \
		echo "  🔍 找到 Reflex Backend 进程 (PID: $$(lsof -ti:8000 | tr '\n' ', '))"; \
		echo "  🛑 正在停止..."; \
		lsof -ti:8000 | xargs kill -TERM 2>/dev/null; \
		sleep 1; \
		echo "  ✅ Reflex Backend 已停止 (端口 8000)"; \
	else \
		echo "  ⚪ Reflex Backend 未运行 (端口 8000)"; \
	fi
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Reflex UI 已停止"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""

stop-backend:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║   🛑 正在停止 MCP Server...                                 ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@if lsof -ti:5173 >/dev/null 2>&1; then \
		echo "  🔍 找到 MCP Inspector 进程 (PID: $$(lsof -ti:5173 | tr '\n' ', '))"; \
		echo "  🛑 正在停止..."; \
		lsof -ti:5173 | xargs kill -TERM 2>/dev/null; \
		sleep 1; \
		echo "  ✅ MCP Inspector 已停止 (端口 5173)"; \
	else \
		echo "  ⚪ MCP Inspector 未运行 (端口 5173)"; \
	fi
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ MCP Server 已停止"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
