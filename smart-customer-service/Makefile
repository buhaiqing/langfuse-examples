.PHONY: help install install-dev update clean run-test run-basic run-demo run-verify lint format type-check check-all setup dotenv build

# Default target
help:
	@echo "Langfuse Smart Customer Service - Makefile Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Initial project setup (create .env, install dependencies)"
	@echo "  make install        - Install production dependencies with uv"
	@echo "  make install-dev    - Install development dependencies with uv"
	@echo "  make update         - Update dependencies to latest versions"
	@echo "  make dotenv         - Create .env file from template"
	@echo ""
	@echo "Development:"
	@echo "  make lint           - Run linters (ruff)"
	@echo "  make format         - Format code (black + ruff)"
	@echo "  make type-check     - Run type checker (mypy)"
	@echo "  make check-all      - Run all checks (lint + format + type-check + test)"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests with pytest"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make test-watch     - Run tests in watch mode"
	@echo ""
	@echo "Running Examples:"
	@echo "  make verify         - Verify project setup"
	@echo "  make run-basic      - Run basic tracing example"
	@echo "  make run-demo       - Run full customer service demo"
	@echo "  make run-tech       - Run tech support demo"
	@echo "  make run-failure    - Run failure analysis demo"
	@echo "  make run-dashboard  - Run dashboard example"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Remove cache files and build artifacts"
	@echo "  make clean-all      - Remove everything including .venv"
	@echo ""
	@echo "Build:"
	@echo "  make build          - Build package distribution"

# Setup & Installation
setup: dotenv install-dev
	@echo ""
	@echo "✓ Project setup complete!"
	@echo "  1. Edit .env file with your API keys"
	@echo "  2. Run: make verify"

install:
	@echo "Installing production dependencies with uv..."
	uv sync --no-dev

install-dev:
	@echo "Installing development dependencies with uv..."
	uv sync

update:
	@echo "Updating dependencies to latest versions..."
	uv lock --upgrade

dotenv:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env file from template"; \
		echo "⚠️  Please edit .env with your API keys"; \
	else \
		echo ".env file already exists"; \
	fi

# Development Tools
lint:
	@echo "Running linters..."
	uv run ruff check .

format:
	@echo "Formatting code..."
	uv run black .
	uv run ruff check . --fix

type-check:
	@echo "Running type checker..."
	uv run mypy .

check-all: lint format type-check test
	@echo ""
	@echo "✓ All checks passed!"

# Testing
test:
	@echo "Running tests..."
	uv run pytest backend/tests/

test-cov:
	@echo "Running tests with coverage..."
	uv run pytest backend/tests/ --cov=. --cov-report=term-missing --cov-report=html

test-watch:
	@echo "Running tests in watch mode (Ctrl+C to exit)..."
	uv run ptw backend/tests/

# Running Examples
verify:
	@echo "Verifying project setup..."
	uv run python backend/verify_setup.py

run-basic:
	@echo "Running basic tracing example..."
	uv run python backend/examples/basic_tracing.py

run-demo:
	@echo "Running full customer service demo..."
	uv run python backend/main.py

run-tech:
	@echo "Running tech support demo..."
	uv run python backend/examples/tech_support_demo.py

run-failure:
	@echo "Running failure analysis demo..."
	uv run python backend/examples/failure_analysis_demo.py

run-dashboard:
	@echo "Running dashboard example..."
	uv run python backend/examples/dashboard_example.py

# Maintenance
clean:
	@echo "Cleaning cache files..."
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	@echo "✓ Cleaned cache files"

clean-all: clean
	@echo "Removing virtual environment..."
	rm -rf .venv
	rm -rf uv.lock
	@echo "✓ Cleaned everything"

# Build
build:
	@echo "Building package..."
	uv build
	@echo ""
	@echo "✓ Package built successfully!"
	@echo "  Distribution files are in dist/"
