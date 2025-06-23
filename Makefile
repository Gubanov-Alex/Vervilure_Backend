# Vervilure Backend - Modern Makefile
# =================================

# Variables
SHELL := /bin/bash
.DEFAULT_GOAL := help

# Export user IDs for Docker
export USER_ID := $(shell id -u)
export GROUP_ID := $(shell id -g)

# Docker compose command with proper env
DC := USER_ID=$(USER_ID) GROUP_ID=$(GROUP_ID) docker-compose
DC_RUN := $(DC) run --rm
DC_EXEC := $(DC) exec

# Python commands
PYTHON := python
MANAGE := $(PYTHON) manage.py
POETRY := poetry run

# Colors for output
YELLOW := \033[0;33m
GREEN := \033[0;32m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Main targets
.PHONY: help
help: ## Show this help message
	@echo -e "$(GREEN)Vervilure Backend - Docker Management$(NC)"
	@echo -e "Current user: UID=$(USER_ID), GID=$(GROUP_ID)\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# === DOCKER LIFECYCLE ===
.PHONY: build
build: ## Build Docker images
	@echo -e "$(YELLOW)Building Docker images...$(NC)"
	$(DC) build

.PHONY: up
up: ## Start all core services
	@echo -e "$(YELLOW)Starting services...$(NC)"
	$(DC) up -d db redis web celery
	@echo -e "$(GREEN)Services started!$(NC)"
	@echo "  Web: http://localhost:8000"
	@echo "  DB:  localhost:5490"
	@echo "  Redis: localhost:6390"

.PHONY: down
down: ## Stop all services
	$(DC) down --remove-orphans

.PHONY: restart
restart: down up ## Restart all services

.PHONY: ps
ps: ## Show running containers
	$(DC) ps

.PHONY: logs
logs: ## Follow logs for all services
	$(DC) logs -f --tail=100

.PHONY: logs-%
logs-%: ## Follow logs for specific service (e.g., make logs-web)
	$(DC) logs -f --tail=100 $*

# === DJANGO MANAGEMENT ===
.PHONY: manage
manage: ## Run Django manage.py command (e.g., make manage cmd="showmigrations")
	$(DC_EXEC) web $(POETRY) $(MANAGE) $(cmd)

.PHONY: shell
shell: ## Open Django shell_plus
	$(DC_EXEC) web $(POETRY) $(MANAGE) shell_plus || $(DC_EXEC) web $(POETRY) $(MANAGE) shell

.PHONY: migrate
migrate: ## Run database migrations
	@echo -e "$(YELLOW)Running migrations...$(NC)"
	$(DC_EXEC) web $(POETRY) $(MANAGE) migrate

.PHONY: makemigrations
makemigrations: ## Create new migrations
	$(DC_EXEC) web $(POETRY) $(MANAGE) makemigrations

.PHONY: showmigrations
showmigrations: ## Show migration status
	$(DC_EXEC) web $(POETRY) $(MANAGE) showmigrations

.PHONY: createsuperuser
createsuperuser: ## Create Django superuser
	$(DC_EXEC) web $(POETRY) $(MANAGE) createsuperuser

.PHONY: collectstatic
collectstatic: ## Collect static files
	$(DC_EXEC) web $(POETRY) $(MANAGE) collectstatic --noinput

# === TESTING ===
.PHONY: test
test: ## Run all tests
	$(DC_EXEC) web $(POETRY) pytest -v

.PHONY: test-fast
test-fast: ## Run tests without migrations
	$(DC_EXEC) web $(POETRY) pytest -v --reuse-db --no-migrations

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	$(DC_EXEC) web $(POETRY) pytest --cov=. --cov-report=html --cov-report=term-missing

.PHONY: test-file
test-file: ## Run specific test file (e.g., make test-file path=apps/users/tests/test_models.py)
	$(DC_EXEC) web $(POETRY) pytest -v $(path)

# === CODE QUALITY ===
.PHONY: setup-format-env
setup-format-env: ## Setup formatting environment with proper permissions
	@echo -e "$(YELLOW)Setting up formatting environment...$(NC)"
	@$(DC_EXEC) web bash -c " \
		rm -rf /app/.ruff_cache && \
		mkdir -p /tmp/ruff_cache && \
		chmod 777 /tmp/ruff_cache && \
		mkdir -p /app/.ruff_cache && \
		chown django:django /app/.ruff_cache && \
		chmod 755 /app/.ruff_cache \
	"

.PHONY: lint
lint: ## Run all linters
	@echo -e "$(YELLOW)Running linters...$(NC)"
	@echo -e "$(BLUE)Running ruff...$(NC)"
	$(DC_EXEC) web $(POETRY) ruff check . --cache-dir /tmp/ruff_cache
	@echo -e "$(BLUE)Running mypy...$(NC)"
	$(DC_EXEC) web $(POETRY) mypy .
	@echo -e "$(GREEN)Linting complete!$(NC)"

.PHONY: lint-fix
lint-fix: ## Run linters with auto-fix
	@echo -e "$(YELLOW)Running linters with fixes...$(NC)"
	@$(MAKE) setup-format-env
	$(DC_EXEC) web $(POETRY) ruff check . --fix --cache-dir /tmp/ruff_cache
	$(DC_EXEC) web $(POETRY) mypy .

.PHONY: format
format:
	@echo "Formatting code..."
	poetry run black .
	poetry run isort .



.PHONY: format-check
format-check: ## Check if code is properly formatted
	@echo -e "$(YELLOW)Checking code formatting...$(NC)"
	$(DC_EXEC) web $(POETRY) black --check .
	$(DC_EXEC) web $(POETRY) isort --check-only .


.PHONY: check
check: ## Run all checks (tests, linting, etc.)
	@make lint
	@make test

# === GOOGLE OAUTH MANAGEMENT ===
.PHONY: cleanup-oauth-duplicates
cleanup-oauth-duplicates: ## Clean up duplicate Google OAuth configurations
	@echo "Cleaning up duplicate Google OAuth configurations..."
	$(DC_EXEC) web $(POETRY) $(MANAGE) cleanup_oauth_duplicates

.PHONY: cleanup-oauth-duplicates-dry
cleanup-oauth-duplicates-dry: ## Check for duplicate Google OAuth configurations
	@echo "Checking for duplicate Google OAuth configurations..."
	$(DC_EXEC) web $(POETRY) $(MANAGE) cleanup_oauth_duplicates --dry-run

.PHONY: test-google-oauth-clean
test-google-oauth-clean: ## Clean OAuth duplicates and run tests
	@echo "Cleaning OAuth duplicates and running tests..."
	@$(MAKE) cleanup-oauth-duplicates
	@$(MAKE) test-google-oauth

.PHONY: setup-mailpit
setup-mailpit: ## Setup Mailpit and OAuth
	@echo "Setting up Mailpit and OAuth..."
	@$(MAKE) up
	@sleep 5
	$(DC_EXEC) web $(POETRY) $(MANAGE) setup_oauth
	@echo "Mailpit UI: http://localhost:8025"
	@echo "Admin: http://localhost:8000/admin/"

.PHONY: test-email
test-email: ## Test email configuration
	$(DC_EXEC) web $(POETRY) $(MANAGE) test_email

# === AUTHENTICATION JWT TESTING ===
.PHONY: test-jwt-auth
test-jwt-auth: ## Run JWT authentication flow tests
	@echo "Running JWT authentication flow tests..."
	$(DC_EXEC) web $(POETRY) $(MANAGE) test_jwt_auth_flow --verbose

.PHONY: test-jwt-auth-quick
test-jwt-auth-quick: ## Run JWT authentication tests (no cleanup)
	@echo "Running JWT authentication tests (no cleanup)..."
	$(DC_EXEC) web $(POETRY) $(MANAGE) test_jwt_auth_flow --skip-cleanup

# === GOOGLE OAUTH TESTING ===
.PHONY: test-google-oauth
test-google-oauth: ## Run Google OAuth authentication tests
	@echo "Running Google OAuth authentication tests..."
	$(DC_EXEC) web $(POETRY) $(MANAGE) test_google_oauth --verbose

.PHONY: test-google-oauth-quick
test-google-oauth-quick: ## Run Google OAuth tests (no cleanup)
	@echo "Running Google OAuth tests (no cleanup)..."
	$(DC_EXEC) web $(POETRY) $(MANAGE) test_google_oauth --skip-cleanup

.PHONY: mailpit-logs
mailpit-logs: ## Show Mailpit logs
	$(DC) logs mailpit

# === DATABASE ===
.PHONY: dbshell
dbshell: ## Open PostgreSQL shell
	$(DC_EXEC) db psql -U admin -d test_db

.PHONY: dbreset
dbreset: ## Reset database (WARNING: destroys all data!)
	@echo -e "$(RED)WARNING: This will destroy all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DC) down; \
		docker volume rm vervilure-back_postgres_data 2>/dev/null || true; \
		$(DC) up -d db; \
		sleep 5; \
		make migrate; \
		echo -e "$(GREEN)Database reset complete$(NC)"; \
	fi

.PHONY: dbbackup
dbbackup: ## Create database backup
	@mkdir -p backups
	$(DC_EXEC) db pg_dump -U admin test_db | gzip > backups/backup_$$(date +%Y%m%d_%H%M%S).sql.gz
	@echo -e "$(GREEN)Backup created in backups/$(NC)"

.PHONY: dbrestore
dbrestore: ## Restore database from latest backup
	@LATEST_BACKUP=$$(ls -t backups/*.sql.gz | head -1); \
	if [ -z "$$LATEST_BACKUP" ]; then \
		echo -e "$(RED)No backup found$(NC)"; \
	else \
		echo -e "$(YELLOW)Restoring from $$LATEST_BACKUP...$(NC)"; \
		gunzip < $$LATEST_BACKUP | $(DC_EXEC) -T db psql -U admin test_db; \
		echo -e "$(GREEN)Restore complete$(NC)"; \
	fi

# === UTILITIES ===
.PHONY: bash
bash: ## Open bash shell in web container
	$(DC_EXEC) web bash

.PHONY: redis-cli
redis-cli: ## Open Redis CLI
	$(DC_EXEC) redis redis-cli

.PHONY: urls
urls: ## Show all service URLs
	@echo -e "$(GREEN)Service URLs:$(NC)"
	@echo "  Django:    http://localhost:8000"
	@echo "  Django Admin: http://localhost:8000/admin/"
	@if [ "$$($(DC) ps -q mailpit 2>/dev/null)" ]; then echo "  Mailpit:   http://localhost:8025"; fi
	@echo "  PostgreSQL: localhost:5490"
	@echo "  Redis:     localhost:6390"

.PHONY: fix-permissions
fix-permissions: ## Fix file permissions
	@echo -e "$(YELLOW)Fixing permissions...$(NC)"
	sudo chown -R $(USER_ID):$(GROUP_ID) .
	find . -type d -exec chmod 755 {} \;
	find . -type f -exec chmod 644 {} \;
	chmod +x manage.py
	rm -rf .ruff_cache
	@echo -e "$(GREEN)Permissions fixed$(NC)"

.PHONY: clean
clean: ## Clean up Docker resources
	$(DC) down -v
	docker system prune -f

.PHONY: rebuild
rebuild: ## Rebuild containers and restart
	@echo -e "$(YELLOW)Rebuilding containers...$(NC)"
	$(DC) down
	$(DC) build --no-cache
	$(DC) up -d
	@echo -e "$(GREEN)Rebuild complete!$(NC)"

# === DEVELOPMENT SETUP ===
.PHONY: dev-setup
dev-setup: ## Complete development setup
	@echo -e "$(YELLOW)Setting up development environment...$(NC)"
	@make build
	@make up
	@sleep 5
	@make migrate
	@make collectstatic
	@echo -e "$(GREEN)Setup complete! Create superuser with 'make createsuperuser'$(NC)"

.PHONY: install-deps
install-deps: ## Install/update Poetry dependencies
	@echo -e "$(YELLOW)Installing dependencies...$(NC)"
	$(DC_EXEC) web poetry install
	@echo -e "$(GREEN)Dependencies installed!$(NC)"

# === SHORTCUTS ===
.PHONY: m
m: migrate ## Shortcut for migrate

.PHONY: mm
mm: makemigrations ## Shortcut for makemigrations

.PHONY: s
s: shell ## Shortcut for shell

.PHONY: t
t: test ## Shortcut for test

.PHONY: l
l: logs ## Shortcut for logs

.PHONY: f
f: format-safe ## Shortcut for safe format

.PHONY: c
c: createsuperuser ## Shortcut for createsuperuser

# === CI/CD ===
.PHONY: ci-test
ci-test: ## Run tests in CI mode
	$(DC_RUN) -e CI=true web $(POETRY) pytest -v --no-migrations

.PHONY: ci-lint
ci-lint: ## Run linting in CI mode
	$(DC_RUN) web $(POETRY) ruff check . --output-format=github --no-cache
	$(DC_RUN) web $(POETRY) mypy . --no-error-summary

.PHONY: ci-format-check
ci-format-check: ## Check formatting in CI mode
	$(DC_RUN) web $(POETRY) black --check .
	$(DC_RUN) web $(POETRY) isort --check-only .
	$(DC_RUN) web $(POETRY) ruff check . --no-cache
