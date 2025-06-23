# Comprehensive tests for account deletion functionality

import pytest
from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from src.apps.accounts.models import User, UserAddress


@pytest.mark.django_db
class TestUserModelDeletionFields:
    """Test User model deletion-related fields and methods."""

    def test_user_creation_with_deletion_fields(self):
        """Test user creation includes deletion fields with defaults."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User"
        )

        assert user.deactivated_at is None
        assert user.deactivation_reason == ""
        assert user.is_anonymized is False
        assert user.anonymized_at is None
        assert user.is_active is True

    def test_can_reactivate_method(self):
        """Test can_reactivate method logic."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User"
        )

        # Active user cannot be reactivated
        assert user.can_reactivate() is False

        # Recently deactivated user can be reactivated
        user.deactivated_at = timezone.now() - timedelta(days=10)
        assert user.can_reactivate() is True

        # User deactivated over 30 days ago cannot be reactivated
        user.deactivated_at = timezone.now() - timedelta(days=35)
        assert user.can_reactivate() is False

    def test_get_reactivation_deadline(self):
        """Test reactivation deadline calculation."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User"
        )

        # No deadline for active user
        assert user.get_reactivation_deadline() is None

        # Deadline should be 30 days after deactivation
        deactivation_time = timezone.now() - timedelta(days=5)
        user.deactivated_at = deactivation_time
        expected_deadline = deactivation_time + timedelta(days=30)

        deadline = user.get_reactivation_deadline()
        assert deadline is not None
        assert abs((deadline - expected_deadline).total_seconds()) < 1  # Within 1 second

    def test_anonymize_user_data_method(self):
        """Test user data anonymization method."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe"
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
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe"
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
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe"
        )

        assert user.full_name == "John Doe"

        user.anonymize_user_data()
        assert user.full_name == "Deleted User"


class TestAccountDeletionAPI(APITestCase):
    """Test account deletion API endpoint functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe"
        )
        self.delete_url = reverse('authviewset-delete-account')

    def test_delete_account_requires_authentication(self):
        """Test that delete account requires authentication."""
        response = self.client.delete(self.delete_url, {
            "password": "testpass123",
            "deletion_type": "soft"
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_account_requires_password(self):
        """Test that password confirmation is required."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.delete_url, {
            "deletion_type": "soft"
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Password confirmation is required" in response.data["error"]

    def test_delete_account_invalid_password(self):
        """Test deletion with invalid password."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.delete_url, {
            "password": "wrongpassword",
            "deletion_type": "soft"
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid password confirmation" in response.data["error"]

    def test_delete_account_invalid_deletion_type(self):
        """Test deletion with invalid deletion type."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.delete_url, {
            "password": "testpass123",
            "deletion_type": "invalid"
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid deletion type" in response.data["error"]

    def test_soft_delete_account(self):
        """Test soft delete functionality."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.delete_url, {
            "password": "testpass123",
            "deletion_type": "soft",
            "reason": "Test reason"
        })

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
        # Create address to test cascade deletion
        UserAddress.objects.create(
            user=self.user,
            address_type="shipping",
            first_name="John",
            last_name="Doe",
            address_line1="123 Test St",
            city="Test City",
            country="US"
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.delete_url, {
            "password": "testpass123",
            "deletion_type": "anonymize"
        })

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Check database changes
        self.user.refresh_from_db()
        assert self.user.is_active is False
        assert self.user.is_anonymized is True
        assert self.user.anonymized_at is not None
        assert self.user.email.endswith("@deleted.local")
        assert self.user.first_name == "Deleted"
        assert self.user.last_name == "User"

        # Check address deletion
        assert UserAddress.objects.filter(user=self.user).count() == 0

    def test_hard_delete_account(self):
        """Test hard delete functionality."""
        # Create related data
        UserAddress.objects.create(
            user=self.user,
            address_type="shipping",
            first_name="John",
            last_name="Doe",
            address_line1="123 Test St",
            city="Test City",
            country="US"
        )

        user_id = self.user.id
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.delete_url, {
            "password": "testpass123",
            "deletion_type": "hard"
        })

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Check user is completely deleted
        assert not User.objects.filter(id=user_id).exists()
        assert UserAddress.objects.filter(user_id=user_id).count() == 0

    @patch('src.apps.accounts.views.logger')
    def test_delete_account_logging(self, mock_logger):
        """Test that account deletion is properly logged."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.delete_url, {
            "password": "testpass123",
            "deletion_type": "soft",
            "reason": "Test reason"
        })

        assert response.status_code == status.HTTP_200_OK

        # Check that info log was called
        mock_logger.info.assert_called()
        log_call = mock_logger.info.call_args
        assert "Account deactivated (soft delete)" in log_call[0][0]

        # Check log extra data
        log_extra = log_call[1]['extra']
        assert log_extra['user_id'] == self.user.id
        assert log_extra['deletion_type'] == 'soft'
        assert log_extra['reason'] == 'Test reason'
        assert log_extra['action'] == 'account_soft_delete'

    def test_delete_account_with_data_export_request(self):
        """Test account deletion with data export request."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.delete_url, {
            "password": "testpass123",
            "deletion_type": "soft",
            "export_data": True
        })

        assert response.status_code == status.HTTP_200_OK
        # In real implementation, this would trigger async task
        # Here we just verify the request was processed

    @patch('src.apps.accounts.views.transaction')
    def test_delete_account_transaction_rollback_on_error(self, mock_transaction):
        """Test that database transaction is rolled back on error."""
        # Mock atomic context manager to raise exception
        mock_transaction.atomic.return_value.__enter__.side_effect = Exception("Test error")

        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.delete_url, {
            "password": "testpass123",
            "deletion_type": "soft"
        })

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Account deletion failed" in response.data["error"]

        # User should remain unchanged
        self.user.refresh_from_db()
        assert self.user.is_active is True
        assert self.user.deactivated_at is None


@pytest.mark.django_db
class TestUserManagerMethods:
    """Test custom User manager methods."""

    def test_active_users_queryset(self):
        """Test active_users queryset method."""
        # Create various user states
        active_user = User.objects.create_user(
            email="active@example.com",
            password="test123",
            first_name="Active",
            last_name="User"
        )

        deactivated_user = User.objects.create_user(
            email="deactivated@example.com",
            password="test123",
            first_name="Deactivated",
            last_name="User",
            is_active=False
        )
        deactivated_user.deactivated_at = timezone.now()
        deactivated_user.save()

        anonymized_user = User.objects.create_user(
            email="anonymized@example.com",
            password="test123",
            first_name="Anonymized",
            last_name="User"
        )
        anonymized_user.anonymize_user_data()

        # Test active_users method
        active_users = User.objects.active_users()
        assert active_user in active_users
        assert deactivated_user not in active_users
        assert anonymized_user not in active_users

    def test_deactivated_users_queryset(self):
        """Test deactivated_users queryset method."""
        active_user = User.objects.create_user(
            email="active@example.com",
            password="test123",
            first_name="Active",
            last_name="User"
        )

        deactivated_user = User.objects.create_user(
            email="deactivated@example.com",
            password="test123",
            first_name="Deactivated",
            last_name="User",
            is_active=False
        )
        deactivated_user.deactivated_at = timezone.now()
        deactivated_user.save()

        deactivated_users = User.objects.deactivated_users()
        assert active_user not in deactivated_users
        assert deactivated_user in deactivated_users

    def test_anonymized_users_queryset(self):
        """Test anonymized_users queryset method."""
        normal_user = User.objects.create_user(
            email="normal@example.com",
            password="test123",
            first_name="Normal",
            last_name="User"
        )

        anonymized_user = User.objects.create_user(
            email="anonymized@example.com",
            password="test123",
            first_name="Anonymized",
            last_name="User"
        )
        anonymized_user.anonymize_user_data()

        anonymized_users = User.objects.anonymized_users()
        assert normal_user not in anonymized_users
        assert anonymized_user in anonymized_users
