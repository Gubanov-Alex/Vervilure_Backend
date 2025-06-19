"""Pytest configuration and fixtures."""

import os
import sys

import django
import pytest
from django.conf import settings

# Add project root to a Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def pytest_configure(config):
    """Configure Django for pytest."""
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
            INSTALLED_APPS=[
                "django.contrib.admin",
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.staticfiles",
                "rest_framework",
                "rest_framework_simplejwt",
                "src.apps.accounts",
            ],
            SECRET_KEY="test-secret-key-for-pytest",
            USE_TZ=True,
            PASSWORD_HASHERS=[
                "django.contrib.auth.hashers.MD5PasswordHasher",
            ],
            REST_FRAMEWORK={
                "DEFAULT_AUTHENTICATION_CLASSES": [
                    "rest_framework_simplejwt.authentication.JWTAuthentication",
                ],
                "DEFAULT_PERMISSION_CLASSES": [
                    "rest_framework.permissions.IsAuthenticated",
                ],
            },
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [],
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
            ],
            MIDDLEWARE=[
                "django.middleware.security.SecurityMiddleware",
                "django.contrib.sessions.middleware.SessionMiddleware",
                "django.middleware.common.CommonMiddleware",
                "django.middleware.csrf.CsrfViewMiddleware",
                "django.contrib.auth.middleware.AuthenticationMiddleware",
                "django.contrib.messages.middleware.MessageMiddleware",
            ],
            DEFAULT_FROM_EMAIL="test@example.com",
            SITE_ID=1,
            # Add cache settings for testing
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                }
            },
            # Add Google OAuth settings for testing
            GOOGLE_OAUTH2_CLIENT_ID="test_client_id",
            GOOGLE_OAUTH2_CLIENT_SECRET="test_client_secret",
        )

    django.setup()


@pytest.fixture
def api_client():
    """Return DRF test client."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def api_client():
    """Return DRF test client."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user_data():
    """Return valid user data for tests."""
    return {"email": "test@example.com", "password": "TestPass123!", "first_name": "Test", "last_name": "User"}


@pytest.fixture
def django_user_model():
    """Return User model."""
    from django.contrib.auth import get_user_model

    return get_user_model()


@pytest.fixture
def authenticated_user(django_user_model):
    """Create and return authenticated user."""
    user = django_user_model.objects.create_user(
        email="auth@example.com",
        password="TestPass123!",
        first_name="Auth",
        last_name="User",
        is_active=True,
        email_verified=True,
    )
    return user


@pytest.fixture
def api_client_with_auth(api_client, authenticated_user):
    """Return API client with authenticated user."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(authenticated_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def google_oauth_mock_data():
    """Return mock data for Google OAuth testing."""
    return {
        "access_token": "mock_access_token",
        "user_info": {
            "email": "oauth@example.com",
            "email_verified": True,
            "given_name": "OAuth",
            "family_name": "User",
            "sub": "google123456",
            "aud": "test_client_id",
        },
    }
