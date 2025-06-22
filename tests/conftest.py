"""Tests for OAuth validators"""

import os
import sys
import warnings
from pathlib import Path

import pytest
import timedelta
from django.conf import settings
from django.test.utils import setup_test_environment, teardown_test_environment

# Add project root to Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Убираем принудительную настройку базы данных
# Set Django settings before any Django imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.test_settings")
os.environ["IS_TESTING"] = "True"
os.environ["ENVIRONMENT"] = "testing"
os.environ["THROTTLING_DISABLED"] = "True"

# Suppress warnings during tests
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import django
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.test.client import Client
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

# Initialize Django
django.setup()

User = get_user_model()


# Session-scoped fixtures for test environment setup
@pytest.fixture(scope="session", autouse=True)
def django_test_environment():
    """Set up Django test environment for the entire test session."""
    setup_test_environment()
    yield
    teardown_test_environment()


@pytest.fixture(scope="session")
def django_db_setup():
    """
    Setup test database for the session.
    ИСПРАВЛЕНИЕ: Убираем принудительную настройку :memory:
    Позволяем Django использовать настройки из test_settings.py
    """
    # УДАЛЕНО: settings.DATABASES["default"]["NAME"] = ":memory:"
    # Позволяем Django использовать настройки из test_settings.py
    pass


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Automatically enable database access for all tests.
    This eliminates the need to mark every test with @pytest.mark.django_db
    """
    pass


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test to ensure test isolation."""
    try:
        cache.clear()
    except Exception:
        # Dummy cache doesn't need clearing
        pass
    yield
    try:
        cache.clear()
    except Exception:
        pass


# Client fixtures
@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def api_client():
    """DRF API test client."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, regular_user):
    """Authenticated API client with regular user."""
    refresh = RefreshToken.for_user(regular_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Authenticated API client with admin user."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


# User fixtures
@pytest.fixture
def regular_user():
    """Create a regular user for testing."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
        is_active=True,
        email_verified=True,
    )
    return user


@pytest.fixture
def admin_user():
    """Create an admin user for testing."""
    user = User.objects.create_user(
        email="admin@example.com",
        password="adminpass123",
        first_name="Admin",
        last_name="User",
        is_active=True,
        is_staff=True,
        is_superuser=True,
        email_verified=True,
    )
    return user


def get_celery_setting(setting_name: str, default_value: str = "Not configured") -> str:
    """Safely get Celery settings without triggering errors."""
    try:
        return getattr(settings, setting_name, default_value)
    except AttributeError:
        return default_value


@pytest.fixture(scope="session", autouse=True)
def test_session_info():
    """Print test session information with safe settings access."""
    print(f"\n🚀 Starting test session")
    print(f"📍 Django settings: {getattr(settings, 'SETTINGS_MODULE', 'tests.test_settings')}")
    print(f"💾 Database: {settings.DATABASES['default']['NAME']}")

    # Safe access to REST_FRAMEWORK settings
    rest_framework = getattr(settings, "REST_FRAMEWORK", {})
    throttle_rates = rest_framework.get("DEFAULT_THROTTLE_RATES", {})
    print(f"🚫 Throttling: {'Disabled' if not throttle_rates else 'Enabled'}")

    # Safe access to password hashers
    password_hashers = getattr(settings, "PASSWORD_HASHERS", [])
    has_md5 = any("MD5" in hasher for hasher in password_hashers) if password_hashers else False
    print(f"⚡ Fast passwords: {has_md5}")

    celery_eager = get_celery_setting("CELERY_TASK_ALWAYS_EAGER", "Not configured")
    print(f"🏃 Celery eager: {celery_eager}")

    yield

    print(f"\n✅ Test session completed")


# OAuth и специфичные для авторизации фикстуры
@pytest.fixture
def google_oauth_validator():
    """Google OAuth validator for testing."""
    from src.apps.accounts.utils.oauth_validators import GoogleOAuthValidator

    return GoogleOAuthValidator("test_client_id")


# Автоматически добавляем маркер для тестов аутентификации
def pytest_collection_modifyitems(config, items):
    """Automatically add auth marker to OAuth and auth related tests."""
    for item in items:
        if "oauth" in item.nodeid.lower() or "auth" in item.nodeid.lower():
            item.add_marker(pytest.mark.auth)


# =============================================================================
# 2. ИСПРАВЛЕНИЕ test_settings.py (tests/test_settings.py)
# =============================================================================

"""
Django settings for testing environment.
Optimized for maximum test speed and isolation.
"""

import os
import tempfile
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: Don't use this secret key in production!
SECRET_KEY = "test-secret-key-for-testing-only"

# SECURITY WARNING: Don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]

LOCAL_APPS = [
    "src.apps.accounts",
    "src.apps.common",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

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

# КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: База данных для тестов - SQLite в памяти
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "OPTIONS": {
            "timeout": 20,
        },
        "TEST": {
            "NAME": ":memory:",
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

# JWT settings for tests - shorter expiration times
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

# Custom user model
AUTH_USER_MODEL = "accounts.User"

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging configuration for tests - minimal logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
    },
    "loggers": {
        "django": {
            "handlers": ["null"],
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["null"],
            "propagate": False,
        },
    },
}

# Email backend for tests - use console backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# CORS settings for tests
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Django Allauth settings for tests
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1

ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = "none"  # Disable for tests
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = None  # Disable for tests
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = None  # Disable for tests

# Social account settings for tests
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": "test_google_client_id",
            "secret": "test_google_secret",
            "key": "",
        },
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
        "OAUTH_PKCE_ENABLED": True,
    }
}

# Test environment specific settings
TESTING = True
IS_TESTING = True

# Celery settings for tests - always eager
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Security settings for tests
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# MIGRATION_MODULES = DisableMigrations()

from datetime import timedelta
