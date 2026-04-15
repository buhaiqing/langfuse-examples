.PHONY: help install install-dev update clean run-test run-basic run-demo run-verify lint format type-check check-all setup dotenv build docker-up docker-down docker-logs docker-restart redis-cli postgres-cli db-migrate db-init minio-init test-e2e test-e2e-user test-e2e-agent test-e2e-api test-e2e-integration

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
	@echo "  make test-e2e       - Run E2E tests (requires backend running)"
	@echo "  make test-e2e-user  - Run E2E user flow tests"
	@echo "  make test-e2e-agent - Run E2E agent flow tests"
	@echo "  make test-e2e-api   - Run E2E API tests"
	@echo "  make test-e2e-integration - Run E2E integration tests"
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

# E2E Testing (requires backend running)
test-e2e:
	@echo "Running E2E tests..."
	@echo "⚠️  Requires backend running at http://localhost:8000"
	uv run python tests/e2e/run_tests.py --type all

test-e2e-user:
	@echo "Running E2E user flow tests..."
	uv run python tests/e2e/run_tests.py --type user

test-e2e-agent:
	@echo "Running E2E agent flow tests..."
	uv run python tests/e2e/run_tests.py --type agent

test-e2e-api:
	@echo "Running E2E API tests..."
	uv run python tests/e2e/run_tests.py --type api

test-e2e-integration:
	@echo "Running E2E integration tests..."
	uv run python tests/e2e/run_tests.py --type integration

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

# Docker Commands
docker-up:
	@echo "Starting Docker containers..."
	docker-compose up -d
	@echo "✓ Containers started"
	@echo "  API: http://localhost:8000"
	@echo "  Redis: localhost:6379"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  ChromaDB: localhost:8001"
	@echo "  MinIO Console: http://localhost:9001"

docker-down:
	@echo "Stopping Docker containers..."
	docker-compose down
	@echo "✓ Containers stopped"

docker-logs:
	@echo "Showing container logs..."
	docker-compose logs -f

docker-restart: docker-down docker-up

redis-cli:
	@echo "Connecting to Redis..."
	docker exec -it smart-cs-redis redis-cli

postgres-cli:
	@echo "Connecting to PostgreSQL..."
	docker exec -it smart-cs-postgres psql -U postgres -d smart_cs

db-migrate:
	@echo "Running database migrations..."
	uv run alembic upgrade head

db-init: docker-up
	@echo "Initializing databases..."
	@sleep 5
	@echo "✓ Databases initialized"

minio-init:
	@echo "Creating MinIO bucket..."
	@echo "Bucket: smart-cs-archives"
	@echo "✓ MinIO initialized"

# Quick Start
quick-start: setup docker-up db-init
	@echo ""
	@echo "✓ Quick start complete!"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  Health Check: http://localhost:8000/health"
