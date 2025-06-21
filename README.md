# Vervilure E-commerce Platform

A comprehensive Django-based e-commerce platform providing a scalable and robust solution for online retail operations.

## Project Status
🚧 **Active Development** 🚧

Core authentication, user management, and OAuth integration are implemented. Platform architecture is production-ready with comprehensive testing and monitoring capabilities.

## About This Project

Modern e-commerce platform built with Django REST Framework, featuring secure JWT authentication, Google OAuth integration, robust API design, and full Docker support for development and production environments.

## Architecture Overview

### Tech Stack
- **Backend**: Django 5.1 + Django REST Framework
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **Task Queue**: Celery
- **Authentication**: JWT + Google OAuth
- **API Documentation**: Swagger/OpenAPI
- **Testing**: pytest + coverage
- **Deployment**: Docker + docker-compose

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
│   │   ├── accounts/         # User management & authentication
│   │   │   ├── models.py     # User model with Google OAuth
│   │   │   ├── views.py      # Auth ViewSets (JWT + OAuth)
│   │   │   ├── serializers.py # API serializers
│   │   │   ├── auth_urls.py  # Authentication endpoints
│   │   │   ├── user_urls.py  # User management endpoints
│   │   │   └── management/   # Django commands
│   │   │
│   │   ├── catalog/          # Product catalog (planned)
│   │   ├── cart/             # Shopping cart (planned)
│   │   ├── orders/           # Order management (planned)
│   │   └── reviews/          # Product reviews (planned)
│   │
│   ├── api/                  # API routing
│   └── core/                 # Shared utilities
│       ├── middleware/       # Custom middleware
│       ├── mixins/           # Reusable mixins
│       ├── testing/          # Testing utilities
│       └── utils/            # Helper functions
│
├── tests/                    # Test suite
│   ├── conftest.py           # Pytest configuration
│   └── test_*.py             # Test modules
│
├── docs/                     # Documentation
│   └── architecture/         # Architecture documentation
│
├── docker-compose.yml        # Development environment
├── Dockerfile               # Application container
├── Makefile                 # Development commands
├── pyproject.toml           # Python dependencies (Poetry)
└── poetry.lock              # Locked dependencies
```

## Key Features

### ✅ Implemented
- 🔐 **JWT Authentication** with refresh token rotation
- 🔑 **Google OAuth Integration** via django-allauth
- 👤 **User Management** with profile, addresses, preferences
- 📧 **Email System** with Mailpit for development
- 🔒 **Security Features** (rate limiting, blacklist, CORS)
- 🐳 **Docker Development Environment**
- 📊 **Comprehensive Testing** (OAuth, JWT, edge cases)
- 🔧 **Development Tools** (pgAdmin, Redis Commander)
- 📝 **API Documentation** (Swagger/OpenAPI)

### 🚧 In Development
- 📦 Product catalog with categories and search
- 🛒 Shopping cart and order management
- 💳 Payment processing with Stripe
- ⚡ Asynchronous task processing
- 🔄 CI/CD pipeline with GitHub Actions

## Prerequisites

- **Docker** and **Docker Compose** 20.0+
- **Git**
- **Make** (optional, but recommended)

## Quick Start

### 1. Clone and Initialize

```bash
git clone <repository-url>
cd Vervilure_Backend
make init
```

This creates two environment templates:
- `.env.docker` - for Docker development
- `.env.local` - for local development

### 2. Choose Development Environment

#### Option A: Docker Development (Recommended)
```bash
make setup-docker
```

#### Option B: Local Development
```bash
make setup-local
```

### 3. Create Superuser
```bash
make superuser
```

### 4. Access Services
- **Django**: http://localhost:8000
- **API Documentation**: http://localhost:8000/swagger/
- **Admin Panel**: http://localhost:8000/admin/
- **Mailpit**: http://localhost:8025

## Environment Setup Guides

### Local Environment Setup (.env.local)

For development without Docker, create `.env.local`:

```bash
# Database Configuration
DB_NAME=vervilure_local
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Redis Configuration  
REDIS_URL=redis://localhost:6379/0

# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email Configuration (for local testing)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Google OAuth (see OAuth setup guide below)
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH_SECRET=your-google-client-secret
```

**Requirements for local setup:**
```bash
# Install PostgreSQL
brew install postgresql  # macOS
sudo apt install postgresql postgresql-contrib  # Ubuntu

# Install Redis
brew install redis  # macOS
sudo apt install redis-server  # Ubuntu

# Install Python dependencies
poetry install
```

### Docker Environment Setup (.env.docker)

For Docker development, create `.env.docker`:

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
SECRET_KEY=docker-development-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,web

# Email Configuration (Mailpit)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=mailpit
EMAIL_PORT=1025
EMAIL_USE_TLS=False

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH_SECRET=your-google-client-secret
```

## Google OAuth Setup Guide

### 1. Create Google OAuth Application

1. **Go to Google Cloud Console**: https://console.cloud.google.com/
2. **Create or select a project**
3. **Enable Google+ API**:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Google+ API" and enable it
   - Also enable "People API" for profile information

4. **Create OAuth Credentials**:
   - Go to "APIs & Services" → "Credentials"
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

6. **Save credentials** and copy:
   - Client ID
   - Client Secret

### 2. Configure Application

Add credentials to your environment file:

```bash
# In .env.docker or .env.local
GOOGLE_OAUTH_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_OAUTH_SECRET=GOCSPX-abcdefghijklmnop
```

### 3. Initialize OAuth Configuration

```bash
# Start services
make up

# Setup OAuth configuration in Django
make setup-oauth
```

### 4. Test OAuth Integration

```bash
# Run comprehensive OAuth tests
make test-google-oauth

# Test JWT authentication flow
make test-jwt-auth
```

### 5. OAuth Endpoints

Once configured, these endpoints become available:

```
# OAuth URLs
GET  /accounts/google/login/          # Initiate Google OAuth
GET  /accounts/google/login/callback/ # OAuth callback
POST /api/v1/auth/google/             # Exchange Google token for JWT

# JWT Endpoints  
POST /api/v1/auth/register/           # User registration
POST /api/v1/auth/login/              # Email/password login
POST /api/v1/auth/refresh/            # Refresh JWT tokens
POST /api/v1/auth/logout/             # Logout and blacklist tokens
```

## Development Commands

### Docker Management
```bash
make build              # Build Docker images
make up                 # Start all services  
make down               # Stop all services
make restart            # Restart services
make logs               # View service logs
make status             # Check service status
```

### Django Operations
```bash
make shell              # Django shell
make migrate            # Run migrations
make makemigrations     # Create migrations
make superuser          # Create admin user
make collectstatic      # Collect static files
```

### Testing & Quality
```bash
make test               # Run test suite
make test-coverage      # Run tests with coverage
make lint               # Code linting
make format             # Code formatting
```

### Development Tools
```bash
make tools              # Start pgAdmin & Redis Commander
make tools-down         # Stop development tools
make db-shell           # PostgreSQL shell
make redis-cli          # Redis CLI
```

### Authentication Testing
```bash
make test-jwt-auth      # Test JWT authentication flow
make test-google-oauth  # Test Google OAuth integration
make setup-mailpit     # Setup email testing environment
```

### Debugging & Maintenance
```bash
make debug-web          # View web container logs
make debug-celery       # View Celery logs
make clean              # Clean containers and volumes
make reset-db           # Reset database
make reset-all          # Nuclear option - reset everything
```

## Service URLs

### Development Services
- **Django Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/swagger/
- **Django Admin**: http://localhost:8000/admin/
- **Database**: localhost:5490 (external port)
- **Redis**: localhost:6379

### Development Tools (when running `make tools`)
- **pgAdmin**: http://localhost:8080
  - Login: `admin@vervilure.local` / `admin`
- **Redis Commander**: http://localhost:8081
- **Mailpit**: http://localhost:8025

## API Documentation

### Authentication Flow

1. **Register User**:
```bash
POST /api/v1/auth/register/
{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
}
```

2. **Login with Email/Password**:
```bash
POST /api/v1/auth/login/
{
    "email": "user@example.com", 
    "password": "SecurePass123!"
}
```

3. **Google OAuth Login**:
```bash
# Frontend redirects to:
GET /accounts/google/login/

# Or exchange Google token directly:
POST /api/v1/auth/google/
{
    "access_token": "google-access-token"
}
```

### User Management

```bash
# Get user profile
GET /api/v1/users/profile/

# Update profile
PATCH /api/v1/users/profile/
{
    "first_name": "Updated Name"
}

# Manage addresses
GET /api/v1/users/addresses/
POST /api/v1/users/addresses/
```

## Testing

### Running Tests

```bash
# All tests
make test

# With coverage
make test-coverage

# Specific test modules
docker-compose exec web poetry run pytest tests/test_authentication.py -v
```

### OAuth Testing

The platform includes comprehensive OAuth testing:

```bash
# Test Google OAuth configuration
make test-google-oauth

# Test JWT authentication flows  
make test-jwt-auth

# Test email functionality
make test-email
```

## Security Features

- **JWT Authentication** with automatic token rotation
- **Rate Limiting** on authentication endpoints
- **CORS Configuration** for frontend integration
- **Token Blacklisting** on logout
- **Email Verification** for new accounts
- **OAuth Security** with state validation
- **Password Validation** with complexity requirements

## Production Considerations

### Environment Variables
Set these for production:
```bash
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=your-domain.com
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://host:port/db
```

### Security Checklist
- [ ] Set `DEBUG=False`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Set up HTTPS
- [ ] Configure secure headers
- [ ] Review CORS settings
- [ ] Set up monitoring and logging

## Troubleshooting

### Common Issues

**Docker Build Fails**:
```bash
make fix-docker
```

**Database Connection Issues**:
```bash
make reset-db
```

**OAuth Not Working**:
```bash
make cleanup-oauth-duplicates
make test-google-oauth
```

**Environment Detection Issues**:
```bash
make env-info  # Check current environment configuration
```

### Getting Help

1. **Check service status**: `make status`
2. **View logs**: `make logs` or `make debug-all`
3. **Validate configuration**: `make check-django`
4. **Reset environment**: `make reset-all` (nuclear option)

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Run tests: `make test`
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Need help?** Check the troubleshooting section or run `make help` for available commands.
