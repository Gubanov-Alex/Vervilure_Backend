Vervilure E-commerce Platform
A comprehensive Django-based e-commerce platform providing a scalable and robust solution for online retail operations.

Project Status
🚧 Early Development 🚧

This project is currently in the early stages of development. Core features are being designed and implemented. The codebase is not yet ready for production use.

About This Project

This platform is built to support product management, user authentication, shopping cart functionality, order processing, and payment integration. It offers a complete solution for modern e-commerce businesses with both admin and customer interfaces.

Key Features
🔐 User authentication and authorization
📦 Product catalog with categories and search
🛒 Shopping cart and order management
💳 Payment processing with Stripe
🔌 RESTful API for mobile and third-party integration
⚡ Asynchronous task processing for performance optimization
🐳 Full Docker support for development and production
🔄 CI/CD pipeline with GitHub Actions
📊 Comprehensive testing suite

# Docker and Makefile Development Setup

## Prerequisites

- Docker and Docker Compose
- Git
- Make

## Quick Start with Docker

1. Clone the repository:
   ```
   git clone <repository-url>
   cd Vervilure_Backend
   ```

2. Initialize the project:
   ```
   make init
   ```
   This will create an `.env` file based on `.env_default`. Edit this file if needed.

3. Set up Docker environment:
   ```
   make setup-docker
   ```
   This command will:
   - Switch to Docker environment
   - Build Docker images
   - Start all services
   - Run Django migrations

4. Create a superuser:
   ```
   make superuser
   ```

5. Access the project at http://localhost:8000

## Makefile Commands Reference

### Docker Management

- `make build` - Build Docker images
- `make up` - Start all services
- `make down` - Stop all services
- `make restart` - Restart all services
- `make logs` - View logs for all services
- `make status` - Check services status

### Django Commands

- `make shell` - Open Django shell
- `make migrate` - Run Django migrations
- `make makemigrations` - Create Django migrations
- `make test` - Run tests
- `make test-coverage` - Run tests with coverage report
- `make superuser` - Create Django superuser
- `make collectstatic` - Collect static files

### Environment Switching

- `make env-docker` - Switch to Docker environment
- `make env-local` - Switch to local environment

### Development Tools

- `make tools` - Start development tools (pgAdmin, Redis Commander)
- `make tools-down` - Stop development tools
- `make db-shell` - Open PostgreSQL shell
- `make redis-cli` - Open Redis CLI

### Maintenance and Debugging

- `make clean` - Clean containers and volumes
- `make reset-db` - Reset database
- `make lint` - Run code linting
- `make format` - Format code
- `make debug-web` - View web container logs
- `make debug-celery` - View Celery container logs
- `make debug-all` - View all container logs
- `make fix-docker` - Fix common Docker build issues
- `make reset-all` - Complete reset (nuclear option)
- `make check-django` - Check Django configuration

## Service URLs

When running with Docker, you can access:
- Django: http://localhost:8000
- PostgreSQL: localhost:5490
- Redis: localhost:6379
- pgAdmin (when tools are running): http://localhost:8080 (admin@vervilure.local / admin)
- Redis Commander (when tools are running): http://localhost:8081
