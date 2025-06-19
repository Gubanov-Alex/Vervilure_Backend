"""Django settings for Vervilure project."""

import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List

import dj_database_url
from dotenv import load_dotenv

# Environment detection
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
IS_CI = bool(os.environ.get("GITHUB_ACTIONS") or os.environ.get("ENVIRONMENT") == "ci")
IS_LOCAL_DOCKER = "db" in os.environ.get("DB_HOST", "")
IS_TESTING = "test" in sys.argv or "pytest" in sys.modules

# CRITICAL: Clear DATABASE_URL in CI to force individual settings
if IS_CI and "DATABASE_URL" in os.environ:
    print(f"[CI] Removing DATABASE_URL: {os.environ['DATABASE_URL']}")
    del os.environ["DATABASE_URL"]

# Load environment variables
if IS_CI:
    # CI environment gets config from GitHub Actions env
    pass
elif os.path.exists(".env"):
    load_dotenv(".env")
else:
    load_dotenv(".env_default")

BASE_DIR = Path(__file__).resolve().parent.parent

# Security Configuration
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if IS_CI or IS_TESTING:
        SECRET_KEY = "django-insecure-ci-test-key-for-testing-only"
    else:
        raise ValueError("SECRET_KEY environment variable is required in production")

DEBUG: bool = os.environ.get("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS: List[str] = [
    host.strip() for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()
]
if DEBUG or IS_TESTING or IS_CI:
    ALLOWED_HOSTS.extend(["testserver", ".testserver"])

# Application Configuration
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
    # "src.apps.cart",
    # "src.apps.catalog",
    # "src.apps.loyalty",
    # "src.apps.orders",
    # "src.apps.reviews",
    # "src.apps.wishlist",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Middleware Configuration
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

AUTH_USER_MODEL = "accounts.User"
ROOT_URLCONF = "config.urls"

# Template Configuration
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


# Database Configuration
def get_database_config() -> Dict[str, Any]:
    """Get database configuration with environment-specific optimizations."""
    database_url = os.environ.get("DATABASE_URL")

    base_options = {
        "connect_timeout": 10,
        "application_name": "vervilure_backend",
    }

    if IS_CI:
        print("[DEBUG] CI detected: Using individual DB settings")
        return {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.environ.get("DB_NAME", "test_db"),
                "USER": os.environ.get("DB_USER", "admin"),
                "PASSWORD": os.environ.get("DB_PASSWORD", "admin_password"),
                "HOST": os.environ.get("DB_HOST", "localhost"),
                "PORT": os.environ.get("DB_PORT", "5433"),
                "OPTIONS": {
                    **base_options,
                    "sslmode": "disable",
                },
                "CONN_MAX_AGE": 0,
                "CONN_HEALTH_CHECKS": False,
                "ATOMIC_REQUESTS": True,
            }
        }

    if database_url:
        config = dj_database_url.parse(database_url, conn_max_age=600)
        config["OPTIONS"] = {
            **base_options,
            "sslmode": "prefer" if not DEBUG else "disable",
        }
        return {"default": config}

    db_password = os.environ.get("DB_PASSWORD")
    if not db_password and not IS_TESTING:
        raise ValueError("DB_PASSWORD is required")

    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "vervilure"),
            "USER": os.environ.get("DB_USER", "admin"),
            "PASSWORD": db_password or "admin_password",
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "OPTIONS": {
                **base_options,
                "sslmode": "disable" if DEBUG else "prefer",
                "options": "-c log_statement=all" if DEBUG else "",
            },
            "CONN_MAX_AGE": 300 if DEBUG else 600,
            "CONN_HEALTH_CHECKS": True,
        }
    }


DATABASES = get_database_config()

# CI/Testing specific database optimizations
if IS_CI or IS_TESTING:
    DATABASES["default"].update(
        {
            "TEST": {
                "NAME": "test_vervilure_ci",
                "CHARSET": "utf8",
                "COLLATION": "utf8_general_ci",
            }
        }
    )

    # Disable migrations for faster CI if requested
    class DisableMigrations:
        def __contains__(self, item):
            return True

        def __getitem__(self, item):
            return None

    if os.environ.get("DISABLE_MIGRATIONS", "False").lower() == "true":
        MIGRATION_MODULES = DisableMigrations()

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Django Allauth Configuration
SITE_ID = 1

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 7

# URLs Configuration
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_SECRET = os.environ.get("GOOGLE_OAUTH_SECRET", "")

# Social Account Providers Configuration
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
        "APP": (
            {
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "secret": GOOGLE_OAUTH_SECRET,
                "key": "",
            }
            if GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_SECRET
            else {}
        ),
    }
}

SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "mandatory"
SOCIALACCOUNT_AUTO_SIGNUP = True

# JWT Configuration
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_TYPE_CLAIM": "token_type",
}

# REST Framework Configuration
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
    ]
    + (["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "login": "5/min",
        "registration": "3/min",
        "password_change": "3/hour",
        "password_reset": "3/hour",
    },
}

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static Files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

# Media Files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Redis Configuration
def get_redis_config() -> Dict[str, Any]:
    """Get Redis configuration with CI fallback."""
    if IS_CI and not os.environ.get("REDIS_HOST"):
        # Use dummy cache for CI if Redis not available
        return {
            "default": {
                "BACKEND": "django.core.cache.backends.dummy.DummyCache",
            }
        }

    redis_url = (
        f"redis://{os.environ.get('REDIS_HOST', 'localhost')}:"
        f"{os.environ.get('REDIS_PORT', '6379')}/"
        f"{os.environ.get('REDIS_DB', '1')}"
    )

    return {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": redis_url,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "PASSWORD": os.environ.get("REDIS_PASSWORD"),
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


CACHES = get_redis_config()

# Celery Configuration
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60


# Email Configuration
def get_email_config() -> Dict[str, Any]:
    """Get email configuration with environment-specific settings."""
    if IS_CI or IS_TESTING:
        return {
            "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
            "DEFAULT_FROM_EMAIL": "Vervilure Test <test@vervilure.local>",
        }

    if os.environ.get("USE_MAILPIT", "True").lower() == "true":
        return {
            "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "EMAIL_HOST": os.environ.get("EMAIL_HOST", "mailpit"),
            "EMAIL_PORT": int(os.environ.get("EMAIL_PORT", 1025)),
            "EMAIL_HOST_USER": "",
            "EMAIL_HOST_PASSWORD": "",
            "EMAIL_USE_TLS": False,
            "EMAIL_USE_SSL": False,
            "DEFAULT_FROM_EMAIL": "Vervilure <noreply@vervilure.local>",
        }

    return {
        "EMAIL_BACKEND": os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"),
        "EMAIL_HOST": os.environ.get("EMAIL_HOST", "smtp.example.com"),
        "EMAIL_PORT": int(os.environ.get("EMAIL_PORT", "587")),
        "EMAIL_HOST_USER": os.environ.get("EMAIL_HOST_USER", ""),
        "EMAIL_HOST_PASSWORD": os.environ.get("EMAIL_HOST_PASSWORD", ""),
        "EMAIL_USE_TLS": os.environ.get("EMAIL_USE_TLS", "True").lower() == "true",
        "DEFAULT_FROM_EMAIL": os.environ.get("DEFAULT_FROM_EMAIL", "Vervilure <noreply@example.com>"),
    }


# Apply email configuration
email_config = get_email_config()
globals().update(email_config)

MAILPIT_URL = os.environ.get("MAILPIT_URL", "http://mailpit:8025/api/v1/info")
SITE_NAME = os.environ.get("SITE_NAME", "Vervilure")
SERVER_EMAIL = globals().get("DEFAULT_FROM_EMAIL", "Vervilure <noreply@vervilure.local>")

# Frontend Configuration
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# Stripe Configuration
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True

# Security Settings for Production
if not DEBUG and not IS_CI:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = []


# Logging Configuration
def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration optimized for environment."""
    base_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
                "style": "{",
            },
            "simple": {
                "format": "{levelname} {message}",
                "style": "{",
            },
            "ci": {
                "format": "[{levelname}] {name}: {message}",
                "style": "{",
            },
        },
        "handlers": {
            "console": {
                "level": "DEBUG" if DEBUG else "INFO",
                "class": "logging.StreamHandler",
                "formatter": "ci" if IS_CI else "verbose",
            },
        },
        "loggers": {
            "django": {
                "handlers": ["console"],
                "level": "INFO" if IS_CI else "DEBUG",
                "propagate": False,
            },
            "django.db.backends": {
                "handlers": ["console"],
                "level": "WARNING" if IS_CI else "INFO",
                "propagate": False,
            },
            "allauth": {
                "handlers": ["console"],
                "level": "ERROR" if IS_CI else "INFO",
                "propagate": False,
            },
            "email_testing": {
                "handlers": ["console"],
                "level": "DEBUG",
                "propagate": False,
            },
            "django.core.mail": {
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

    # Add file logging only in development (not CI)
    if not IS_CI and not IS_TESTING:
        os.makedirs(BASE_DIR / "logs", exist_ok=True)
        if (BASE_DIR / "logs").exists():
            base_config["handlers"]["file"] = {
                "level": "DEBUG",
                "class": "logging.FileHandler",
                "filename": BASE_DIR / "logs" / "django.log",
                "formatter": "verbose",
            }
            # Add file handler to all loggers
            for logger in base_config["loggers"].values():
                logger["handlers"].append("file")

    return base_config


LOGGING = get_logging_config()

# Create logs directory
if not IS_CI:
    os.makedirs(BASE_DIR / "logs", exist_ok=True)

# Swagger Configuration
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {"Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}},
    "USE_SESSION_AUTH": False,
    "JSON_EDITOR": True,
}

# Environment-specific overrides
if IS_CI:
    # CI-specific optimizations
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",  # Faster for tests
    ]

    # Disable throttling in CI
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}

    # Simplified middleware for CI
    MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m.lower()]

    print("CI Environment detected")
    print(f"Database: {DATABASES['default']['HOST']}:{DATABASES['default']['PORT']}")
    print(f"Redis: {CACHES['default']['BACKEND']}")

elif IS_TESTING:
    # Test-specific settings
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

# Debug output
if DEBUG or IS_CI:
    print("Django settings loaded")
    print(f"Environment: {ENVIRONMENT}")
    print(f"IS_CI: {IS_CI}")
    print(f"Database URL (from env): {os.environ.get('DATABASE_URL', 'Not set')}")
    print(f"Google OAuth configured: {bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_SECRET)}")

    # Show actual database config being used
    db_config = DATABASES["default"]
    print(f"Actual database config: {db_config['NAME']}@{db_config['HOST']}:{db_config['PORT']}")

    if IS_CI:
        print("CI-specific optimizations applied:")
        print(f"- Fast password hashing: {len(PASSWORD_HASHERS) == 1}")
        print(f"- Throttling disabled: {len(REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES']) == 0}")
        print(f"- Redis backend: {CACHES['default']['BACKEND']}")
        print("- Using individual DB settings (DATABASE_URL ignored)")

        # Additional CI debug
        print("Environment variables check:")
        print(f"- DB_HOST: {os.environ.get('DB_HOST', 'NOT SET')}")
        print(f"- DB_PORT: {os.environ.get('DB_PORT', 'NOT SET')}")
        print(f"- DB_NAME: {os.environ.get('DB_NAME', 'NOT SET')}")
