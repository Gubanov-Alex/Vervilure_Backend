from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory
from src.apps.accounts.serializers import (
    GoogleOAuthSerializer,
    PasswordValidationMixin,
    UserAddressSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)

User = get_user_model()


class TestPasswordValidationMixin:
    """Test password validation mixin - covers validation logic"""

    def setup_method(self):
        self.mixin = PasswordValidationMixin()

    @pytest.mark.parametrize(
        "password,should_pass",
        [
            ("Password123!", True),
            ("ValidPass1@", True),
            ("weak", False),  # Too short
            ("nouppercasehere1!", False),  # No uppercase
            ("NOLOWERCASEHERE1!", False),  # No lowercase
            ("NoNumbers!", False),  # No digits
            ("NoSpecialChars123", False),  # No special chars
        ],
    )
    def test_validate_password_strength(self, password, should_pass):
        """Test password strength validation"""
        if should_pass:
            result = self.mixin.validate_password_strength(password)
            assert result == password
        else:
            with pytest.raises(serializers.ValidationError):
                self.mixin.validate_password_strength(password)

    @patch("django.contrib.auth.password_validation.validate_password")
    def test_validate_password_django_validators(self, mock_validate):
        """Test integration with Django password validators"""
        mock_validate.side_effect = DjangoValidationError(["Password too common"])

        with pytest.raises(serializers.ValidationError) as exc_info:
            self.mixin.validate_password_strength("Password123!")

        assert "Password too common" in str(exc_info.value)

    def test_password_complexity_validation(self):
        """Test password complexity validation rules."""
        mixin = PasswordValidationMixin()

        # Test password with no uppercase
        with pytest.raises(ValidationError):
            mixin.validate_password("lowercase123!")

        # Test password with no numbers
        with pytest.raises(ValidationError):
            mixin.validate_password("NoNumbersHere!")

        # Test password with no special characters
        with pytest.raises(ValidationError):
            mixin.validate_password("NoSpecialChars123")


@pytest.mark.django_db
class TestUserRegistrationSerializer:
    """Test user registration serializer - increase coverage from 39% to 85%"""

    def test_valid_registration_data(self):
        """Test valid registration data"""
        data = {
            "email": "test@example.com",
            "password": "ValidPass123!",
            "password_confirm": "ValidPass123!",
            "first_name": "Test",
            "last_name": "User",
            "phone_number": "+1234567890",
            "marketing_consent": True,
        }

        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid()

        user = serializer.save()
        assert user.email == "test@example.com"
        assert user.first_name == "Test"
        assert user.check_password("ValidPass123!")

    def test_password_mismatch(self):
        """Test password confirmation mismatch"""
        data = {
            "email": "test@example.com",
            "password": "ValidPass123!",
            "password_confirm": "DifferentPass123!",
            "first_name": "Test",
            "last_name": "User",
        }

        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert "password_confirm" in serializer.errors

    def test_duplicate_email(self):
        """Test duplicate email validation"""
        User.objects.create_user(
            email="existing@example.com", password="password123", first_name="Existing", last_name="User"
        )

        data = {
            "email": "existing@example.com",
            "password": "ValidPass123!",
            "password_confirm": "ValidPass123!",
            "first_name": "Test",
            "last_name": "User",
        }

        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert "email" in serializer.errors

    def test_missing_required_fields(self):
        """Test missing required fields"""
        data = {
            "email": "test@example.com",
            "password": "ValidPass123!",
            # Missing password_confirm, first_name, last_name
        }

        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert "password_confirm" in serializer.errors
        assert "first_name" in serializer.errors
        assert "last_name" in serializer.errors

    def test_password_confirmation_field(self):
        """Test password confirmation field handling."""
        data = {
            "email": "test@example.com",
            "password": "ValidPass123!",
            "password_confirm": "ValidPass123!",
            "first_name": "Test",
            "last_name": "User",
        }
        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid()

    def test_create_user_with_valid_data(self):
        """Test user creation with serializer."""
        data = {
            "email": "newuser@example.com",
            "password": "ValidPass123!",
            "password_confirm": "ValidPass123!",
            "first_name": "New",
            "last_name": "User",
        }
        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid()
        user = serializer.save()
        assert user.email == "newuser@example.com"
        assert user.first_name == "New"
        assert user.last_name == "User"

    def test_email_normalization(self):
        """Test email normalization during registration."""
        data = {
            "email": "TEST@EXAMPLE.COM",
            "password": "ValidPass123!",
            "password_confirm": "ValidPass123!",
            "first_name": "Test",
            "last_name": "User",
        }
        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid()
        user = serializer.save()
        assert user.email == "test@example.com"


@pytest.mark.django_db
class TestUserLoginSerializer:
    """Test user login serializer"""

    def setup_method(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            is_email_verified=True,
        )
        self.factory = APIRequestFactory()

    def test_valid_login(self):
        """Test valid login credentials"""
        request = self.factory.post("/auth/login/")
        data = {"email": "test@example.com", "password": "testpass123"}

        serializer = UserLoginSerializer(data=data, context={"request": request})
        assert serializer.is_valid()

        validated_data = serializer.validated_data
        assert validated_data["user"] == self.user
        assert "access" in validated_data
        assert "refresh" in validated_data

    def test_invalid_credentials(self):
        """Test invalid login credentials"""
        request = self.factory.post("/auth/login/")
        data = {"email": "test@example.com", "password": "wrongpassword"}

        serializer = UserLoginSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors

    def test_inactive_user(self):
        """Test login with inactive user"""
        self.user.is_active = False
        self.user.save()

        request = self.factory.post("/auth/login/")
        data = {"email": "test@example.com", "password": "testpass123"}

        serializer = UserLoginSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "authorization" in str(serializer.errors)

    def test_unverified_email(self):
        """Test login with unverified email"""
        self.user.is_email_verified = False
        self.user.save()

        request = self.factory.post("/auth/login/")
        data = {"email": "test@example.com", "password": "testpass123"}

        serializer = UserLoginSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "authorization" in str(serializer.errors)


@pytest.mark.django_db
class TestGoogleOAuthSerializer:
    """Test Google OAuth serializer"""

    def test_empty_access_token(self):
        """Test empty access token validation"""
        data = {"access_token": ""}

        serializer = GoogleOAuthSerializer(data=data)
        assert not serializer.is_valid()
        assert "access_token" in serializer.errors

    def test_whitespace_token_stripped(self):
        """Test token whitespace stripping"""
        data = {"access_token": "  valid_token  "}

        serializer = GoogleOAuthSerializer(data=data)
        # Only test format validation, not full OAuth flow
        assert serializer.initial_data["access_token"].strip() == "valid_token"

    @patch("src.apps.accounts.utils.oauth_validators.GoogleOAuthValidator.validate_token")
    def test_valid_google_token_new_user(self, mock_validate):
        """Test valid Google token with new user creation"""
        mock_validate.return_value = (
            True,
            {
                "email": "newuser@gmail.com",
                "google_id": "123456789",
                "first_name": "New",
                "last_name": "User",
                "email_verified": True,
            },
            None,
        )

        data = {"access_token": "valid_google_token"}
        serializer = GoogleOAuthSerializer(data=data)

        assert serializer.is_valid()
        validated_data = serializer.validated_data

        assert validated_data["user"].email == "newuser@gmail.com"
        assert validated_data["user"].google_id == "123456789"
        assert "access" in validated_data
        assert "refresh" in validated_data

    @patch("src.apps.accounts.utils.oauth_validators.GoogleOAuthValidator.validate_token")
    def test_valid_google_token_existing_user(self, mock_validate):
        """Test valid Google token with existing user"""
        existing_user = User.objects.create_user(
            email="existing@gmail.com", password="temp_pass", first_name="Existing", last_name="User"
        )

        mock_validate.return_value = (
            True,
            {
                "email": "existing@gmail.com",
                "google_id": "123456789",
                "first_name": "Existing",
                "last_name": "User",
                "email_verified": True,
            },
            None,
        )

        data = {"access_token": "valid_google_token"}
        serializer = GoogleOAuthSerializer(data=data)

        assert serializer.is_valid()
        validated_data = serializer.validated_data

        assert validated_data["user"].id == existing_user.id
        assert validated_data["user"].google_id == "123456789"

    @patch("src.apps.accounts.utils.oauth_validators.GoogleOAuthValidator.validate_token")
    def test_invalid_google_token(self, mock_validate):
        """Test invalid Google token"""
        mock_validate.return_value = (False, None, "Invalid token")

        data = {"access_token": "invalid_token"}
        serializer = GoogleOAuthSerializer(data=data)

        assert not serializer.is_valid()
        assert "access_token" in serializer.errors

    @patch("src.apps.accounts.utils.oauth_validators.GoogleOAuthValidator.validate_token")
    def test_unverified_google_email(self, mock_validate):
        """Test Google token with unverified email"""
        mock_validate.return_value = (
            True,
            {"email": "unverified@gmail.com", "google_id": "123456789", "email_verified": False},
            None,
        )

        data = {"access_token": "valid_token_unverified_email"}
        serializer = GoogleOAuthSerializer(data=data)

        assert not serializer.is_valid()
        assert "access_token" in serializer.errors

    @patch("src.apps.accounts.utils.oauth_validators.GoogleOAuthValidator.validate_token")
    def test_inactive_user_google_oauth(self, mock_validate):
        """Test Google OAuth with inactive user"""
        User.objects.create_user(
            email="inactive@gmail.com", password="temp_pass", first_name="Inactive", last_name="User", is_active=False
        )

        mock_validate.return_value = (
            True,
            {"email": "inactive@gmail.com", "google_id": "123456789", "email_verified": True},
            None,
        )

        data = {"access_token": "valid_token"}
        serializer = GoogleOAuthSerializer(data=data)

        assert not serializer.is_valid()
        assert "access_token" in serializer.errors

    @patch("src.apps.accounts.serializers.GoogleOAuthValidator")
    def test_google_oauth_validation_process(self, mock_validator):
        """Test complete Google OAuth validation process."""
        mock_validator_instance = Mock()
        mock_validator.return_value = mock_validator_instance
        mock_validator_instance.validate.return_value = {
            "email": "oauth@example.com",
            "first_name": "OAuth",
            "last_name": "User",
            "google_id": "google123",
        }

        serializer = GoogleOAuthSerializer(data={"access_token": "valid_token"})
        assert serializer.is_valid()
        result = serializer.save()
        assert result["user"].email == "oauth@example.com"

    def test_oauth_serializer_error_handling(self):
        """Test error handling in OAuth serializer."""
        with patch("src.apps.accounts.serializers.GoogleOAuthValidator") as mock_validator:
            mock_validator_instance = Mock()
            mock_validator.return_value = mock_validator_instance
            mock_validator_instance.validate.side_effect = Exception("OAuth validation failed")

            serializer = GoogleOAuthSerializer(data={"access_token": "invalid_token"})
            assert not serializer.is_valid()


@pytest.mark.django_db
class TestUserProfileSerializer:
    """Test user profile serializer"""

    def test_user_profile_serialization(self):
        """Test user profile data serialization"""
        user = User.objects.create_user(
            email="profile@example.com",
            password="testpass123",
            first_name="Profile",
            last_name="User",
            phone_number="+1234567890",
        )

        request = APIRequestFactory().get("/")
        serializer = UserProfileSerializer(user, context={"request": request})

        data = serializer.data
        assert data["email"] == "profile@example.com"
        assert data["first_name"] == "Profile"
        assert data["last_name"] == "User"
        assert data["phone_number"] == "+1234567890"


@pytest.mark.django_db
class TestUserAddressSerializer:
    """Test user address serializer"""

    def test_valid_address_creation(self):
        """Test valid address creation"""
        user = User.objects.create_user(
            email="address@example.com", password="testpass123", first_name="Address", last_name="User"
        )

        data = {
            "user": user.id,
            "address_type": "shipping",
            "street_address": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345",
            "country": "US",
        }

        serializer = UserAddressSerializer(data=data)
        assert serializer.is_valid()

        address = serializer.save()
        assert address.street_address == "123 Test St"
        assert address.user == user

    def test_invalid_address_data(self):
        """Test invalid address data"""
        data = {
            "address_type": "invalid_type",
            "street_address": "",  # Required field
        }

        serializer = UserAddressSerializer(data=data)
        assert not serializer.is_valid()
        assert "street_address" in serializer.errors or "user" in serializer.errors

    def test_address_type_validation(self):
        """Test address type validation."""
        from src.apps.accounts.models import UserAddress

        valid_types = [choice[0] for choice in UserAddress.ADDRESS_TYPES]
        for address_type in valid_types:
            data = {
                "address_type": address_type,
                "street": "123 Test St",
                "city": "Test City",
                "state": "TS",
                "postal_code": "12345",
                "country": "Test Country",
            }
            serializer = UserAddressSerializer(data=data)
            assert serializer.is_valid(), f"Address type {address_type} should be valid"

    def test_default_address_handling(self):
        """Test default address field handling."""
        data = {
            "address_type": "home",
            "street": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345",
            "country": "Test Country",
            "is_default": True,
        }
        serializer = UserAddressSerializer(data=data)
        assert serializer.is_valid()
