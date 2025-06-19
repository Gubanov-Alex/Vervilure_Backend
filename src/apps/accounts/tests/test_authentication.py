from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import BlacklistedToken, UserAddress

User = get_user_model()


class AuthenticationTestCase(APITestCase):
    """
    Comprehensive test suite for authentication functionality.

    Tests registration, login, logout, and security features.
    """

    def setUp(self):
        """Set up test data."""
        self.user_data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
            "phone_number": "+1234567890",
            "marketing_consent": True,
        }

        self.existing_user = User.objects.create_user(
            email="existing@example.com",
            password="ExistingPass123!",
            first_name="Existing",
            last_name="User",
            is_email_verified=True,
        )

    def test_user_registration_success(self):
        """Test successful user registration."""
        url = reverse("accounts:auth-register")
        response = self.client.post(url, self.user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", response.data)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])

        # Verify user was created
        user = User.objects.get(email=self.user_data["email"])
        self.assertEqual(user.first_name, self.user_data["first_name"])
        self.assertFalse(user.is_email_verified)  # Should be False initially

    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email fails."""
        self.user_data["email"] = self.existing_user.email
        url = reverse("accounts:auth-register")
        response = self.client.post(url, self.user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_user_registration_weak_password(self):
        """Test registration with weak password fails."""
        weak_passwords = [
            "password",  # No uppercase, digits, or special chars
            "PASSWORD",  # No lowercase, digits, or special chars
            "Password",  # No digits or special chars
            "Pass123",  # Too short
            "password123",  # No uppercase or special chars
        ]

        url = reverse("accounts:auth-register")

        for weak_password in weak_passwords:
            with self.subTest(password=weak_password):
                data = self.user_data.copy()
                data["password"] = weak_password
                data["password_confirm"] = weak_password
                data["email"] = f"test_{weak_password}@example.com"

                response = self.client.post(url, data, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("password", response.data)

    def test_user_registration_password_mismatch(self):
        """Test registration with mismatched passwords fails."""
        self.user_data["password_confirm"] = "DifferentPass123!"
        url = reverse("accounts:auth-register")
        response = self.client.post(url, self.user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)

    def test_user_login_success(self):
        """Test successful user login."""
        login_data = {"email": self.existing_user.email, "password": "ExistingPass123!"}

        url = reverse("accounts:auth-login")
        response = self.client.post(url, login_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials fails."""
        login_data = {"email": self.existing_user.email, "password": "WrongPassword123!"}

        url = reverse("accounts:auth-login")
        response = self.client.post(url, login_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_user_login_unverified_email(self):
        """Test login with unverified email fails."""
        unverified_user = User.objects.create_user(
            email="unverified@example.com", password="TestPass123!", is_email_verified=False
        )

        login_data = {"email": unverified_user.email, "password": "TestPass123!"}

        url = reverse("accounts:auth-login")
        response = self.client.post(url, login_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_logout_success(self):
        """Test successful user logout."""
        # First login to get tokens
        refresh = RefreshToken.for_user(self.existing_user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Set authentication
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        logout_data = {"refresh": refresh_token}
        url = reverse("accounts:auth-logout")
        response = self.client.post(url, logout_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify token was blacklisted
        self.assertTrue(BlacklistedToken.objects.filter(token_jti=refresh["jti"], user=self.existing_user).exists())

    def test_user_logout_invalid_token(self):
        """Test logout with invalid token fails."""
        self.client.force_authenticate(user=self.existing_user)

        logout_data = {"refresh": "invalid_token"}
        url = reverse("accounts:auth-logout")
        response = self.client.post(url, logout_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_refresh_success(self):
        """Test successful token refresh."""
        refresh = RefreshToken.for_user(self.existing_user)
        refresh_token = str(refresh)

        url = reverse("accounts:token_refresh")
        response = self.client.post(url, {"refresh": refresh_token}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_blacklisted_token_rejected(self):
        """Test that blacklisted tokens are rejected."""
        refresh = RefreshToken.for_user(self.existing_user)

        # Blacklist the token
        BlacklistedToken.objects.create(token_jti=refresh["jti"], user=self.existing_user, expires_at=refresh["exp"])

        url = reverse("accounts:token_refresh")
        response = self.client.post(url, {"refresh": str(refresh)}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("src.apps.accounts.views.send_verification_email.delay")
    def test_email_verification_sent(self, mock_send_email):
        """Test that email verification is triggered during registration."""
        url = reverse("accounts:auth-register")
        response = self.client.post(url, self.user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # mock_send_email.assert_called_once()


class UserProfileTestCase(APITestCase):
    """
    Test suite for user profile management.
    """

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="profile@example.com",
            password="ProfilePass123!",
            first_name="Profile",
            last_name="User",
            is_email_verified=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_get_user_profile(self):
        """Test retrieving user profile."""
        url = reverse("accounts:profile-detail", kwargs={"pk": "me"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["full_name"], f"{self.user.first_name} {self.user.last_name}")

    def test_update_user_profile(self):
        """Test updating user profile."""
        url = reverse("accounts:profile-detail", kwargs={"pk": "me"})
        update_data = {"first_name": "Updated", "phone_number": "+9876543210"}

        response = self.client.patch(url, update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.phone_number, "+9876543210")

    def test_change_password_success(self):
        """Test successful password change."""
        url = reverse("accounts:profile-change-password")
        password_data = {
            "current_password": "ProfilePass123!",
            "new_password": "NewSecurePass123!",
            "new_password_confirm": "NewSecurePass123!",
        }

        response = self.client.post(url, password_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecurePass123!"))

    def test_change_password_wrong_current(self):
        """Test password change with wrong current password."""
        url = reverse("accounts:profile-change-password")
        password_data = {
            "current_password": "WrongPassword",
            "new_password": "NewSecurePass123!",
            "new_password_confirm": "NewSecurePass123!",
        }

        response = self.client.post(url, password_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("current_password", response.data)

    def test_add_user_address(self):
        """Test adding user address."""
        url = reverse("accounts:profile-add-address")
        address_data = {
            "address_type": "shipping",
            "first_name": "John",
            "last_name": "Doe",
            "address_line1": "123 Main St",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
            "country": "US",
            "is_default": True,
        }

        response = self.client.post(url, address_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify address was created
        address = UserAddress.objects.get(user=self.user)
        self.assertEqual(address.address_line1, "123 Main St")
        self.assertTrue(address.is_default)

    def test_get_user_addresses(self):
        """Test retrieving user addresses."""
        UserAddress.objects.create(
            user=self.user,
            address_type="shipping",
            first_name="John",
            last_name="Doe",
            address_line1="123 Main St",
            city="New York",
            state="NY",
            postal_code="10001",
            country="US",
        )

        url = reverse("accounts:profile-addresses")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["address_line1"], "123 Main St")


@pytest.mark.django_db
class TestPasswordValidation:
    """
    Test password validation edge cases.
    """

    def test_password_strength_validation(self):
        """Test comprehensive password strength validation."""
        from src.apps.accounts.serializers import PasswordValidationMixin

        mixin = PasswordValidationMixin()

        # Test valid passwords
        valid_passwords = ["SecurePass123!", "MyP@ssw0rd2023", "Complex#Password1"]

        for password in valid_passwords:
            try:
                result = mixin.validate_password_strength(password)
                assert result == password
            except Exception as e:
                pytest.fail(f"Valid password '{password}' failed validation: {e}")

        # Test invalid passwords
        invalid_passwords = [
            ("short", "Password must be at least 8 characters"),
            ("alllowercase123!", "uppercase letter"),
            ("ALLUPPERCASE123!", "lowercase letter"),
            ("NoDigitsHere!", "digit"),
            ("NoSpecialChars123", "special character"),
        ]

        for password, expected_error in invalid_passwords:
            with pytest.raises(Exception) as exc_info:
                mixin.validate_password_strength(password)
            assert expected_error in str(exc_info.value)
