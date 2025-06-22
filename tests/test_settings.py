import os
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment detection for tests
IS_TESTING = True
IS_CI = bool(os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI") or os.environ.get("ENVIRONMENT") == "ci")
DEBUG = True

# Security settings for tests
SECRET_KEY = "test-secret-key-not-for-production-only-for-testing-12345"
ALLOWED_HOSTS = ["*"]  # Allow all hosts for testing

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
    "corsheaders",
    "drf_yasg",  # Added for API documentation
]

LOCAL_APPS = [
    "src.apps.accounts",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Minimal middleware for tests
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# URL configuration
ROOT_URLCONF = "config.urls"  # Use main URL config

# Templates for tests
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# Database for tests - SQLite in memory for maximum speed
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "OPTIONS": {
            "timeout": 20,
        },
    }
}


# Disable migrations for faster test execution
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Ultra-fast password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Cache settings for tests - use dummy cache to avoid Redis dependency
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# REST Framework settings - THROTTLING COMPLETELY DISABLED
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # CRITICAL: Completely disable throttling in tests
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
    # Test-specific settings
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "TEST_REQUEST_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# JWT settings for tests - longer lifetime for easier testing
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),  # Longer for tests
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_TYPE_CLAIM": "token_type",
    # Test-specific settings
    "UPDATE_LAST_LOGIN": False,  # Don't update last_login in tests
}

# Custom user model
AUTH_USER_MODEL = "accounts.User"

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files for tests
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files for tests
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Sites framework
SITE_ID = 1

# Email backend for tests - use in-memory backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "test@vervilure.local"

# Celery - always eager for tests (execute immediately)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Completely disable logging during tests for performance
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
    "loggers": {
        "django": {
            "handlers": ["null"],
            "level": "CRITICAL",
            "propagate": False,
        },
        "src": {
            "handlers": ["null"],
            "level": "CRITICAL",
            "propagate": False,
        },
        "rest_framework": {
            "handlers": ["null"],
            "level": "CRITICAL",
            "propagate": False,
        },
    },
}

# OAuth settings for tests
GOOGLE_OAUTH_CLIENT_ID = "test-client-id"
GOOGLE_OAUTH_SECRET = "test-secret"

# CORS settings for tests
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://testserver",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins in tests

# Django Admin settings
ADMIN_URL = "admin/"

# Security settings for tests (relaxed)
SECURE_SSL_REDIRECT = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
X_FRAME_OPTIONS = "SAMEORIGIN"

# Session settings for tests
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# CSRF settings for tests
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = ["http://testserver", "http://localhost:3000"]

# File upload settings for tests
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880

# Test-specific environment variables
os.environ["TESTING"] = "True"
os.environ["THROTTLING_DISABLED"] = "True"

# Swagger/OpenAPI settings for tests
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header"
        }
    },
    "USE_SESSION_AUTH": False,
    "JSON_EDITOR": True,
    "SUPPORTED_SUBMIT_METHODS": ["get", "post", "put", "delete", "patch"],
}

# Additional test performance optimizations
if IS_CI:
    # CI-specific optimizations

    # Even faster password hashing
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

    # Disable debug toolbar and other dev tools
    DEBUG = False

    # Minimal middleware
    MIDDLEWARE = [
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
    ]

    # Disable file logging completely
    LOGGING["handlers"] = {"null": {"class": "logging.NullHandler"}}

    print("🚀 CI-optimized test settings loaded")
else:
    print("🧪 Local test settings loaded")

# Ensure throttling is completely disabled
assert REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] == []
assert REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] == {}

print("✅ Throttling completely disabled for tests")
print(f"📊 Database: {DATABASES['default']['NAME']}")
print(f"💾 Cache: {CACHES['default']['BACKEND']}")
print(f"🔐 Password hasher: {PASSWORD_HASHERS[0]}")
print(f"📧 Email backend: {EMAIL_BACKEND}")
print(f"🏃 Celery eager: {CELERY_TASK_ALWAYS_EAGER}")

# Verify critical test settings
critical_settings = {
    "SECRET_KEY": bool(SECRET_KEY),
    "THROTTLING_DISABLED": len(REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]) == 0,
    "FAST_PASSWORDS": "MD5" in PASSWORD_HASHERS[0],
    "MEMORY_DB": DATABASES["default"]["NAME"] == ":memory:",
    "DUMMY_CACHE": "dummy" in CACHES["default"]["BACKEND"].lower(),
}

print("🔍 Critical test settings verification:")
for setting, status in critical_settings.items():
    status_icon = "✅" if status else "❌"
    print(f"  {status_icon} {setting}: {status}")

# Fail fast if critical settings are wrong
if not all(critical_settings.values()):
    raise RuntimeError("Critical test settings are not properly configured!")

print("🎯 All test settings verified and optimized for performance")
