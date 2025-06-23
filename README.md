# Vervilure E-commerce Platform

A comprehensive Django-based e-commerce platform providing a scalable and robust solution for online retail operations.

## Project Status
🚀 **Production Ready Core** 🚀

Core authentication, user management, and OAuth integration are implemented and tested. Platform architecture is production-ready with comprehensive testing and monitoring capabilities.

## About This Project

Modern e-commerce platform built with Django REST Framework, featuring secure JWT authentication, Google OAuth integration, robust API design, and full Docker support for development and production environments.

## Architecture Overview

### Tech Stack
- **Backend**: Django 5.2 + Django REST Framework 3.16
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7 + Celery 5.5
- **Authentication**: JWT + Google OAuth + django-allauth
- **API Documentation**: Swagger/OpenAPI (drf-yasg)
- **Testing**: pytest + coverage (70%+ coverage)
- **Code Quality**: Black, isort, flake8, mypy, safety
- **Deployment**: Docker + docker-compose
- **CI/CD**: GitHub Actions (complete pipeline)

### Project Structure

```
Vervilure_Backend/
├── config/                    # Django project configuration
│   ├── settings.py           # Environment-aware settings
│   ├── urls.py               # Main URL routing  
│   └── wsgi.py/asgi.py       # Server configuration
│
├── src/                      # Application source code
│   ├── apps/                 # Django applications
│   │   ├── accounts/         # ✅ User management & authentication
│   │   │   ├── models.py     # User + UserAddress + BlacklistedToken
│   │   │   ├── views.py      # AuthViewSet (JWT + OAuth + CRUD)
│   │   │   ├── serializers.py # Comprehensive validation
│   │   │   ├── auth_urls.py  # Authentication endpoints
│   │   │   ├── user_urls.py  # User management endpoints
│   │   │   ├── jwt_views.py  # JWT token management
│   │   │   ├── throttles.py  # Rate limiting
│   │   │   ├── utils/        # OAuth validators
│   │   │   └── management/   # Django commands
│   │   │
│   │   ├── catalog/          # 🚧 Product catalog (planned)
│   │   ├── cart/             # 🚧 Shopping cart (planned)
│   │   ├── orders/           # 🚧 Order management (planned)
│   │   └── reviews/          # 🚧 Product reviews (planned)
│   │
│   ├── api/                  # API routing and versioning
│   └── core/                 # Shared utilities
│       ├── middleware/       # Custom middleware
│       ├── mixins/           # Reusable mixins
│       ├── testing/          # Testing utilities
│       └── utils/            # Helper functions
│
├── tests/                    # Comprehensive test suite
│   ├── conftest.py           # Pytest configuration  
│   ├── test_settings.py      # Test-specific settings
│   ├── test_authentication.py # Authentication tests
│   ├── test_serializers.py   # Serializer validation tests
│   └── test_*.py             # Feature-specific tests
│
├── docs/                     # Documentation
│   └── architecture/         # Architecture documentation
│
├── .github/workflows/        # CI/CD pipeline
│   └── Vervelure_CI.yml      # Complete GitHub Actions workflow
│
├── docker-compose.yml        # Development environment
├── Dockerfile               # Application container (multi-stage)
├── Makefile                 # 70+ development commands
├── pyproject.toml           # Poetry dependencies + tools config
├── poetry.lock              # Locked dependencies
└── entrypoint.sh            # Docker entrypoint script
```

## Key Features

### ✅ Implemented and Tested
- 🔐 **JWT Authentication** with refresh token rotation and blacklisting
- 🔑 **Google OAuth Integration** via django-allauth
- 👤 **User Management** with profile, addresses, preferences
- 📧 **Email System** with Mailpit for development
- 🔒 **Security Features** (rate limiting, CORS, token blacklist)
- 🐳 **Docker Development Environment** with hot-reload
- 📊 **Comprehensive Testing** (OAuth, JWT, edge cases, 70%+ coverage)
- 🔧 **Development Tools** (pgAdmin, Redis Commander, Mailpit)
- 📝 **API Documentation** (Swagger/OpenAPI auto-generation)
- 🎨 **Code Quality Tools** (Black, isort, flake8, mypy)
- 🚀 **CI/CD Pipeline** (GitHub Actions with matrix testing)
- 🛡️ **Security Scanning** (safety, dependency checks)

### 🚧 In Development (Architecture Ready)
- 📦 Product catalog with categories and search
- 🛒 Shopping cart and order management  
- 💳 Payment processing with Stripe
- ⚡ Asynchronous task processing (Celery configured)
- 📈 Performance monitoring and analytics
- 🌐 Multi-language support

## Quick Start

### Prerequisites
- **Docker** and **Docker Compose** 20.0+
- **Git**
- **Make** (optional, but recommended)

### 1. Clone and Initialize

```bash
git clone <repository-url>
cd Vervilure_Backend
make init
```

This creates two template files:
- `.env.docker` - for Docker development
- `.env.local` - for local development

### 2. Choose Development Environment

#### Option A: Docker Development (Recommended)
```bash
# Complete Docker environment setup
make setup-docker

# Or step by step:
make build              # Build containers
make up                 # Start services
make migrate            # Run DB migrations
make superuser          # Create admin user
```

#### Option B: Local Development
```bash
# Local environment setup
make setup-local

# Requires installed PostgreSQL, Redis, Python 3.12+
```

### 3. Check Status
```bash
make status             # Container status
make urls               # List all services
make health             # Health check all services
```

### 4. Access Services
- **Django Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/swagger/
- **Django Admin**: http://localhost:8000/admin/
- **Mailpit (Email Testing)**: http://localhost:8025
- **pgAdmin**: http://localhost:8080 (with `make tools`)
- **Redis Commander**: http://localhost:8081 (with `make tools`)

## Environment Setup

### Docker Environment (.env.docker)

```bash
# Database Configuration (Docker services)
DB_NAME=vervilure_db
DB_USER=admin  
DB_PASSWORD=admin123
DB_HOST=db
DB_PORT=5432

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Django Configuration
SECRET_KEY=docker-development-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,web

# Email Configuration (Mailpit for testing)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=mailpit
EMAIL_PORT=1025
EMAIL_USE_TLS=False

# Google OAuth (get from Google Cloud Console)
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_SECRET=GOCSPX-your-google-client-secret

# Security & Performance
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

### Local Environment (.env.local)

```bash
# Database Configuration (Local PostgreSQL)
DB_NAME=vervilure_local
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Django Configuration
SECRET_KEY=your-local-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH_SECRET=your-google-client-secret
```

## Google OAuth Setup

### 1. Create Google OAuth Application

1. **Go to Google Cloud Console**: https://console.cloud.google.com/
2. **Create or select a project**
3. **Enable APIs**:
   ```
   - Google+ API (for profile info)
   - People API (for detailed information)
   - Gmail API (optional for email operations)
   ```

4. **Create OAuth Credentials**:
   - Navigate to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth 2.0 Client ID"
   - Choose "Web application"

5. **Configure OAuth Settings**:
   ```
   Name: Vervilure Development
   
   Authorized JavaScript origins:
   - http://localhost:8000
   - http://127.0.0.1:8000
   
   Authorized redirect URIs:
   - http://localhost:8000/accounts/google/login/callback/
   - http://127.0.0.1:8000/accounts/google/login/callback/
   ```

6. **Copy credentials**:
   - Client ID
   - Client Secret

### 2. Configure Application

```bash
# Add to .env file
GOOGLE_OAUTH_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_OAUTH_SECRET=GOCSPX-abcdefghijklmnop
```

### 3. Initialize OAuth

```bash
# Start services
make up

# Setup OAuth in Django
make setup-oauth

# Clean up duplicate configurations (if needed)
make cleanup-oauth-duplicates
```

### 4. Test OAuth

```bash
# Comprehensive Google OAuth testing
make test-google-oauth

# Test JWT authentication flow
make test-jwt-auth

# Test email functionality
make test-email
```

## API Documentation

### Authentication Endpoints

```bash
# === Core Authentication ===
POST /api/v1/auth/register/           # User registration
POST /api/v1/auth/login/              # Login with email/password
POST /api/v1/auth/logout/             # Logout + blacklist token
POST /api/v1/auth/google/             # Google OAuth authentication

# === JWT Token Management ===
POST /api/v1/auth/jwt/                # Get JWT tokens
POST /api/v1/auth/jwt/refresh/        # Refresh access token
POST /api/v1/auth/jwt/verify/         # Verify token
POST /api/v1/auth/jwt/blacklist/      # Blacklist token

# === Email Verification ===
POST /api/v1/auth/email/verify/       # Email verification
POST /api/v1/auth/email/resend-verification/ # Resend verification

# === Password Management ===
POST /api/v1/auth/password/reset/     # Password reset
POST /api/v1/auth/password/reset/confirm/ # Confirm new password
```

### User Management Endpoints

```bash
# === Profile Management ===
GET    /api/v1/users/profile/         # Get profile
PATCH  /api/v1/users/profile/         # Update profile
POST   /api/v1/users/password/change/ # Change password

# === Address Management ===
GET    /api/v1/users/addresses/       # List addresses
POST   /api/v1/users/addresses/       # Create address
PATCH  /api/v1/users/addresses/{id}/  # Update address
DELETE /api/v1/users/addresses/{id}/  # Delete address
```

### Authentication Flow Examples

#### 1. User Registration
```bash
POST /api/v1/auth/register/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+380501234567",
    "marketing_consent": true
}

# Response:
{
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "message": "Registration successful. Please check your email for verification."
}
```

#### 2. Email/Password Login
```bash
POST /api/v1/auth/login/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "SecurePass123!"
}

# Response:
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe"
    }
}
```

#### 3. Google OAuth Authentication
```bash
# Frontend redirects to:
GET /accounts/google/login/

# Or direct Google token exchange for JWT:
POST /api/v1/auth/google/
Content-Type: application/json

{
    "access_token": "ya29.a0AfH6SMC..."
}

# Response:
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 2,
        "email": "google.user@gmail.com",
        "first_name": "Google",
        "last_name": "User",
        "is_email_verified": true
    }
}
```

## Development Commands

### Docker Management
```bash
make build              # Build Docker images
make up                 # Start all core services
make down               # Stop all services  
make restart            # Restart services
make logs               # View logs for all services
make logs-web           # Logs for specific service
make ps                 # Container status
```

### Django Operations
```bash
make shell              # Django shell_plus
make migrate            # Run migrations
make makemigrations     # Create migrations
make superuser          # Create superuser
make collectstatic      # Collect static files
make manage cmd="..."   # Execute Django commands
```

### Testing & Quality Assurance
```bash
make test               # Run all tests
make test-fast          # Fast tests (no migrations)
make test-coverage      # Tests with coverage report
make test-file path=... # Test specific file

# Code Quality
make format             # Code formatting (Black + isort)
make lint               # Linting (flake8, mypy)
make format-check       # Check formatting
make deps-check         # Check dependencies
```

### Authentication Testing
```bash
make test-jwt-auth      # Test JWT authentication
make test-google-oauth  # Test Google OAuth
make test-email         # Test email functionality
make setup-mailpit     # Setup email testing
```

### Development Tools
```bash
make tools              # Start pgAdmin + Redis Commander
make tools-down         # Stop development tools
make db-shell           # PostgreSQL shell (psql)
make redis-cli          # Redis CLI
make dev-shell          # Interactive shell in container
```

### Monitoring & Debugging
```bash
make health             # Health check all services
make monitor            # Monitor system resources
make watch-logs         # Watch logs with filtering
make quick-test         # Quick smoke tests
make env-info           # Environment information
```

### Utilities & Maintenance
```bash
make clean              # Clean Docker resources
make reset-db           # Reset database
make reset-cache        # Clean all caches
make rebuild            # Complete container rebuild
make urls               # List all services
```

### Production Readiness
```bash
make prod-check         # Check production readiness
make ci-test            # Run tests in CI mode
make ci-lint            # Linting in CI mode
```

## Testing

### Running Tests

```bash
# All tests
make test

# With coverage analysis
make test-coverage

# Fast tests
make test-fast

# Specific module
make test-file path=tests/test_authentication.py
```

### Coverage Report

Project maintains 70%+ code coverage:

```bash
# Generate HTML report
make test-coverage

# Report available at htmlcov/index.html
```

### OAuth Testing

Platform includes comprehensive OAuth testing:

```bash
# Test Google OAuth configuration
make test-google-oauth

# Test JWT authentication flows
make test-jwt-auth

# Test email functionality  
make test-email
```

## Security Features

### Implemented Security Measures
- **JWT Authentication** with automatic token rotation
- **Rate Limiting** on authentication endpoints
- **CORS Configuration** for frontend integration  
- **Token Blacklisting** on logout
- **Email Verification** for new accounts
- **OAuth Security** with state validation
- **Password Validation** with complexity requirements
- **Security Headers** (CSRF, XFrame, etc.)
- **Dependency Scanning** with safety tool

### Password Requirements
- Minimum 8 characters
- Upper and lowercase letters
- Numbers and special characters
- Django password validators

## Production Deployment

### Environment Variables for Production
```bash
# Core Django Settings
DEBUG=False
SECRET_KEY=your-strong-production-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (Recommended PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
DB_HOST=your-db-host
DB_PORT=5432
DB_NAME=vervilure_prod
DB_USER=vervilure_user
DB_PASSWORD=strong-db-password

# Redis (Cache + Celery)
REDIS_URL=redis://your-redis-host:6379/0
CELERY_BROKER_URL=redis://your-redis-host:6379/1

# Email (Production SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_USE_TLS=True

# Google OAuth (Production credentials)
GOOGLE_OAUTH_CLIENT_ID=your-prod-client-id
GOOGLE_OAUTH_SECRET=your-prod-client-secret

# Security
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
```

### Security Checklist for Production
- [ ] `DEBUG=False`
- [ ] Strong `SECRET_KEY` (50+ characters)
- [ ] Proper `ALLOWED_HOSTS`
- [ ] HTTPS configuration
- [ ] Secure headers configuration  
- [ ] CORS settings review
- [ ] Database backup strategy
- [ ] Monitoring and logging
- [ ] Rate limiting configuration
- [ ] Firewall configuration

### Docker Production Build
```bash
# Multi-stage production build
docker build --target production -t vervilure:prod .

# Production docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

## CI/CD Pipeline

Project includes complete GitHub Actions pipeline:

### Pipeline Stages
1. **Foundation Setup** - Environment and dependencies
2. **Test Matrix** - Parallel testing of different modules
3. **Full Test Suite** - Comprehensive testing
4. **Quality & Security Audit** - Code quality and security scan
5. **Coverage Analysis** - Coverage analysis with threshold check

### CI/CD Configuration
```yaml
# .github/workflows/Vervelure_CI.yml
# - Automatic testing on PR/push
# - Code quality checks
# - Security vulnerability scanning  
# - Coverage reporting
# - Multi-environment testing
```

## Troubleshooting

### Common Issues

**Docker Build Fails**:
```bash
make clean && make rebuild
# or
make reset-cache && make build
```

**Database Connection Issues**:
```bash
make reset-db
# or check status:
make health
```

**OAuth Not Working**:
```bash
make cleanup-oauth-duplicates
make test-google-oauth
```

**Environment Detection Issues**:
```bash
make env-info  # Check current configuration
make status    # Status of all services
```

**Testing Issues**:
```bash
# Check test environment
make quick-test

# Reset test database
make test cmd="--reuse-db --create-db"
```

### Getting Help

1. **Check status**: `make status`
2. **View logs**: `make logs` or `make logs-web`
3. **Validate configuration**: `make health`
4. **Reset environment**: `make reset-all` (nuclear option)
5. **Check documentation**: `make urls` for endpoint list

### Debug Commands
```bash
# Detailed environment information
make env-info

# Interactive shell in container
make dev-shell

# Resource monitoring
make monitor

# Quick smoke tests
make quick-test
```

## Roadmap

### Next Development Phases

#### Phase 1: Core E-commerce (Q2 2025)
- [ ] Product Catalog with search and filtering
- [ ] Shopping Cart functionality
- [ ] Order Management System
- [ ] Payment Integration (Stripe)

#### Phase 2: Advanced Features (Q3 2025)  
- [ ] Product Reviews and Ratings
- [ ] Wishlist functionality
- [ ] Loyalty Program
- [ ] Email Marketing Integration

#### Phase 3: Performance & Scaling (Q4 2025)
- [ ] Caching optimization
- [ ] Database performance tuning  
- [ ] CDN integration
- [ ] Load balancing setup

## Contributing

1. **Fork repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Run tests**: `make test`
4. **Check code quality**: `make lint && make format-check`
5. **Commit changes**: `git commit -m 'Add amazing feature'`
6. **Push to branch**: `git push origin feature/amazing-feature`
7. **Open Pull Request**

### Code Requirements
- 70%+ test coverage
- Pass all CI checks
- Code quality standards (Black, isort, flake8)
- Comprehensive documentation
- Type hints for all functions

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Need help?** Check the troubleshooting section or run `make help` for available commands.
