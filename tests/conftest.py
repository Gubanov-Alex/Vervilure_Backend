"""Pytest configuration - optimized for fast test execution."""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Use test-specific settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_settings")
os.environ["IS_TESTING"] = "True"

import pytest

# DO NOT import Django here - let pytest-django handle it


@pytest.fixture(scope="session")
def django_db_setup():
    """Setup test database."""
    # Since we're using :memory: SQLite, no setup needed
    pass


@pytest.fixture
def api_client():
    """Return DRF test client."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def django_user_model():
    """Return User model."""
    from django.contrib.auth import get_user_model

    return get_user_model()


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
def regular_user(django_user_model):
    """Create and return regular user."""
    return django_user_model.objects.create_user(
        email="user@example.com",
        password="UserPass123!",
        first_name="Regular",
        last_name="User",
    )


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
