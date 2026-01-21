.PHONY: help install install-uv install-poetry run backend frontend test lint format clean

# Default Python version
PYTHON := python3.14
VENV_PYTHON := .venv/bin/python

# Detect if we're using uv, poetry, or pip
HAS_UV := $(shell command -v uv 2> /dev/null)
HAS_POETRY := $(shell command -v poetry 2> /dev/null)

help: ## Show this help message
	@echo "Finance Analysis - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation commands

install-uv: ## Install dependencies using uv (recommended)
	@echo "Installing with uv..."
	@if [ -z "$(HAS_UV)" ]; then \
		echo "uv not found. Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi
	uv venv --python $(PYTHON)
	@echo "Activate with: source .venv/bin/activate"
	@echo "Then run: uv pip install -e . --group dev"

install-poetry: ## Install dependencies using Poetry
	@echo "Installing with Poetry..."
	@if [ -z "$(HAS_POETRY)" ]; then \
		echo "Poetry not found. Install from: https://python-poetry.org/docs/#installation"; \
		exit 1; \
	fi
	poetry config virtualenvs.in-project true
	poetry install --with dev

install: ## Auto-detect and install (tries uv, then poetry, then pip)
	@if [ -n "$(HAS_UV)" ]; then \
		echo "Using uv..."; \
		uv venv --python $(PYTHON) && uv pip install -e . --group dev; \
	elif [ -n "$(HAS_POETRY)" ]; then \
		echo "Using Poetry..."; \
		poetry install --with dev; \
	else \
		echo "Using pip..."; \
		$(PYTHON) -m venv .venv && \
		. .venv/bin/activate && \
		pip install -e ".[dev]"; \
	fi

# Running commands

run: ## Run both backend and frontend
	@if [ -f $(VENV_PYTHON) ]; then \
		$(VENV_PYTHON) run.py; \
	else \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi

backend: ## Run backend only
	@if [ -f $(VENV_PYTHON) ]; then \
		. .venv/bin/activate && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi

frontend: ## Run frontend only
	@if [ -f $(VENV_PYTHON) ]; then \
		. .venv/bin/activate && streamlit run frontend/app.py --server.port 8501; \
	else \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi

# Development commands

test: ## Run tests with pytest
	@. .venv/bin/activate && pytest tests/ -v --cov=backend --cov=frontend --cov-report=html

test-watch: ## Run tests in watch mode
	@. .venv/bin/activate && pytest-watch tests/ -v

lint: ## Run linter (ruff)
	@. .venv/bin/activate && ruff check .

lint-fix: ## Fix linting issues automatically
	@. .venv/bin/activate && ruff check --fix .

format: ## Format code with black
	@. .venv/bin/activate && black .
	@. .venv/bin/activate && ruff check --fix .

type-check: ## Run type checker (mypy)
	@. .venv/bin/activate && mypy backend/ frontend/

# Quality checks

check: lint type-check test ## Run all checks (lint, type-check, test)

# Database commands

db-reset: ## Reset database (delete and recreate)
	rm -f data/finance.db
	@echo "Database reset. It will be recreated on next run."

# Cleanup commands

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/

clean-all: clean ## Clean everything including venv
	rm -rf .venv/
	rm -f uv.lock poetry.lock

# Development setup

setup: ## Full setup (install + configure)
	@echo "Setting up Finance Analysis project..."
	@$(MAKE) install
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file. Please add your ANTHROPIC_API_KEY"; \
	fi
	@echo ""
	@echo "Setup complete! Next steps:"
	@echo "1. Edit .env and add your ANTHROPIC_API_KEY"
	@echo "2. Run: make run"

# Update commands

update: ## Update all dependencies
	@if [ -n "$(HAS_UV)" ]; then \
		uv pip install --upgrade -e ".[dev]"; \
	elif [ -n "$(HAS_POETRY)" ]; then \
		poetry update; \
	else \
		pip install --upgrade -e ".[dev]"; \
	fi

# Lock files

lock: ## Generate lock file for reproducibility
	@if [ -n "$(HAS_UV)" ]; then \
		uv pip compile pyproject.toml -o requirements.lock; \
	elif [ -n "$(HAS_POETRY)" ]; then \
		poetry lock; \
	else \
		pip freeze > requirements.txt; \
	fi

# Info commands

info: ## Show project information
	@echo "Project: Finance Analysis"
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Location: $(shell pwd)"
	@if [ -n "$(HAS_UV)" ]; then \
		echo "Package Manager: uv $(shell uv --version)"; \
	elif [ -n "$(HAS_POETRY)" ]; then \
		echo "Package Manager: Poetry $(shell poetry --version)"; \
	else \
		echo "Package Manager: pip $(shell pip --version)"; \
	fi
	@echo ""
	@if [ -d .venv ]; then \
		echo "Virtual Environment: ✅ Active"; \
	else \
		echo "Virtual Environment: ❌ Not found"; \
	fi
	@if [ -f .env ]; then \
		echo "Environment File: ✅ Found"; \
	else \
		echo "Environment File: ❌ Not found (copy .env.example)"; \
	fi

# Docker commands (future)

docker-build: ## Build Docker image
	docker build -t finance-analysis .

docker-run: ## Run in Docker container
	docker run -p 8000:8000 -p 8501:8501 finance-analysis

# Documentation

docs: ## Open documentation in browser
	@open README.md || xdg-open README.md || start README.md
