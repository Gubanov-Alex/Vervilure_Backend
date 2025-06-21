.PHONY: help build up down restart logs shell migrate makemigrations test superuser env-docker env-local setup-docker clean reset-db lint format test-coverage debug init status collectstatic db-shell redis-cli tools tools-down info fix-docker reset-all debug-web debug-celery debug-all restart-services check-django

# Default target
help:
	@echo "Available commands:"
	@echo "  build         - Build Docker images"
	@echo "  up            - Start all services"
	@echo "  down          - Stop all services"
	@echo "  restart       - Restart all services"
	@echo "  logs          - Show logs for all services"
	@echo "  status        - Show services status"
	@echo "  shell         - Open Django shell"
	@echo "  migrate       - Run Django migrations"
	@echo "  makemigrations- Create Django migrations"
	@echo "  test          - Run tests"
	@echo "  test-coverage - Run tests with coverage"
	@echo "  superuser     - Create Django superuser"
	@echo "  collectstatic - Collect static files"
	@echo "  env-docker    - Switch to Docker environment"
	@echo "  env-local     - Switch to local environment"
	@echo "  setup-docker  - Complete Docker setup"
	@echo "  clean         - Clean containers and volumes"
	@echo "  reset-db      - Reset database"
	@echo "  lint          - Run code linting"
	@echo "  format        - Format code"
	@echo "  db-shell      - Open PostgreSQL shell"
	@echo "  redis-cli     - Open Redis CLI"
	@echo "  tools         - Start development tools (pgAdmin, Redis Commander)"
	@echo "  tools-down    - Stop development tools"
	@echo "  debug         - Show PyCharm debugging setup"
	@echo "  init          - Initialize project"
	@echo "  info          - Show project info and status"
	@echo "  fix-docker    - Fix common Docker build issues"
	@echo "  reset-all     - Complete reset (nuclear option)"
	@echo "  debug-web     - Show web container logs"
	@echo "  debug-celery  - Show celery container logs"
	@echo "  debug-all     - Show all container logs"
	@echo "  restart-services - Restart failed services"
	@echo "  check-django  - Check Django configuration"

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services started. Web available at http://localhost:8000"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

# Status check
status:
	docker-compose ps

# Django commands
shell:
	docker-compose exec web poetry run python manage.py shell

migrate:
	@echo "Running migrations..."
	docker-compose exec web poetry run python manage.py migrate

makemigrations:
	docker-compose exec web poetry run python manage.py makemigrations

test:
	docker-compose exec web poetry run pytest -v

superuser:
	docker-compose exec web poetry run python manage.py createsuperuser

collectstatic:
	docker-compose exec web poetry run python manage.py collectstatic --noinput

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

# Quick setup for Docker
setup-docker:
	@echo "Setting up Docker environment..."
	$(MAKE) env-docker
	$(MAKE) build
	$(MAKE) up
	@echo "Waiting for services to start..."
	sleep 15
	$(MAKE) migrate
	@echo "Docker setup complete! Create superuser with 'make superuser'"

# Testing and Quality
test-coverage:
	docker-compose exec web poetry run pytest --cov=src --cov-report=html --cov-report=term


lint:
	@echo "Running code linting..."
	docker-compose exec web poetry run flake8 --max-line-length=120 . || true
	docker-compose exec web poetry run mypy . || true

format:
	@echo "Formatting code..."
	poetry run black .
	poetry run isort .

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

# Complete testing setup
setup-testing: setup-mailpit test-auth-flow
	@echo "Testing environment ready!"
	@echo "- Mailpit: http://localhost:8025"
	@echo "- Django Admin: http://localhost:8000/admin/"
	@echo "- Login: http://localhost:8000/auth/login/"
	@echo "- Google OAuth: http://localhost:8000/auth/google/login/"

# Maintenance
clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

reset-db:
	@echo "Resetting database..."
	docker-compose down
	docker volume rm $$(docker-compose config --services | head -1)_postgres_data 2>/dev/null || true
	docker-compose up -d db
	@echo "Waiting for database to start..."
	sleep 10
	$(MAKE) migrate
	@echo "Database reset complete. Create superuser with 'make superuser'"

# Development helpers
db-shell:
	docker-compose exec db psql -U admin -d test_db

redis-cli:
	docker-compose exec redis redis-cli

# Development tools
tools:
	@echo "Starting development tools..."
	docker-compose --profile tools up -d
	@echo "Tools started:"
	@echo "  pgAdmin: http://localhost:8080 (admin@vervilure.local / admin)"
	@echo "  Redis Commander: http://localhost:8081"

tools-down:
	docker-compose --profile tools down

# PyCharm specific
debug:
	@echo "PyCharm Remote Debugging Setup:"
	@echo "1. Run → Edit Configurations → Python Remote Debug"
	@echo "2. Host: localhost, Port: 5678"
	@echo "3. Path mappings: /app → $(PWD)"
	@echo "4. Add this to your code:"
	@echo "   import pydevd_pycharm"
	@echo "   pydevd_pycharm.settrace('host.docker.internal', port=5678)"

# Environment setup
init:
	@echo "Initializing project with simplified environment configuration..."
	@if [ ! -f .env.docker ] && [ ! -f .env.local ]; then \
		echo "Creating both environment templates..."; \
		$(MAKE) create-docker-env; \
		$(MAKE) create-local-env; \
		echo ""; \
		echo "Environment files created:"; \
		echo "  .env.docker - for Docker development"; \
		echo "  .env.local  - for local development"; \
		echo ""; \
		echo "Edit the appropriate file for your setup, then run:"; \
		echo "  make setup-docker  (for Docker development)"; \
		echo "  make setup-local   (for local development)"; \
	else \
		echo "Environment files already exist:"; \
		[ -f .env.docker ] && echo "  ✓ .env.docker"; \
		[ -f .env.local ] && echo "  ✓ .env.local"; \
	fi

validate-env:
	@echo "Validating environment configuration..."
	@docker-compose run --rm web poetry run python manage.py check --deploy --settings=config.settings
	@echo "✓ Environment configuration is valid"
env-info:
	@echo "Environment Information:"
	@echo "======================="
	@if [ -f .env.docker ]; then echo "Docker config: .env.docker exists"; else echo "Docker config: .env.docker missing"; fi
	@if [ -f .env.local ]; then echo "Local config:  .env.local exists"; else echo "Local config:  .env.local missing"; fi
	@echo ""
	@echo "Current detection (when Django loads):"
	@echo "  IS_LOCAL_DOCKER: DB_HOST contains 'db'"
	@echo "  IS_CI: GITHUB_ACTIONS or ENVIRONMENT=ci"
	@echo ""
	@echo "File priority:"
	@echo "  1. CI: GitHub Actions environment variables"
	@echo "  2. Docker: .env.docker (when DB_HOST contains 'db')"
	@echo "  3. Local: .env.local (when DB_HOST doesn't contain 'db')"

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

# Restart failed services
restart-services:
	@echo "Restarting failed services..."
	docker-compose up -d web celery

# Check Django configuration
check-django:
	@echo "Checking Django configuration..."
	docker-compose run --rm web poetry run python manage.py check

# Reset everything
reset-all:
	@echo "Resetting entire Docker environment..."
	docker-compose down -v
	docker system prune -af
	docker volume prune -f
	$(MAKE) fix-docker
	$(MAKE) setup-docker

# Project info
info:
	@echo "Project: Vervilure E-commerce Platform"
	@echo "Services status:"
	@docker-compose ps
	@echo ""
	@echo "Available URLs:"
	@echo "  Django: http://localhost:8000"
	@echo "  PostgreSQL: localhost:5490"
	@echo "  Redis: localhost:6379"
test-django:
	docker-compose exec web poetry run python manage.py test
