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
NC := \033[0m # No Color

# Main targets
.PHONY: help
help: ## Show this help message
	@echo -e "$(GREEN)Vervilure Backend - Docker Management$(NC)"
	@echo -e "Current user: UID=$(USER_ID), GID=$(GROUP_ID)\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
# Environment switching
env-docker:
	@echo "Switching to Docker environment..."
	@if [ ! -f .env.docker ]; then \
		echo "Error: .env.docker not found. Creating template..."; \
		$(MAKE) create-docker-env; \
	fi
	@echo "Using .env.docker for Docker development"
	@echo "✓ Docker environment configured"

env-local:
	@echo "Switching to local environment..."
	@if [ ! -f .env.local ]; then \
		echo "Error: .env.local not found. Creating template..."; \
		$(MAKE) create-local-env; \
	fi
	@echo "Using .env.local for local development"
	@echo "✓ Local environment configured"

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

.PHONY: up-all
up-all: ## Start all services including dev tools
	$(DC) --profile dev --profile tools up -d
	@echo -e "$(GREEN)All services started!$(NC)"
	@make urls

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
# Google OAuth Management
cleanup-oauth-duplicates:
	@echo "Cleaning up duplicate Google OAuth configurations..."
	docker-compose exec web poetry run python manage.py cleanup_oauth_duplicates

cleanup-oauth-duplicates-dry:
	@echo "Checking for duplicate Google OAuth configurations..."
	docker-compose exec web poetry run python manage.py cleanup_oauth_duplicates --dry-run

test-google-oauth-clean:
	@echo "Cleaning OAuth duplicates and running tests..."
	$(MAKE) cleanup-oauth-duplicates
	$(MAKE) test-google-oauth
setup-mailpit:
	@echo "Setting up Mailpit and OAuth..."
	$(MAKE) up
	sleep 5
	docker-compose exec web poetry run python manage.py setup_oauth
	@echo "Mailpit UI: http://localhost:8025"
	@echo "Admin: http://localhost:8000/admin/"

test-email:
	docker-compose exec web poetry run python manage.py test_email

# Authentication JWT Testing
test-jwt-auth:
	@echo "Running JWT authentication flow tests..."
	docker-compose exec web poetry run python manage.py test_jwt_auth_flow --verbose

test-jwt-auth-quick:
	@echo "Running JWT authentication tests (no cleanup)..."
	docker-compose exec web poetry run python manage.py test_jwt_auth_flow --skip-cleanup

# Google OAuth Testing
test-google-oauth:
	@echo "Running Google OAuth authentication tests..."
	docker-compose exec web poetry run python manage.py test_google_oauth --verbose

test-google-oauth-quick:
	@echo "Running Google OAuth tests (no cleanup)..."
	docker-compose exec web poetry run python manage.py test_google_oauth --skip-cleanup

mailpit-logs:
	docker-compose logs mailpit
# === CODE QUALITY ===
.PHONY: lint
lint: ## Run all linters
	@echo -e "$(YELLOW)Running linters...$(NC)"
	$(DC_EXEC) web $(POETRY) ruff check .
	$(DC_EXEC) web $(POETRY) mypy .

.PHONY: format
format: ## Format code with black and isort
	$(DC_EXEC) web $(POETRY) black .
	$(DC_EXEC) web $(POETRY) isort .
	$(DC_EXEC) web $(POETRY) ruff check . --fix

.PHONY: check
check: ## Run all checks (tests, linting, etc.)
	@make lint
	@make test

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
		docker volume rm vervilure_postgres_data 2>/dev/null || true; \
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

# === CELERY ===
.PHONY: celery-logs
celery-logs: ## Show Celery worker logs
	$(DC) logs -f --tail=100 celery

.PHONY: flower
flower: ## Start Flower (Celery monitoring)
	$(DC) --profile monitoring up -d flower
	@echo "Flower available at: http://localhost:5555"

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
	@if [ "$$($(DC) ps -q flower 2>/dev/null)" ]; then echo "  Flower:    http://localhost:5555"; fi
	@if [ "$$($(DC) ps -q pgadmin 2>/dev/null)" ]; then echo "  pgAdmin:   http://localhost:5050"; fi
	@echo "  PostgreSQL: localhost:5490"
	@echo "  Redis:     localhost:6390"

# === DEVELOPMENT TOOLS ===
.PHONY: dev
dev: ## Start development environment with all tools
	$(DC) --profile dev --profile tools --profile monitoring up -d
	@make urls

.PHONY: tools
tools: ## Start development tools (pgAdmin)
	$(DC) --profile tools up -d
	@echo "pgAdmin available at: http://localhost:5050"
	@echo "Login: admin@vervilure.local / admin"

# === MAINTENANCE ===
.PHONY: clean
clean: ## Clean up Docker resources
	$(DC) down -v
	docker system prune -f

.PHONY: clean-all
clean-all: ## Clean everything including images
	$(DC) down -v --rmi all
	docker system prune -af --volumes

.PHONY: fix-permissions
fix-permissions: ## Fix file permissions
	@echo -e "$(YELLOW)Fixing permissions...$(NC)"
	@sudo chown -R $(USER_ID):$(GROUP_ID) .
	@find . -type d -exec chmod 755 {} \;
	@find . -type f -exec chmod 644 {} \;
	@chmod +x manage.py
	@echo -e "$(GREEN)Permissions fixed$(NC)"

# === QUICK COMMANDS ===
.PHONY: dev-setup
dev-setup: ## Complete development setup
	@echo -e "$(YELLOW)Setting up development environment...$(NC)"
	@make build
	@make up
	@sleep 5
	@make migrate
	@make collectstatic
	@echo -e "$(GREEN)Setup complete! Create superuser with 'make createsuperuser'$(NC)"

.PHONY: quickfix
quickfix: ## Quick fix for common Docker issues
	@echo -e "$(YELLOW)Running quick fixes...$(NC)"
	@docker-compose down --remove-orphans || true
	@docker network prune -f
	@docker volume prune -f
	@echo -e "$(GREEN)Quick fix complete$(NC)"

# === PRODUCTION ===
.PHONY: prod
prod: ## Start production-like environment
	$(DC) --profile production up -d
	@echo "Nginx available at: http://localhost"

.PHONY: deploy-check
deploy-check: ## Run deployment readiness check
	$(DC_EXEC) web $(POETRY) $(MANAGE) check --deploy
	$(DC_EXEC) web $(POETRY) $(MANAGE) validate_templates
	@echo -e "$(GREEN)Deployment checks passed$(NC)"

# === MONITORING ===
.PHONY: stats
stats: ## Show container resource usage
	docker stats --no-stream $$($(DC) ps -q)

.PHONY: health
health: ## Check health of all services
	@echo -e "$(YELLOW)Checking service health...$(NC)"
	@$(DC) ps | grep -E "(healthy|unhealthy)" || echo "All services running"

# === SHORTCUTS ===
.PHONY: m
m: migrate ## Shortcut for migrate

.PHONY: mm
mm: makemigrations ## Shortcut for makemigrations

.PHONY: c
c: createsuperuser ## Shortcut for createsuperuser

.PHONY: s
s: shell ## Shortcut for shell

.PHONY: t
t: test ## Shortcut for test

.PHONY: l
l: logs ## Shortcut for logs

# === CI/CD ===
.PHONY: ci-test
ci-test: ## Run tests in CI mode
	$(DC_RUN) -e CI=true web $(POETRY) pytest -v --no-migrations

.PHONY: ci-lint
ci-lint: ## Run linting in CI mode
	$(DC_RUN) web $(POETRY) ruff check . --exit-non-zero-on-fix
	$(DC_RUN) web $(POETRY) mypy . --strict
