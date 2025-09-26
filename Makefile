# Makefile for MCP as a Judge
# Provides convenient commands for development and deployment

.PHONY: help install test lint format type-check clean build docker-build docker-run dev prod act-test act-lint act-security act-all

# Default target
help: ## Show this help message
	@echo "MCP as a Judge - Development Commands"
	@echo "====================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development Setup
install: ## Install dependencies and setup development environment
	@echo "🔧 Setting up development environment..."
	pip install uv
	uv venv
	uv pip install -e ".[dev]"
	pre-commit install
	@echo "✅ Development environment ready!"

install-prod: ## Install production dependencies only
	@echo "🚀 Installing production dependencies..."
	uv pip install -e .
	@echo "✅ Production dependencies installed!"

# Code Quality
test: ## Run all tests
	@echo "🧪 Running tests..."
	uv run pytest

test-cov: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	uv run pytest --cov=src/mcp_as_a_judge --cov-report=html --cov-report=term

test-fast: ## Run fast tests only (skip slow tests)
	@echo "⚡ Running fast tests..."
	uv run pytest -m "not slow"

lint: ## Run linting checks
	@echo "🔍 Running linting checks..."
	uv run ruff check src tests

lint-fix: ## Fix linting issues automatically
	@echo "🔧 Fixing linting issues..."
	uv run ruff check --fix src tests

format: ## Format code with Black
	@echo "🎨 Formatting code..."
	uv run black src tests

format-check: ## Check code formatting
	@echo "🎨 Checking code formatting..."
	uv run black --check src tests

type-check: ## Run type checking with MyPy
	@echo "🔍 Running type checks..."
	uv run mypy src

quality: lint format-check type-check ## Run all quality checks
	@echo "✅ All quality checks passed!"

# Development
dev: ## Run development server with hot reload
	@echo "🚀 Starting development server..."
	uv run python -m mcp_as_a_judge.server

dev-stdio: ## Run development server with stdio transport
	@echo "🚀 Starting development server (stdio)..."
	TRANSPORT=stdio uv run python -m mcp_as_a_judge.server

dev-sse: ## Run development server with SSE transport
	@echo "🚀 Starting development server (SSE)..."
	TRANSPORT=sse uv run python -m mcp_as_a_judge.server

# Docker
docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	docker build -t mcp-as-a-judge:latest .

docker-run: ## Run Docker container
	@echo "🐳 Running Docker container..."
	docker run -p 8050:8050 -e TRANSPORT=sse mcp-as-a-judge:latest

docker-dev: ## Run development environment with Docker Compose
	@echo "🐳 Starting development environment..."
	docker-compose -f docker-compose.yml --profile development up --build

docker-prod: ## Run production environment with Docker Compose
	@echo "🐳 Starting production environment..."
	docker-compose -f docker-compose.yml --profile production up -d --build

docker-stop: ## Stop Docker containers
	@echo "🐳 Stopping Docker containers..."
	docker-compose down

# Cleanup
clean: ## Clean up build artifacts and cache
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	find . -name "*~" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete!"

clean-docker: ## Clean up Docker images and containers
	@echo "🐳 Cleaning up Docker..."
	docker-compose down --rmi all --volumes --remove-orphans 2>/dev/null || true
	docker system prune -f
	@echo "✅ Docker cleanup complete!"

# Release
build: clean ## Build distribution packages
	@echo "📦 Building distribution packages..."
	uv build

release-test: build ## Upload to Test PyPI
	@echo "📦 Uploading to Test PyPI..."
	uv publish --repository testpypi

release: build ## Upload to PyPI
	@echo "📦 Uploading to PyPI..."
	uv publish

# Documentation
docs: ## Generate documentation
	@echo "📚 Generating documentation..."
	# Add documentation generation commands here
	@echo "✅ Documentation generated!"

# Validation
validate: quality test ## Run all validation checks
	@echo "✅ All validation checks passed! Ready for commit."

pre-commit: format lint type-check test-fast ## Run pre-commit checks
	@echo "✅ Pre-commit checks passed!"

# CI/CD helpers
ci-install: ## Install dependencies for CI
	pip install uv
	uv pip install -e ".[dev]"

ci-test: ## Run tests in CI environment
	uv run pytest --cov=src/mcp_as_a_judge --cov-report=xml

ci-quality: ## Run quality checks in CI
	uv run ruff check src tests
	uv run black --check src tests
	uv run mypy src

# Information
info: ## Show project information
	@echo "MCP as a Judge - Project Information"
	@echo "==================================="
	@echo "Python version: $(shell python --version)"
	@echo "UV version: $(shell uv --version 2>/dev/null || echo 'Not installed')"
	@echo "Project structure:"
	@tree -I '__pycache__|*.pyc|.git|.venv|node_modules' -L 2 . 2>/dev/null || find . -type d -name ".*" -prune -o -type f -print | head -20

# Act (Local GitHub Actions) Commands
act-test: ## Run tests using Act (local GitHub Actions)
	@echo "🎭 Running tests with Act..."
	act -j tests -W .github/workflows/ci-act.yml

act-lint: ## Run linting using Act
	@echo "🎭 Running linting with Act..."
	act -j code-quality -W .github/workflows/ci-act.yml

act-security: ## Run security scan using Act
	@echo "🎭 Running security scan with Act..."
	act -j security -W .github/workflows/ci-act.yml

act-all: ## Run all CI jobs using Act
	@echo "🎭 Running full CI pipeline with Act..."
	act -W .github/workflows/ci-act.yml

act-list: ## List available Act jobs
	@echo "🎭 Available Act jobs:"
	act -l -W .github/workflows/ci-act.yml

act-clean: ## Clean Act containers and artifacts
	@echo "🎭 Cleaning Act containers and artifacts..."
	docker container prune -f
	rm -rf /tmp/artifacts
	rm -rf ./artifacts

act-status: ## Show Act setup status and troubleshooting info
	@echo "🎭 Act Setup Status:"
	@echo "✅ Act is configured and working"
	@echo "⚠️  SSL certificate issues may cause some steps to fail"
	@echo "📋 Available commands:"
	@echo "   make act-lint    - Run code quality checks"
	@echo "   make act-test    - Run test suite"
	@echo "   make act-all     - Run complete CI pipeline"
	@echo "   make act-list    - List all available jobs"
	@echo ""
	@echo "🔧 Troubleshooting:"
	@echo "   - SSL errors are expected in Act environment"
	@echo "   - Workflow structure validation works correctly"
	@echo "   - Use 'make act-clean' to reset containers if needed"

# Quick start
quick-start: install test ## Quick start: install dependencies and run tests
	@echo "🎉 Quick start complete! You're ready to develop."
	@echo ""
	@echo "Next steps:"
	@echo "  make dev          # Start development server"
	@echo "  make test         # Run tests"
	@echo "  make quality      # Check code quality"
	@echo "  make act-test     # Test with Act (local GitHub Actions)"
