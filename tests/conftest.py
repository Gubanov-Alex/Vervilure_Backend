"""Pytest configuration and fixtures - minimal and safe."""

import os
import sys
from pathlib import Path

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Mark as testing environment
os.environ["IS_TESTING"] = "True"


def pytest_configure(config):
    """Configure pytest and Django safely."""
    # Import Django only when needed
    import django
    from django.conf import settings

    # Ensure Django is properly configured
    if not settings.configured:
        django.setup()


@pytest.fixture
def api_client():
    """Return DRF test client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def user_data():
    """Return valid user data for tests."""
    return {
        "email": "test@example.com",
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User",
    }


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
        is_email_verified=True,
    )
    return user


@pytest.fixture
def superuser(django_user_model):
    """Create and return superuser."""
    return django_user_model.objects.create_superuser(
        email="admin@example.com",
        password="AdminPass123!",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def api_client_with_auth(api_client, authenticated_user):
    """Return API client with authenticated user."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(authenticated_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def admin_site():
    """Return Django admin site instance."""
    from django.contrib.admin.sites import AdminSite
    return AdminSite()


@pytest.fixture
def request_factory():
    """Return Django request factory."""
    from django.test import RequestFactory
    return RequestFactory()
