# MCP Langfuse Observability - Makefile
# Quick commands for development and testing

.PHONY: help test test-unit test-integration test-cov test-html clean

# Default target
help:
	@echo "MCP Langfuse Observability - Available Commands"
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
	@echo "Documentation:"
	@echo "  make docs           - View documentation index"

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
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-xdist pytest-asyncio

install-dev:
	@echo "Installing development dependencies..."
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-xdist pytest-asyncio
	pip install black isort ruff mypy

# Quick test during development
dev:
	@echo "Quick test (unit tests only, no coverage)..."
	pytest tests/unit/ -v -n 2 --no-cov -x

# Watch mode (requires pytest-watch)
watch:
	@echo "Watching for changes..."
	ptw tests/unit/ --runner="pytest -v -n 2"
