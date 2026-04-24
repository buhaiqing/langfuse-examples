# skill-observability-toolkit Makefile

.PHONY: help install test lint type-check format check-all clean

help:
	@echo "skill-observability-toolkit Development Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install         Install dependencies"
	@echo "  test            Run all tests"
	@echo "  test-cov        Run tests with coverage report"
	@echo "  lint            Run ruff linter"
	@echo "  type-check      Run mypy type checking"
	@echo "  format          Format code with black"
	@echo "  check-all       Run lint + type-check + test"
	@echo "  clean           Clean up build artifacts"

install:
	@echo "Installing dependencies..."
	pip install -e "."
	pip install -e ".[dev]"
	@echo "Dependencies installed successfully!"

test:
	@echo "Running tests..."
	pytest tests/ -v

test-cov:
	@echo "Running tests with coverage..."
	pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	@echo "Running linter..."
	ruff check src/ tests/

type-check:
	@echo "Running type checker..."
	mypy src/

format:
	@echo "Formatting code..."
	black src/ tests/

check-all: lint test
	@echo "All checks passed!"

clean:
	@echo "Cleaning up..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .hypothesis/
	rm -rf .mypy_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup complete!"
