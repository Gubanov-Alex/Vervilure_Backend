import os
import sys
import warnings
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.test.utils import setup_test_environment, teardown_test_environment

# Add project root to Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

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
from django.test.client import Client
from django.test import override_settings
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
    Using SQLite in-memory so no actual setup needed.
    """
    # Since we're using :memory: SQLite, no setup required
    settings.DATABASES["default"]["NAME"] = ":memory:"
    yield


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
def user_factory():
    """Factory for creating users with custom attributes."""
    created_users = []

    def _create_user(**kwargs):
        defaults = {
            "email": f"user{len(created_users)}@example.com",
            "password": "TestPass123!",
            "first_name": "Test",
            "last_name": "User",
            "is_email_verified": True,
            "is_active": True,
        }
        defaults.update(kwargs)

        user = User.objects.create_user(**defaults)
        created_users.append(user)
        return user

    yield _create_user

    # Cleanup
    User.objects.filter(id__in=[u.id for u in created_users]).delete()


@pytest.fixture
def regular_user(user_factory):
    """Create a regular test user."""
    return user_factory(
        email="regular@example.com",
        first_name="Regular",
        last_name="User"
    )


@pytest.fixture
def superuser(user_factory):
    """Create a superuser for admin tests."""
    return user_factory(
        email="superuser@example.com",
        first_name="Super",
        last_name="User",
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def admin_user(user_factory):
    """Create an admin test user."""
    return user_factory(
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def unverified_user(user_factory):
    """Create an unverified test user."""
    return user_factory(
        email="unverified@example.com",
        first_name="Unverified",
        last_name="User",
        is_email_verified=False,
        is_active=False
    )


@pytest.fixture
def request_factory():
    """Django request factory for admin tests."""
    from django.test import RequestFactory
    return RequestFactory()


# Authentication fixtures
@pytest.fixture
def user_tokens(regular_user):
    """Generate JWT tokens for a user."""
    refresh = RefreshToken.for_user(regular_user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": regular_user
    }


@pytest.fixture
def admin_tokens(admin_user):
    """Generate JWT tokens for admin user."""
    refresh = RefreshToken.for_user(admin_user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": admin_user
    }


# Mock fixtures for external services
@pytest.fixture
def mock_google_oauth():
    """Mock Google OAuth validation."""
    with patch("src.apps.accounts.serializers.GoogleOAuthValidator.validate_token") as mock:
        mock.return_value = (
            True,
            {
                "email": "google@gmail.com",
                "google_id": "123456789",
                "first_name": "Google",
                "last_name": "User",
                "email_verified": True,
            },
            None,
        )
        yield mock


@pytest.fixture
def mock_celery_tasks():
    """Mock Celery tasks for testing."""
    with patch("src.apps.accounts.tasks.send_verification_email") as mock_verification, \
            patch("src.apps.accounts.tasks.send_password_reset_email") as mock_reset:
        mock_verification.delay.return_value = None
        mock_reset.delay.return_value = None
        yield {
            "verification": mock_verification,
            "reset": mock_reset
        }


# Settings override fixtures
@pytest.fixture
def throttling_disabled():
    """Disable throttling for specific tests."""
    with override_settings(
            REST_FRAMEWORK={
                **settings.REST_FRAMEWORK,
                "DEFAULT_THROTTLE_CLASSES": [],
                "DEFAULT_THROTTLE_RATES": {},
            }
    ):
        yield


@pytest.fixture
def throttling_enabled():
    """Enable throttling for specific tests."""
    with override_settings(
            REST_FRAMEWORK={
                **settings.REST_FRAMEWORK,
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
                },
            }
    ):
        yield


# Performance and debugging fixtures
@pytest.fixture
def performance_monitor():
    """Monitor test performance."""
    import time
    start_time = time.time()
    yield
    end_time = time.time()
    duration = end_time - start_time
    if duration > 5.0:  # Warn if test takes more than 5 seconds
        pytest.warns(f"Test took {duration:.2f} seconds - consider optimization")


@pytest.fixture
def capture_logs():
    """Capture logs during test execution."""
    import logging
    from io import StringIO

    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    # Add handler to relevant loggers
    loggers = [
        logging.getLogger("src.apps.accounts"),
        logging.getLogger("django"),
        logging.getLogger("rest_framework"),
    ]

    for logger in loggers:
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    yield log_capture

    # Cleanup
    for logger in loggers:
        logger.removeHandler(handler)


# Test data fixtures
@pytest.fixture
def valid_user_data():
    """Valid user registration data."""
    return {
        "email": "newuser@example.com",
        "password": "ValidPass123!",
        "password_confirm": "ValidPass123!",
        "first_name": "New",
        "last_name": "User",
        "marketing_consent": True,
    }


@pytest.fixture
def valid_login_data(regular_user):
    """Valid login data."""
    return {
        "email": regular_user.email,
        "password": "TestPass123!"
    }


@pytest.fixture
def valid_address_data():
    """Valid address data."""
    return {
        "address_type": "shipping",
        "first_name": "Test",
        "last_name": "User",
        "address_line1": "123 Test St",
        "city": "Test City",
        "state": "TS",
        "postal_code": "12345",
        "country": "US",
    }


# URL helper fixtures
@pytest.fixture
def url_finder():
    """Helper to find available URLs for testing."""
    from django.urls import reverse, NoReverseMatch

    def find_url(patterns, *args, **kwargs):
        """Try multiple URL patterns and return the first that works."""
        for pattern in patterns:
            try:
                if pattern.startswith("/"):
                    return pattern  # Direct URL
                else:
                    return reverse(pattern, args=args, kwargs=kwargs)
            except (NoReverseMatch, Exception):
                continue
        return None

    return find_url


# Environment fixtures
@pytest.fixture
def ci_environment():
    """Simulate CI environment."""
    with patch.dict(os.environ, {"CI": "true", "GITHUB_ACTIONS": "true"}):
        yield


@pytest.fixture
def local_environment():
    """Simulate local development environment."""
    with patch.dict(os.environ, {"CI": "", "GITHUB_ACTIONS": ""}, clear=False):
        yield


# Test utilities
@pytest.fixture
def assert_response_codes():
    """Utility for asserting response codes."""

    def _assert_codes(response, expected_codes, message=""):
        """Assert that response status code is in expected range."""
        assert response.status_code in expected_codes, (
            f"{message}Expected status codes {expected_codes}, "
            f"got {response.status_code}. "
            f"Response data: {getattr(response, 'data', 'No data')}"
        )

    return _assert_codes


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Clean up any test files created during tests."""
    yield
    # Add cleanup logic here if needed
    pass


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Disable migrations for faster tests
    settings.MIGRATION_MODULES = {
        app: None for app in settings.INSTALLED_APPS
        if app.startswith("src.apps.")
    }

    # Set test runner optimizations
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

    print("🧪 Pytest configured with optimizations")


def pytest_runtest_setup(item):
    """Run before each test."""
    # Clear any cached data
    try:
        cache.clear()
    except Exception:
        pass


def pytest_runtest_teardown(item):
    """Run after each test."""
    # Additional cleanup if needed
    pass


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Add markers to tests based on their location or names
    for item in items:
        # Mark API tests
        if "api" in item.nodeid.lower() or "test_views" in item.nodeid:
            item.add_marker(pytest.mark.api)

        # Mark auth tests
        if "auth" in item.nodeid.lower():
            item.add_marker(pytest.mark.auth)

        # Mark slow tests
        if "test_performance" in item.name or "slow" in item.name:
            item.add_marker(pytest.mark.slow)


def get_celery_setting(setting_name: str, default_value=None):
    """Safely get Celery setting with fallback."""
    try:
        return getattr(settings, setting_name, default_value)
    except AttributeError:
        return default_value


@pytest.fixture(scope="session", autouse=True)
def test_session_info():
    """Print test session information with safe settings access."""
    print(f"\n🚀 Starting test session")
    print(f"📍 Django settings: {getattr(settings, 'SETTINGS_MODULE', 'Not set')}")
    print(f"💾 Database: {settings.DATABASES['default']['NAME']}")

    # Safe access to REST_FRAMEWORK settings
    rest_framework = getattr(settings, 'REST_FRAMEWORK', {})
    throttle_rates = rest_framework.get('DEFAULT_THROTTLE_RATES', {})
    print(f"🚫 Throttling: {'Disabled' if not throttle_rates else 'Enabled'}")

    # Safe access to password hashers
    password_hashers = getattr(settings, 'PASSWORD_HASHERS', [])
    has_md5 = any('MD5' in hasher for hasher in password_hashers) if password_hashers else False
    print(f"⚡ Fast passwords: {has_md5}")

    celery_eager = get_celery_setting('CELERY_TASK_ALWAYS_EAGER', 'Not configured')
    print(f"🏃 Celery eager: {celery_eager}")

    yield

    print(f"\n✅ Test session completed")
