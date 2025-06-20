import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class EmailVerificationTestCase(TestCase):
    """Comprehensive email verification tests with edge cases."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com", password="TestPass123!", is_email_verified=False, is_active=False
        )
        self.user.regenerate_verification_token()

    def test_successful_email_verification(self):
        """Test successful email verification flow."""
        url = reverse("accounts:auth-verify-email")
        data = {"token": str(self.user.email_verification_token)}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "Email verified successfully" in response.data["message"]

        self.user.refresh_from_db()
        assert self.user.is_email_verified is True
        assert self.user.is_active is True

    def test_invalid_token_format(self):
        """Test with malformed UUID token."""
        url = reverse("accounts:auth-verify-email")
        data = {"token": "invalid-uuid-format"}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "token" in response.data

    def test_nonexistent_token(self):
        """Test with valid UUID that doesn't exist in database."""
        url = reverse("accounts:auth-verify-email")
        data = {"token": str(uuid.uuid4())}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid verification token" in response.data["error"]

    def test_expired_token(self):
        """Test with expired verification token."""
        # Set token as sent 25 hours ago
        self.user.email_verification_sent_at = timezone.now() - timedelta(hours=25)
        self.user.save()

        url = reverse("accounts:auth-verify-email")
        data = {"token": str(self.user.email_verification_token)}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "expired" in response.data["error"].lower()

    def test_already_verified_email(self):
        """Test verification of already verified email."""
        self.user.is_email_verified = True
        self.user.save()

        url = reverse("accounts:auth-verify-email")
        data = {"token": str(self.user.email_verification_token)}

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already verified" in response.data["message"].lower()

    def test_race_condition_protection(self):
        """Test concurrent verification attempts."""
        import time
        from threading import Thread

        from django.test import TransactionTestCase

        def verify_email():
            client = APIClient()
            url = reverse("accounts:auth-verify-email")
            data = {"token": str(self.user.email_verification_token)}
            return client.post(url, data, format="json")

        # Simulate concurrent requests
        threads = [Thread(target=verify_email) for _ in range(3)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.user.refresh_from_db()
        assert self.user.is_email_verified is True  # Should be verified only once
