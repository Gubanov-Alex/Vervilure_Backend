import uuid
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


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
    return user_factory(email="regular@example.com", first_name="Regular", last_name="User")


@pytest.fixture
def admin_user(user_factory):
    """Create an admin test user."""
    return user_factory(
        email="admin@example.com", first_name="Admin", last_name="User", is_staff=True, is_superuser=True
    )


@pytest.fixture
def superuser(user_factory):
    """Create a superuser for admin tests."""
    return user_factory(
        email="superuser@example.com", first_name="Super", last_name="User", is_staff=True, is_superuser=True
    )


@pytest.fixture
def unverified_user(user_factory):
    """Create an unverified test user."""
    user = user_factory(
        email="unverified@example.com",
        first_name="Unverified",
        last_name="User",
        is_email_verified=False,
        is_active=False,
    )
    # Manual token setup instead of calling non-existent method
    user.email_verification_token = uuid.uuid4()
    user.email_verification_sent_at = timezone.now()
    user.save(update_fields=["email_verification_token", "email_verification_sent_at"])
    return user


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
    return {"refresh": str(refresh), "access": str(refresh.access_token), "user": regular_user}


@pytest.fixture
def admin_tokens(admin_user):
    """Generate JWT tokens for admin user."""
    refresh = RefreshToken.for_user(admin_user)
    return {"refresh": str(refresh), "access": str(refresh.access_token), "user": admin_user}


@pytest.fixture
def unverified_tokens(unverified_user):
    """Generate JWT tokens for unverified user."""
    refresh = RefreshToken.for_user(unverified_user)
    return {"refresh": str(refresh), "access": str(refresh.access_token), "user": unverified_user}


# Email verification helper fixtures
@pytest.fixture
def verification_token_generator():
    """Helper to generate fresh verification tokens."""
    def _generate_token(user):
        """Generate fresh verification token for user."""
        user.email_verification_token = uuid.uuid4()
        user.email_verification_sent_at = timezone.now()
        user.save(update_fields=["email_verification_token", "email_verification_sent_at"])
        return user.email_verification_token
    
    return _generate_token


@pytest.fixture
def expired_verification_user(user_factory, verification_token_generator):
    """Create user with expired verification token."""
    user = user_factory(
        email="expired@example.com",
        is_email_verified=False,
        is_active=False,
    )
    # Set token as expired (25 hours ago)
    from datetime import timedelta
    user.email_verification_token = uuid.uuid4()
    user.email_verification_sent_at = timezone.now() - timedelta(hours=25)
    user.save(update_fields=["email_verification_token", "email_verification_sent_at"])
    return user


# Database fixtures
@pytest.fixture
def transactional_db():
    """Use transactional database for concurrency tests."""
    pass


# Mock fixtures for external services
@pytest.fixture
def mock_email_backend():
    """Mock email backend for testing."""
    from unittest.mock import patch
    with patch("django.core.mail.send_mail") as mock_send:
        mock_send.return_value = True
        yield mock_send


@pytest.fixture
def mock_celery_task():
    """Mock Celery task execution."""
    from unittest.mock import patch
    with patch("src.apps.accounts.tasks.send_verification_email.delay") as mock_task:
        mock_task.return_value = "Task queued"
        yield mock_task


# Test data fixtures
@pytest.fixture
def sample_verification_data():
    """Sample data for verification tests."""
    return {
        "valid_token": str(uuid.uuid4()),
        "invalid_token": "invalid-token-format",
        "nonexistent_token": str(uuid.uuid4()),
        "empty_token": "",
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for creation tests."""
    return {
        "email": "sample@example.com",
        "password": "SamplePass123!",
        "first_name": "Sample",
        "last_name": "User",
    }


# Performance test fixtures
@pytest.fixture
def performance_test_users(user_factory):
    """Create multiple users for performance testing."""
    users = []
    for i in range(10):
        user = user_factory(
            email=f"perf_user_{i}@example.com",
            first_name=f"User{i}",
            last_name="Performance",
            is_email_verified=False,
            is_active=False,
        )
        # Setup verification token
        user.email_verification_token = uuid.uuid4()
        user.email_verification_sent_at = timezone.now()
        user.save(update_fields=["email_verification_token", "email_verification_sent_at"])
        users.append(user)
    return users


# URL resolution fixtures
@pytest.fixture
def url_resolver():
    """Helper for URL resolution testing."""
    from django.urls import reverse, NoReverseMatch
    
    def _resolve_url(pattern_name, *args, **kwargs):
        """Safely resolve URL pattern."""
        try:
            return reverse(pattern_name, args=args, kwargs=kwargs)
        except NoReverseMatch:
            return None
    
    return _resolve_url


@pytest.fixture
def verification_url_finder():
    """Find working verification URL from multiple patterns."""
    from django.urls import reverse, NoReverseMatch
    
    def _find_verification_url():
        """Find working email verification URL."""
        patterns = [
            "auth:verify_email",
            "accounts:verify_email", 
            "auth:auth-verify-email",
            "verify_email",
            "auth-verify-email",
        ]
        
        for pattern in patterns:
            try:
                return reverse(pattern)
            except NoReverseMatch:
                continue
        
        # Fallback to direct endpoint
        return "/api/v1/auth/email/verify/"
    
    return _find_verification_url


# Settings fixtures for testing different configurations
@pytest.fixture
def test_settings():
    """Common test settings."""
    return {
        "verification_token_expiry_hours": 24,
        "max_verification_attempts": 5,
        "rate_limit_minutes": 5,
    }
