"""
Django settings for Vervilure Backend project.
Production-ready configuration with multi-environment support.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List

import dj_database_url
from celery.schedules import crontab
from dotenv import load_dotenv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment detection
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"
IS_DEVELOPMENT = ENVIRONMENT == "development"
IS_CI = bool(os.environ.get("GITHUB_ACTIONS") or ENVIRONMENT == "ci")
IS_TESTING = "test" in sys.argv or "pytest" in sys.modules


def load_environment_variables():
    """Load environment variables based on current environment."""
    if IS_CI:
        print("[CONFIG] Using CI environment variables")
        return

    if IS_PRODUCTION:
        env_file = BASE_DIR / ".env"
        print("[CONFIG] Loading production environment from .env")
    else:
        # Try Docker first, then local development
        if os.path.exists(BASE_DIR / ".env.docker"):
            env_file = BASE_DIR / ".env.docker"
            print("[CONFIG] Loading Docker development environment from .env.docker")
        else:
            env_file = BASE_DIR / ".env.local"
            print("[CONFIG] Loading local development environment from .env.local")

    if env_file.exists():
        load_dotenv(env_file)
        print(f"[CONFIG] Environment loaded from {env_file.name}")
    elif not IS_TESTING:
        raise FileNotFoundError(f"Environment file {env_file} not found")


# Load environment variables
load_environment_variables()

# =============================================================================
# CORE DJANGO SETTINGS
# =============================================================================

# Security
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if IS_CI or IS_TESTING:
        SECRET_KEY = "django-insecure-ci-test-key-only"
    else:
        raise ValueError("SECRET_KEY environment variable is required")

DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

if DEBUG or IS_TESTING:
    ALLOWED_HOSTS.extend(["testserver", ".testserver", "0.0.0.0"])

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_redis",
    "drf_yasg",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]

LOCAL_APPS = [
    "src.apps.accounts",
    # Add your other apps here
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "src" / "core" / "templates",
            BASE_DIR / "src" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

def get_database_config():
    """Configure database based on environment."""

    # Production: Use DATABASE_URL if available
    database_url = os.environ.get("DATABASE_URL")
    if database_url and IS_PRODUCTION:
        config = dj_database_url.parse(database_url, conn_max_age=600)
        config["OPTIONS"] = {
            "sslmode": "require",
            "application_name": "vervilure_backend",
        }
        return {"default": config}

    # Standard PostgreSQL configuration
    ssl_mode = os.environ.get("DATABASE_SSL_MODE", "require" if IS_PRODUCTION else "disable")

    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "vervilure_db"),
            "USER": os.environ.get("DB_USER", "admin"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "admin_password"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "OPTIONS": {
                "sslmode":  ssl_mode,
                "application_name": "vervilure_backend",
            },
            "CONN_MAX_AGE": 600 if IS_PRODUCTION else 300,
            "CONN_HEALTH_CHECKS": True,
            "ATOMIC_REQUESTS": True,
        }
    }


DATABASES = get_database_config()

# Test database optimizations
if IS_TESTING or IS_CI:
    DATABASES["default"]["TEST"] = {
        "NAME": "test_vervilure",
        "OPTIONS": {"sslmode": "disable"},
    }

# =============================================================================
# AUTHENTICATION & AUTHORIZATION
# =============================================================================

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# =============================================================================
# DJANGO ALLAUTH CONFIGURATION
# =============================================================================

SITE_ID = 1

# Account settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 7

# Social account settings
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "mandatory"
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_STORE_TOKENS = True

# Google OAuth configuration
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_SECRET = os.environ.get("GOOGLE_OAUTH_SECRET", "")

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
        "APP": {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "secret": GOOGLE_OAUTH_SECRET,
            "key": "",
        } if GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_SECRET else {},
    }
}

# URLs
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# =============================================================================
# JWT CONFIGURATION
# =============================================================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("ACCESS_TOKEN_LIFETIME", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("REFRESH_TOKEN_LIFETIME", "1440"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": os.environ.get("JWT_ALGORITHM", "HS256"),
    "SIGNING_KEY": os.environ.get("JWT_SECRET_KEY", SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_TYPE_CLAIM": "token_type",
}

# =============================================================================
# REST FRAMEWORK CONFIGURATION
# =============================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ] + (["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
    "DEFAULT_THROTTLE_CLASSES": [] if IS_CI else [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {} if IS_CI else {
        "anon": "100/hour",
        "user": "1000/hour",
        "login": "5/min",
        "registration": "3/min",
        "password_reset": "3/hour",
    },
}

# =============================================================================
# CACHE CONFIGURATION (REDIS)
# =============================================================================

def get_cache_config():
    """Configure cache based on environment."""
    if IS_CI and not os.environ.get("REDIS_HOST"):
        return {
            "default": {
                "BACKEND": "django.core.cache.backends.dummy.DummyCache",
            }
        }

    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = os.environ.get("REDIS_PORT", "6379")
    redis_db = os.environ.get("REDIS_DB", "1")
    redis_password = os.environ.get("REDIS_PASSWORD", "")

    redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}" if redis_password else f"redis://{redis_host}:{redis_port}/{redis_db}"

    return {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": redis_url,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": 20,
                    "retry_on_timeout": True,
                    "socket_connect_timeout": 5,
                    "socket_timeout": 5,
                },
            },
            "KEY_PREFIX": "vervilure",
            "TIMEOUT": 300,
        }
    }


CACHES = get_cache_config()

# =============================================================================
# CELERY CONFIGURATION
# =============================================================================

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True

# Environment-specific Celery settings
if IS_TESTING:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"
else:
    CELERY_TASK_ALWAYS_EAGER = False
    CELERY_TASK_TIME_LIMIT = 30 * 60
    CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
    CELERY_TASK_ACKS_LATE = True
    CELERY_TASK_REJECT_ON_WORKER_LOST = True
    CELERY_WORKER_PREFETCH_MULTIPLIER = 1
    CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    "cleanup-expired-tokens": {
        "task": "src.apps.accounts.tasks.cleanup_expired_tokens",
        "schedule": 3600,
    },
    "cleanup-expired-accounts": {
        "task": "src.apps.accounts.tasks.cleanup_expired_accounts",
        "schedule": crontab(hour=2, minute=0),
    },
}

# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================

def get_email_config():
    """Configure email based on environment."""
    if IS_TESTING or IS_CI:
        return {
            "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
            "DEFAULT_FROM_EMAIL": "Vervilure Test <test@vervilure.local>",
        }

    # Use Mailpit for development
    if DEBUG and os.environ.get("USE_MAILPIT", "true").lower() == "true":
        return {
            "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "EMAIL_HOST": os.environ.get("EMAIL_HOST", "mailpit"),
            "EMAIL_PORT": int(os.environ.get("EMAIL_PORT", "1025")),
            "EMAIL_HOST_USER": "",
            "EMAIL_HOST_PASSWORD": "",
            "EMAIL_USE_TLS": False,
            "EMAIL_USE_SSL": False,
            "DEFAULT_FROM_EMAIL": "Vervilure <noreply@vervilure.local>",
        }

    # Production email configuration
    return {
        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "EMAIL_HOST": os.environ.get("EMAIL_HOST", "smtp.gmail.com"),
        "EMAIL_PORT": int(os.environ.get("EMAIL_PORT", "587")),
        "EMAIL_HOST_USER": os.environ.get("EMAIL_HOST_USER", ""),
        "EMAIL_HOST_PASSWORD": os.environ.get("EMAIL_HOST_PASSWORD", ""),
        "EMAIL_USE_TLS": os.environ.get("EMAIL_USE_TLS", "True").lower() == "true",
        "EMAIL_USE_SSL": os.environ.get("EMAIL_USE_SSL", "False").lower() == "true",
        "DEFAULT_FROM_EMAIL": os.environ.get("DEFAULT_FROM_EMAIL", "Vervilure <noreply@vervilure.com>"),
    }


# Apply email configuration
email_config = get_email_config()
for key, value in email_config.items():
    globals()[key] = value

# Email settings
SERVER_EMAIL = globals().get("DEFAULT_FROM_EMAIL")
SITE_NAME = os.environ.get("SITE_NAME", "Vervilure")

# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise configuration for production
if IS_PRODUCTION:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# =============================================================================
# CORS & CSRF CONFIGURATION
# =============================================================================

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# CORS settings
CORS_ALLOWED_ORIGINS = [
    FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

if IS_PRODUCTION:
    # Add production URLs
    production_urls = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    CORS_ALLOWED_ORIGINS.extend([url.strip() for url in production_urls if url.strip()])

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG and not IS_PRODUCTION

# CSRF settings
CSRF_TRUSTED_ORIGINS = [
    BACKEND_URL,
    FRONTEND_URL,
]

csrf_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
CSRF_TRUSTED_ORIGINS.extend([url.strip() for url in csrf_origins if url.strip()])

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

if IS_PRODUCTION:
    # Production security settings
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() == "true"
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"
else:
    # Development security settings
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    X_FRAME_OPTIONS = "SAMEORIGIN"

# =============================================================================
# THIRD-PARTY INTEGRATIONS
# =============================================================================

# Stripe configuration
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG" if DEBUG else "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple" if IS_CI else "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING" if IS_PRODUCTION else "INFO",
            "propagate": False,
        },
        "src.apps": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# =============================================================================
# SWAGGER/API DOCUMENTATION
# =============================================================================

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT authorization header using the Bearer scheme. Example: 'Bearer {token}'",
        }
    },
    "USE_SESSION_AUTH": False,
    "JSON_EDITOR": True,
    "SUPPORTED_SUBMIT_METHODS": ["get", "post", "put", "delete", "patch"],
    "OPERATIONS_SORTER": "alpha",
    "TAGS_SORTER": "alpha",
    "DOC_EXPANSION": "list",
    "DEEP_LINKING": True,
    "PERSIST_AUTH": True,
}

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# ENVIRONMENT-SPECIFIC OPTIMIZATIONS
# =============================================================================

# CI optimizations
if IS_CI:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m.lower()]

# Development optimizations
#  Development logging
    os.makedirs(BASE_DIR / "logs", exist_ok=True)

# =============================================================================
# DEBUG OUTPUT
# =============================================================================

if DEBUG or IS_CI:
    print(f"[SETTINGS] Environment: {ENVIRONMENT}")
    print(f"[SETTINGS] Debug: {DEBUG}")
    print(f"[SETTINGS] Database: {DATABASES['default']['NAME']}@{DATABASES['default']['HOST']}")
    print(f"[SETTINGS] Cache backend: {CACHES['default']['BACKEND']}")
    print(f"[SETTINGS] Google OAuth configured: {bool(GOOGLE_OAUTH_CLIENT_ID)}")
    print(f"[SETTINGS] Allowed hosts: {ALLOWED_HOSTS}")
    print(f"[SETTINGS] CORS origins: {CORS_ALLOWED_ORIGINS}")
    print(f"[SETTINGS] CSRF trusted origins: {CSRF_TRUSTED_ORIGINS}")
