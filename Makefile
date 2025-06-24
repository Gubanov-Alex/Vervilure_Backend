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
help: ## Show this help message with sections
	@echo -e "$(GREEN)Vervilure Backend - Docker Management$(NC)"
	@echo -e "Current user: UID=$(USER_ID), GID=$(GROUP_ID)\n"
	@echo -e "$(BLUE)DOCKER LIFECYCLE:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(build|up|down|restart|ps)" | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo -e "\n$(BLUE)DJANGO MANAGEMENT:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(manage|shell|migrate|test)" | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo -e "\n$(BLUE)ENVIRONMENT & MONITORING:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(env-|health|monitor|watch)" | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo -e "\n$(BLUE)UTILITIES:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(clean|fix|reset|urls)" | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'


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

.PHONY:
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
validate-env:
	@echo "Validating environment configuration..."
	@docker-compose run --rm web poetry run python manage.py check --deploy --settings=config.settings
	@echo "✓ Environment configuration is valid"
# Quick fixes
fix-docker:
	@echo "Fixing Docker build issues..."
	@if [ ! -f README.md ]; then echo "# Vervilure E-commerce Platform" > README.md; echo "Created README.md"; fi
	@echo "Cleaning Docker cache..."
	docker builder prune -f
	@echo "Rebuilding..."
	$(MAKE) build

# Debugging commands
debug-web:
	@echo "Web container logs:"
	docker-compose logs web

debug-celery:
	@echo "Celery container logs:"
	docker-compose logs celery

debug-all:
	@echo "All container logs:"
	docker-compose logs

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

# === ENVIRONMENT DIAGNOSTICS ===
.PHONY: env-check
env-check: ## Check environment status and configuration
	@echo -e "$(GREEN)Environment Status Check$(NC)"
	@echo -e "$(YELLOW)Docker Services:$(NC)"
	@$(DC) ps --format 'table {{.Service}}\t{{.Status}}\t{{.Ports}}'
	@echo -e "\n$(YELLOW)Python Environment:$(NC)"
	@$(DC_EXEC) web python --version
	@$(DC_EXEC) web poetry --version
	@echo -e "\n$(YELLOW)Database Connection:$(NC)"
	@$(DC_EXEC) web $(POETRY) python -c "import django; django.setup(); from django.db import connection; connection.ensure_connection(); print('✅ Database connected')" 2>/dev/null || echo "❌ Database connection failed"
	@echo -e "\n$(YELLOW)Redis Connection:$(NC)"
	@$(DC_EXEC) redis redis-cli ping 2>/dev/null || echo "❌ Redis connection failed"

.PHONY: env-info
env-info: ## Show detailed environment information
	@echo -e "$(GREEN)Detailed Environment Information$(NC)"
	@echo -e "$(YELLOW)System Info:$(NC)"
	@echo "User: $(USER_ID):$(GROUP_ID)"
	@echo "Shell: $(SHELL)"
	@echo "Working directory: $(PWD)"
	@echo -e "\n$(YELLOW)Container Environment:$(NC)"
	@$(DC_EXEC) web env | grep -E "(DJANGO|DB_|REDIS|CELERY|POETRY)" | sort
	@echo -e "\n$(YELLOW)Poetry Configuration:$(NC)"
	@$(DC_EXEC) web poetry config --list
	@echo -e "\n$(YELLOW)Installed Packages (top 10):$(NC)"
	@$(DC_EXEC) web poetry show | head -10

.PHONY: health-check
health-check: ## Run comprehensive health check
	@echo -e "$(GREEN)Running Health Checks$(NC)"
	@echo -e "$(YELLOW)Services Status:$(NC)"
	@for service in web db redis mailpit; do \
		if [ "$$($(DC) ps -q $$service 2>/dev/null)" ]; then \
			echo "✅ $$service - running"; \
		else \
			echo "❌ $$service - not running"; \
		fi; \
	done
	@echo -e "\n$(YELLOW)Application Health:$(NC)"
	@curl -s http://localhost:8000/health/ >/dev/null && echo "✅ Django - healthy" || echo "❌ Django - unhealthy"
	@curl -s http://localhost:8025/api/v1/info >/dev/null && echo "✅ Mailpit - healthy" || echo "❌ Mailpit - unhealthy"

.PHONY: dev-shell
dev-shell: ## Open interactive development shell
	@echo -e "$(GREEN)Opening development shell...$(NC)"
	@echo "Available commands: python, django-admin, poetry, pytest, manage.py"
	@echo "Type 'exit' to return to host shell"
	@$(DC_EXEC) web bash

.PHONY: quick-test
quick-test: ## Run quick smoke tests
	@echo -e "$(YELLOW)Running quick smoke tests...$(NC)"
	@$(DC_EXEC) web $(POETRY) python -c "import django; print('✅ Django import')"
	@$(DC_EXEC) web $(POETRY) python manage.py check --deploy --quiet && echo "✅ Django deployment check"
	@$(DC_EXEC) web $(POETRY) python -c "from django.conf import settings; print(f'✅ Debug mode: {settings.DEBUG}')"

.PHONY: reset-cache
reset-cache: ## Reset all caches (Python, Poetry, Docker)
	@echo -e "$(YELLOW)Resetting all caches...$(NC)"
	@$(DC_EXEC) web find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@$(DC_EXEC) web find . -name "*.pyc" -delete 2>/dev/null || true
	@docker system prune -f
	@echo -e "$(GREEN)Caches cleared$(NC)"

.PHONY: deps-check
deps-check: ## Check for dependency issues
	@echo -e "$(YELLOW)Checking dependencies...$(NC)"
	@$(DC_EXEC) web $(POETRY) check
	@$(DC_EXEC) web $(POETRY) show --outdated | head -10 || echo "All packages up to date"

# === PRODUCTION READINESS ===
.PHONY: prod-check
prod-check: ## Check production readiness
	@echo -e "$(GREEN)Production Readiness Check$(NC)"
	@$(DC_EXEC) web $(POETRY) python manage.py check --deploy
	@$(DC_EXEC) web $(POETRY) python manage.py makemigrations --dry-run --check
	@echo -e "$(GREEN)Production checks complete$(NC)"

# === MONITORING ===
.PHONY: watch-logs
watch-logs: ## Watch logs with filtering
	@echo -e "$(YELLOW)Watching logs (Ctrl+C to stop)...$(NC)"
	@$(DC) logs -f --tail=50 | grep -E "(ERROR|WARNING|INFO|DEBUG)" --color=always

.PHONY: monitor
monitor: ## Monitor system resources
	@echo -e "$(GREEN)System Monitoring$(NC)"
	@echo -e "$(YELLOW)Container Stats:$(NC)"
	@docker stats --no-stream $$($(DC) ps -q) 2>/dev/null || echo "No running containers"
	@echo -e "\n$(YELLOW)Disk Usage:$(NC)"
	@docker system df

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


# =============================================================================
# PRODUCTION DEPLOYMENT COMMANDS
# =============================================================================

# Production Docker Compose
DC_PROD = docker-compose -f docker-compose.prod.yml
DC_PROD_EXEC = $(DC_PROD) exec

.PHONY: prod-setup
prod-setup: ## Complete production setup
	@echo -e "$(YELLOW)Setting up production environment...$(NC)"
	@if [ ! -f .env.production ]; then \
		echo -e "$(RED)❌ .env.production file not found!$(NC)"; \
		echo "Please create .env.production file with production settings"; \
		exit 1; \
	fi
	@make prod-build
	@make prod-up
	@sleep 10
	@make prod-migrate
	@make prod-collectstatic
	@echo -e "$(GREEN)✅ Production setup complete!$(NC)"

.PHONY: prod-build
prod-build: ## Build production containers
	@echo -e "$(YELLOW)Building production containers...$(NC)"
	$(DC_PROD) build --no-cache

.PHONY: prod-up
prod-up: ## Start production services
	@echo -e "$(YELLOW)Starting production services...$(NC)"
	$(DC_PROD) up -d

.PHONY: prod-down
prod-down: ## Stop production services
	@echo -e "$(YELLOW)Stopping production services...$(NC)"
	$(DC_PROD) down

.PHONY: prod-restart
prod-restart: ## Restart production services
	@echo -e "$(YELLOW)Restarting production services...$(NC)"
	$(DC_PROD) restart

.PHONY: prod-logs
prod-logs: ## View production logs
	$(DC_PROD) logs -f

.PHONY: prod-status
prod-status: ## Check production services status
	@echo -e "$(GREEN)Production Services Status:$(NC)"
	@$(DC_PROD) ps --format 'table {{.Service}}\t{{.Status}}\t{{.Ports}}'

.PHONY: prod-migrate
prod-migrate: ## Run production migrations
	@echo -e "$(YELLOW)Running production migrations...$(NC)"
	$(DC_PROD_EXEC) web poetry run python manage.py migrate

.PHONY: prod-collectstatic
prod-collectstatic: ## Collect production static files
	@echo -e "$(YELLOW)Collecting static files...$(NC)"
	$(DC_PROD_EXEC) web poetry run python manage.py collectstatic --noinput

.PHONY: prod-createsuperuser
prod-createsuperuser: ## Create production superuser
	@echo -e "$(YELLOW)Creating production superuser...$(NC)"
	$(DC_PROD_EXEC) web poetry run python manage.py createsuperuser

.PHONY: prod-shell
prod-shell: ## Open production Django shell
	$(DC_PROD_EXEC) web poetry run python manage.py shell

.PHONY: prod-bash
prod-bash: ## Open production bash shell
	$(DC_PROD_EXEC) web bash

.PHONY: prod-dbshell
prod-dbshell: ## Open production database shell
	$(DC_PROD_EXEC) db psql -U $(DB_USER) -d $(DB_NAME)

# =============================================================================
# DATABASE TROUBLESHOOTING COMMANDS
# =============================================================================

.PHONY: debug-db
debug-db: ## Debug database connection issues
	@echo -e "$(YELLOW)Debugging database connection...$(NC)"
	@bash debug-db-connection.sh

.PHONY: check-env
check-env: ## Check environment configuration
	@echo -e "$(YELLOW)Checking environment configuration...$(NC)"
	@if [ -f .env.production ]; then \
		echo -e "$(GREEN)✅ .env.production exists$(NC)"; \
		echo "Database configuration:"; \
		grep -E "^(DB_|POSTGRES_)" .env.production || echo "No database config found"; \
	else \
		echo -e "$(RED)❌ .env.production not found$(NC)"; \
	fi
	@if [ -f .env.docker ]; then \
		echo -e "$(GREEN)✅ .env.docker exists$(NC)"; \
		echo "Database configuration:"; \
		grep -E "^(DB_|POSTGRES_)" .env.docker || echo "No database config found"; \
	else \
		echo -e "$(YELLOW)⚠️  .env.docker not found$(NC)"; \
	fi

.PHONY: test-db-connection
test-db-connection: ## Test database connection
	@echo -e "$(YELLOW)Testing database connection...$(NC)"
	@if docker-compose ps | grep -q "db.*Up"; then \
		echo -e "$(GREEN)✅ Database container is running$(NC)"; \
		if $(DC_EXEC) db psql -U admin -d test_db -c "SELECT 1;" 2>/dev/null; then \
			echo -e "$(GREEN)✅ Database connection successful$(NC)"; \
		else \
			echo -e "$(RED)❌ Database connection failed$(NC)"; \
			echo "Database logs:"; \
			docker-compose logs db | tail -10; \
		fi; \
	else \
		echo -e "$(RED)❌ Database container is not running$(NC)"; \
	fi

.PHONY: fix-db-permissions
fix-db-permissions: ## Fix database permissions issues
	@echo -e "$(YELLOW)Fixing database permissions...$(NC)"
	@echo -e "$(RED)WARNING: This will restart the database container!$(NC)"
	@read -p "Continue? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose stop db; \
		docker-compose rm -f db; \
		docker volume rm $$(docker-compose config --volumes | grep postgres) 2>/dev/null || true; \
		docker-compose up -d db; \
		sleep 10; \
		echo -e "$(GREEN)✅ Database permissions fixed$(NC)"; \
	fi

.PHONY: reset-prod-db
reset-prod-db: ## Reset production database (DANGEROUS!)
	@echo -e "$(RED)🚨 WARNING: This will DELETE ALL PRODUCTION DATA! 🚨$(NC)"
	@echo -e "$(RED)This action is IRREVERSIBLE!$(NC)"
	@read -p "Type 'RESET_PRODUCTION_DATABASE' to continue: " confirmation; \
	if [ "$$confirmation" = "RESET_PRODUCTION_DATABASE" ]; then \
		$(DC_PROD) down; \
		docker volume rm $$($(DC_PROD) config --volumes | grep postgres) 2>/dev/null || true; \
		$(DC_PROD) up -d db; \
		sleep 10; \
		$(DC_PROD_EXEC) web poetry run python manage.py migrate; \
		echo -e "$(GREEN)✅ Production database reset complete$(NC)"; \
	else \
		echo -e "$(YELLOW)Operation cancelled$(NC)"; \
	fi

# =============================================================================
# MONITORING AND MAINTENANCE
# =============================================================================

.PHONY: prod-backup
prod-backup: ## Create production database backup
	@mkdir -p backups/production
	@BACKUP_FILE=backups/production/backup_$$(date +%Y%m%d_%H%M%S).sql.gz; \
	$(DC_PROD_EXEC) db pg_dump -U $(DB_USER) $(DB_NAME) | gzip > $$BACKUP_FILE; \
	echo -e "$(GREEN)✅ Backup created: $$BACKUP_FILE$(NC)"

.PHONY: prod-restore
prod-restore: ## Restore production database from backup
	@echo -e "$(YELLOW)Available backups:$(NC)"
	@ls -la backups/production/*.sql.gz 2>/dev/null || echo "No backups found"
	@read -p "Enter backup filename: " backup_file; \
	if [ -f "$$backup_file" ]; then \
		echo -e "$(RED)WARNING: This will replace current database!$(NC)"; \
		read -p "Continue? [y/N] " -n 1 -r; \
		if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
			gunzip < "$$backup_file" | $(DC_PROD_EXEC) -T db psql -U $(DB_USER) $(DB_NAME); \
			echo -e "$(GREEN)✅ Restore complete$(NC)"; \
		fi; \
	else \
		echo -e "$(RED)❌ Backup file not found$(NC)"; \
	fi

.PHONY: prod-health
prod-health: ## Check production health
	@echo -e "$(GREEN)Production Health Check:$(NC)"
	@curl -s http://localhost:8000/health/ | python -m json.tool || echo "Health check failed"

.PHONY: prod-deploy
prod-deploy: ## Deploy to production
	@echo -e "$(YELLOW)Deploying to production...$(NC)"
	@git pull origin main
	@make prod-build
	@make prod-down
	@make prod-up
	@sleep 15
	@make prod-migrate
	@make prod-collectstatic
	@make prod-health
	@echo -e "$(GREEN)✅ Deployment complete!$(NC)"
