"""Pytest configuration and fixtures."""

import os
import sys

import django
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
        )

    django.setup()


import pytest


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
