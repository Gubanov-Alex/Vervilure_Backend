"""Pytest configuration and fixtures - simplified."""

import os
import sys

import pytest

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Mark as testing environment
os.environ["IS_TESTING"] = "True"


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
        is_email_verified=True,
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
