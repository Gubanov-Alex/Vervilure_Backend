"""
Test module for user account deletion functionality.

This module contains comprehensive tests for account deletion workflows,
including soft deletion, anonymization, and complete data removal.
"""

import pytest
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from src.apps.accounts.models import User


@pytest.mark.django_db
class TestUserModelMethods:
    """Test User model custom methods for account deletion."""

    def test_soft_delete_user_data(self):
        """Test soft deletion of user data."""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="John", last_name="Doe"
        )

        original_id = user.id
        user.soft_delete_user_data(reason="User requested deletion")

        # Refresh from database
        user.refresh_from_db()

        assert user.id == original_id  # ID should remain the same
        assert user.is_active is False
        assert user.deactivated_at is not None
        assert user.deactivation_reason == "User requested deletion"
        assert user.is_anonymized is False

    def test_anonymize_user_data(self):
        """Test anonymization of user data."""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="John", last_name="Doe"
        )

        original_id = user.id
        anonymous_id = user.anonymize_user_data()

        # Refresh from database
        user.refresh_from_db()

        assert user.id == original_id  # ID should remain the same
        assert user.email == f"{anonymous_id}@deleted.local"
        assert user.first_name == "Deleted"
        assert user.last_name == "User"
        assert user.is_active is False
        assert user.is_anonymized is True
        assert user.anonymized_at is not None
        assert anonymous_id.startswith("deleted_user_")

    def test_user_str_representation_when_anonymized(self):
        """Test user string representation for anonymized users."""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="John", last_name="Doe"
        )

        # Normal user
        original_str = str(user)
        assert "test@example.com" in original_str
        assert "John Doe" in original_str

        # Anonymized user
        user.anonymize_user_data()
        anonymized_str = str(user)
        assert "Anonymized User" in anonymized_str
        assert user.id in anonymized_str

    def test_full_name_property_when_anonymized(self):
        """Test full_name property for anonymized users."""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="John", last_name="Doe"
        )

        assert user.full_name == "John Doe"

        user.anonymize_user_data()
        assert user.full_name == "Deleted User"


class TestAccountDeletionAPI(APITestCase):
    """Test account deletion API endpoint functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="John", last_name="Doe"
        )
        # FIXED: Use correct URL pattern from users namespace
        self.delete_url = reverse("users:delete_account")

    def test_delete_account_requires_authentication(self):
        """Test that delete account requires authentication."""
        response = self.client.delete(self.delete_url, {"password": "testpass123", "deletion_type": "soft"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_account_requires_password(self):
        """Test that password confirmation is required."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.delete_url, {"deletion_type": "soft"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # FIXED: Match exact error message from API
        assert "Password confirmation is required for account deletion" in response.data["error"]

    def test_delete_account_invalid_password(self):
        """Test deletion with invalid password."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.delete_url, {"password": "wrongpassword", "deletion_type": "soft"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid password confirmation" in response.data["error"]

    def test_delete_account_invalid_deletion_type(self):
        """Test deletion with invalid deletion type."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.delete_url, {"password": "testpass123", "deletion_type": "invalid"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # FIXED: Match exact error message from API
        assert "Invalid deletion type" in response.data["error"]
        assert "Must be 'soft', 'hard', or 'anonymize'" in response.data["error"]

    def test_soft_delete_account(self):
        """Test soft delete functionality."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            self.delete_url, {"password": "testpass123", "deletion_type": "soft", "reason": "Test reason"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert "Account has been deactivated" in response.data["message"]
        assert "reactivation_deadline" in response.data

        # Check database changes
        self.user.refresh_from_db()
        assert self.user.is_active is False
        assert self.user.deactivated_at is not None
        assert self.user.deactivation_reason == "Test reason"
        assert self.user.is_anonymized is False

    def test_anonymize_account(self):
        """Test account anonymization."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            self.delete_url, {"password": "testpass123", "deletion_type": "anonymize", "reason": "Privacy request"}
        )

        # FIXED: Anonymization returns 204 NO CONTENT, not 200 OK
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Check database changes
        self.user.refresh_from_db()
        assert self.user.is_active is False
        assert self.user.is_anonymized is True
        assert self.user.anonymized_at is not None
        assert self.user.first_name == "Deleted"
        assert self.user.last_name == "User"
        assert self.user.email.endswith("@deleted.local")

    def test_hard_delete_account(self):
        """Test hard delete functionality."""
        user_id = self.user.id
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            self.delete_url, {"password": "testpass123", "deletion_type": "hard", "reason": "Complete removal"}
        )

        # FIXED: Hard delete returns 204 NO CONTENT, not 200 OK
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Check that user no longer exists
        with pytest.raises(User.DoesNotExist):
            User.objects.get(id=user_id)

    def test_delete_account_with_data_export(self):
        """Test account deletion with data export request."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            self.delete_url, {"password": "testpass123", "deletion_type": "soft", "export_data": True}
        )

        assert response.status_code == status.HTTP_200_OK
        # In real implementation, this would trigger async task
        # Here we just verify the request was processed
        assert "Account has been deactivated" in response.data["message"]


@pytest.mark.django_db
class TestUserManagerMethods:
    """Test custom User manager methods."""

    def test_active_users_queryset(self):
        """Test active_users queryset method."""
        # Create various user states
        active_user = User.objects.create_user(
            email="active@example.com", password="test123", first_name="Active", last_name="User"
        )

        deactivated_user = User.objects.create_user(
            email="deactivated@example.com",
            password="test123",
            first_name="Deactivated",
            last_name="User",
            is_active=False,
        )
        deactivated_user.deactivated_at = timezone.now()
        deactivated_user.save()

        anonymized_user = User.objects.create_user(
            email="anonymized@example.com", password="test123", first_name="Anonymized", last_name="User"
        )
        anonymized_user.anonymize_user_data()

        # Test active_users method
        active_users = User.objects.active_users()
        assert active_user in active_users
        assert deactivated_user not in active_users
        assert anonymized_user not in active_users

    def test_deactivated_users_queryset(self):
        """Test deactivated_users queryset method."""
        # Create various user states
        active_user = User.objects.create_user(
            email="active@example.com", password="test123", first_name="Active", last_name="User"
        )

        deactivated_user = User.objects.create_user(
            email="deactivated@example.com",
            password="test123",
            first_name="Deactivated",
            last_name="User",
            is_active=False,
        )
        deactivated_user.deactivated_at = timezone.now()
        deactivated_user.save()

        anonymized_user = User.objects.create_user(
            email="anonymized@example.com", password="test123", first_name="Anonymized", last_name="User"
        )
        anonymized_user.anonymize_user_data()

        # Test deactivated_users method
        deactivated_users = User.objects.deactivated_users()
        assert active_user not in deactivated_users
        assert deactivated_user in deactivated_users
        assert anonymized_user in deactivated_users  # Anonymized users are also deactivated

    def test_anonymized_users_queryset(self):
        """Test anonymized_users queryset method."""
        # Create various user states
        active_user = User.objects.create_user(
            email="active@example.com", password="test123", first_name="Active", last_name="User"
        )

        deactivated_user = User.objects.create_user(
            email="deactivated@example.com",
            password="test123",
            first_name="Deactivated",
            last_name="User",
            is_active=False,
        )
        deactivated_user.deactivated_at = timezone.now()
        deactivated_user.save()

        anonymized_user = User.objects.create_user(
            email="anonymized@example.com", password="test123", first_name="Anonymized", last_name="User"
        )
        anonymized_user.anonymize_user_data()

        # Test anonymized_users method
        anonymized_users = User.objects.anonymized_users()
        assert active_user not in anonymized_users
        assert deactivated_user not in anonymized_users
        assert anonymized_user in anonymized_users

    def test_users_for_deletion_queryset(self):
        """Test users_for_deletion queryset method."""
        # Create user deactivated more than 30 days ago
        old_deactivated_user = User.objects.create_user(
            email="old@example.com",
            password="test123",
            first_name="Old",
            last_name="Deactivated",
            is_active=False,
        )
        old_deactivated_user.deactivated_at = timezone.now() - timezone.timedelta(days=35)
        old_deactivated_user.save()

        # Create user deactivated less than 30 days ago
        recent_deactivated_user = User.objects.create_user(
            email="recent@example.com",
            password="test123",
            first_name="Recent",
            last_name="Deactivated",
            is_active=False,
        )
        recent_deactivated_user.deactivated_at = timezone.now() - timezone.timedelta(days=15)
        recent_deactivated_user.save()

        # Test users_for_deletion method
        users_for_deletion = User.objects.users_for_deletion()
        assert old_deactivated_user in users_for_deletion
        assert recent_deactivated_user not in users_for_deletion


@pytest.mark.django_db
class TestAccountReactivation:
    """Test account reactivation functionality."""

    def test_reactivate_soft_deleted_account(self):
        """Test reactivation of soft deleted account."""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="John", last_name="Doe"
        )

        # Soft delete the account
        user.soft_delete_user_data(reason="User requested deletion")
        assert user.is_active is False
        assert user.deactivated_at is not None

        # Reactivate the account
        user.reactivate_account()
        user.refresh_from_db()

        assert user.is_active is True
        assert user.deactivated_at is None
        assert user.deactivation_reason == ""

    def test_cannot_reactivate_anonymized_account(self):
        """Test that anonymized accounts cannot be reactivated."""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="John", last_name="Doe"
        )

        # Anonymize the account
        user.anonymize_user_data()
        assert user.is_anonymized is True

        # Attempt to reactivate should fail
        with pytest.raises(ValueError, match="Cannot reactivate anonymized account"):
            user.reactivate_account()

    def test_reactivation_deadline_check(self):
        """Test that accounts cannot be reactivated after deadline."""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="John", last_name="Doe"
        )

        # Set deactivation date beyond reactivation deadline
        user.deactivated_at = timezone.now() - timezone.timedelta(days=35)  # Beyond 30-day limit
        user.is_active = False
        user.save()

        # Attempt to reactivate should fail
        with pytest.raises(ValueError, match="Reactivation deadline has passed"):
            user.reactivate_account()


@pytest.mark.django_db
class TestDataExportFunctionality:
    """Test user data export functionality."""

    def test_export_user_data(self):
        """Test exporting user data."""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="John", last_name="Doe"
        )

        exported_data = user.export_user_data()

        assert "personal_information" in exported_data
        assert "account_settings" in exported_data
        assert "activity_logs" in exported_data

        # Check personal information
        personal_info = exported_data["personal_information"]
        assert personal_info["email"] == "test@example.com"
        assert personal_info["first_name"] == "John"
        assert personal_info["last_name"] == "Doe"

    def test_export_anonymized_user_data(self):
        """Test exporting data for anonymized user."""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", first_name="John", last_name="Doe"
        )

        user.anonymize_user_data()
        exported_data = user.export_user_data()

        # Anonymized users should have limited data available
        personal_info = exported_data["personal_information"]
        assert personal_info["first_name"] == "Deleted"
        assert personal_info["last_name"] == "User"
        assert personal_info["email"].endswith("@deleted.local")
