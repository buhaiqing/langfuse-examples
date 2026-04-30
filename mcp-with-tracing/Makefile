# MCP Langfuse Observability - Makefile
# Quick commands for development and testing

.PHONY: help test test-unit test-integration test-cov test-html clean ui ui-install start start-all install install-dev

# Default target
help:
	@echo "MCP Langfuse Observability - Available Commands"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make start          - Start MCP Server only (backend)"
	@echo "  make start-all      - Start MCP Server + Streamlit UI (backend + frontend)"
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
	@echo "Streamlit UI:"
	@echo "  make ui             - Start Streamlit UI dashboard only"
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
	PYTHONPATH=. python run.py

# Quick Start - Start both MCP Server and Streamlit UI
start-all:
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "🚀 Starting MCP Langfuse Observability Platform..."
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "📋 Starting Components:"
	@echo "  ✓ Backend: MCP Server (FastMCP)"
	@echo "  ✓ Frontend: Streamlit UI Dashboard"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "🌐 Access Points:"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  📊 Streamlit UI Dashboard:"
	@echo "     → URL: http://localhost:8501"
	@echo "     → Features:"
	@echo "       • System health overview"
	@echo "       • Real-time metrics monitoring"
	@echo "       • Alert management"
	@echo "       • Feedback analysis"
	@echo "       • Prompt version management"
	@echo "       • System settings"
	@echo ""
	@echo "  🔌 MCP Server (Backend):"
	@echo "     → Transport: Stdio (JSON-RPC 2.0)"
	@echo "     → MCP Inspector: http://localhost:5173"
	@echo "     → Available Tools:"
	@echo "       • health_check"
	@echo "       • submit_feedback_accept"
	@echo "       • submit_feedback_reject"
	@echo "       • submit_feedback_rating"
	@echo "       • submit_feedback_comment"
	@echo ""
	@echo "  📈 Langfuse Dashboard:"
	@echo "     → URL: https://cloud.langfuse.com"
	@echo "     → View traces, sessions, and metrics"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "💡 Usage Tips:"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  • Both services will run in this terminal"
	@echo "  • Press Ctrl+C to stop all services"
	@echo "  • Open http://localhost:8501 for the UI dashboard"
	@echo "  • Use MCP Inspector to test backend tools"
	@echo "  • Check logs below for server activity"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "🔄 Starting services..."
	@echo ""
	@echo "─── Streamlit UI (Frontend) ─────────────────────────────────"
	@streamlit run ui/app.py --server.headless true --server.port 8501 &
	@sleep 2
	@echo ""
	@echo "─── MCP Server (Backend) ────────────────────────────────────"
	@PYTHONPATH=. python run.py
	@wait

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

# Streamlit UI commands
ui:
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "📊 Starting Streamlit UI Dashboard..."
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "🌐 Access Point:"
	@echo "  → URL: http://localhost:8501"
	@echo ""
	@echo "📋 Features:"
	@echo "  • System health overview"
	@echo "  • Real-time metrics monitoring"
	@echo "  • Alert management"
	@echo "  • Feedback analysis"
	@echo "  • Prompt version management"
	@echo "  • System settings"
	@echo ""
	@echo "💡 Tips:"
	@echo "  • Press Ctrl+C to stop the UI"
	@echo "  • The UI will auto-reload on code changes"
	@echo "  • Requires MCP Server to be running for data"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	streamlit run ui/app.py

ui-install:
	@echo "Installing Streamlit UI dependencies..."
	uv pip install -r ui/requirements.txt
	@echo "✅ UI dependencies installed successfully!"
