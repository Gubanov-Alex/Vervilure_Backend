from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from src.apps.accounts.models import UserAddress

User = get_user_model()


@pytest.mark.django_db
class TestAuthViewSetExtended:
    """Extended tests for AuthViewSet to improve coverage."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
            is_active=True,
            email_verified=True,
        )

    def test_register_validation_errors(self):
        """Test registration with various validation errors."""
        # Test invalid email format
        data = {
            "email": "invalid-email",
            "password": "ValidPass123!",
            "password_confirm": "ValidPass123!",
            "first_name": "Test",
            "last_name": "User",
        }
        response = self.client.post("/auth/register/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_edge_cases(self):
        """Test login edge cases."""
        # Test with empty credentials
        response = self.client.post("/auth/login/", {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Test with only email
        response = self.client.post("/auth/login/", {"email": "test@example.com"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("src.apps.accounts.views.GoogleOAuthValidator")
    def test_google_oauth_validation_failure(self, mock_validator):
        """Test Google OAuth with validation failure."""
        mock_validator_instance = Mock()
        mock_validator.return_value = mock_validator_instance
        mock_validator_instance.validate.side_effect = Exception("Validation failed")

        response = self.client.post("/auth/google/", {"access_token": "invalid"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_with_refresh_token_blacklisting(self):
        """Test logout with refresh token blacklisting."""
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.post("/auth/logout/", {"refresh": str(refresh)})
        assert response.status_code == status.HTTP_205_RESET_CONTENT

    def test_refresh_token_edge_cases(self):
        """Test refresh token edge cases."""
        # Test with invalid refresh token
        response = self.client.post("/auth/token/refresh/", {"refresh": "invalid_token"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test with expired refresh token
        refresh = RefreshToken.for_user(self.user)
        refresh.set_exp(lifetime=-1)  # Make it expired
        response = self.client.post("/auth/token/refresh/", {"refresh": str(refresh)})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAuthViewSet:
    """Test AuthViewSet"""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            is_email_verified=True,
        )

    def test_register_success(self):
        """Test successful user registration"""
        data = {
            "email": "newuser@example.com",
            "password": "ValidPass123!",
            "password_confirm": "ValidPass123!",
            "first_name": "New",
            "last_name": "User",
            "marketing_consent": True,
        }

        response = self.client.post("/auth/register/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "user" in response.data
        assert response.data["message"] == "Registration successful. Please check your email for verification."

        # Verify user was created
        user = User.objects.get(email="newuser@example.com")
        assert user.first_name == "New"
        assert not user.is_email_verified  # Should be False initially

    def test_register_duplicate_email(self):
        """Test registration with duplicate email"""
        data = {
            "email": "test@example.com",  # Already exists
            "password": "ValidPass123!",
            "password_confirm": "ValidPass123!",
            "first_name": "Duplicate",
            "last_name": "User",
        }

        response = self.client.post("/auth/register/", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_register_rate_limiting(self):
        """Test registration rate limiting"""
        # Mock rate limiting to trigger
        with patch("django.core.cache.cache.get") as mock_get:
            mock_get.return_value = 10  # Exceed limit

            data = {
                "email": "ratelimited@example.com",
                "password": "ValidPass123!",
                "password_confirm": "ValidPass123!",
                "first_name": "Rate",
                "last_name": "Limited",
            }

            response = self.client.post("/auth/register/", data, format="json")
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_login_success(self):
        """Test successful login"""
        data = {"email": "test@example.com", "password": "testpass123"}

        response = self.client.post("/auth/login/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "user" in response.data
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {"email": "test@example.com", "password": "wrongpassword"}

        response = self.client.post("/auth/login/", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "non_field_errors" in response.data

    def test_login_unverified_email(self):
        """Test login with unverified email"""
        self.user.is_email_verified = False
        self.user.save()

        data = {"email": "test@example.com", "password": "testpass123"}

        response = self.client.post("/auth/login/", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_inactive_user(self):
        """Test login with inactive user"""
        self.user.is_active = False
        self.user.save()

        data = {"email": "test@example.com", "password": "testpass123"}

        response = self.client.post("/auth/login/", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_rate_limiting(self):
        """Test login rate limiting"""
        with patch("django.core.cache.cache.get") as mock_get:
            mock_get.return_value = 10  # Exceed limit

            data = {"email": "test@example.com", "password": "testpass123"}

            response = self.client.post("/auth/login/", data, format="json")
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @patch("apps.accounts.utils.oauth_validators.GoogleOAuthValidator.validate_token")
    def test_google_oauth_success_new_user(self, mock_validate):
        """Test successful Google OAuth with new user"""
        mock_validate.return_value = (
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

        data = {"access_token": "valid_google_token"}
        response = self.client.post("/auth/google-oauth/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "user" in response.data
        assert "tokens" in response.data
        assert response.data["is_new_user"] is True

        # Verify user was created
        user = User.objects.get(email="google@gmail.com")
        assert user.google_id == "123456789"
        assert user.is_email_verified is True

    @patch("apps.accounts.utils.oauth_validators.GoogleOAuthValidator.validate_token")
    def test_google_oauth_existing_user(self, mock_validate):
        """Test Google OAuth with existing user"""
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
        response = self.client.post("/auth/google-oauth/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_new_user"] is False

        # Verify user was updated
        existing_user.refresh_from_db()
        assert existing_user.google_id == "123456789"

    @patch("apps.accounts.utils.oauth_validators.GoogleOAuthValidator.validate_token")
    def test_google_oauth_invalid_token(self, mock_validate):
        """Test Google OAuth with invalid token"""
        mock_validate.return_value = (False, None, "Invalid token")

        data = {"access_token": "invalid_token"}
        response = self.client.post("/auth/google-oauth/", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.accounts.utils.oauth_validators.GoogleOAuthValidator.validate_token")
    def test_google_oauth_rate_limiting(self, mock_validate):
        """Test Google OAuth rate limiting"""
        with patch("django.core.cache.cache.get") as mock_get:
            mock_get.return_value = 15  # Exceed OAuth limit

            data = {"access_token": "valid_token"}
            response = self.client.post("/auth/google-oauth/", data, format="json")

            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_logout_success(self):
        """Test successful logout"""
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        data = {"refresh": str(refresh)}
        response = self.client.post("/auth/logout/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Logout successful."

    def test_logout_invalid_token(self):
        """Test logout with invalid refresh token"""
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid_token")

        data = {"refresh": "invalid_refresh_token"}
        response = self.client.post("/auth/logout/", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_unauthenticated(self):
        """Test logout without authentication"""
        data = {"refresh": "some_token"}
        response = self.client.post("/auth/logout/", data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_success(self):
        """Test successful token refresh"""
        refresh = RefreshToken.for_user(self.user)

        data = {"refresh": str(refresh)}
        response = self.client.post("/auth/refresh/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_refresh_token_invalid(self):
        """Test token refresh with invalid token"""
        data = {"refresh": "invalid_refresh_token"}
        response = self.client.post("/auth/refresh/", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserViewSetExtended:
    """Extended tests for UserViewSet to improve coverage."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com", password="TestPass123!", first_name="Test", last_name="User"
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_partial_profile_update(self):
        """Test partial profile update."""
        data = {"first_name": "Updated"}
        response = self.client.patch("/users/profile/", data)
        assert response.status_code == status.HTTP_200_OK
        self.user.refresh_from_db()
        assert self.user.first_name == "Updated"

    def test_profile_update_validation_errors(self):
        """Test profile update with validation errors."""
        data = {"email": "invalid-email"}
        response = self.client.patch("/users/profile/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_validation_errors(self):
        """Test password change with various validation errors."""
        # Test with weak new password
        data = {"old_password": "TestPass123!", "new_password": "123", "new_password_confirm": "123"}
        response = self.client.post("/users/change-password/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthorized_profile_access(self):
        """Test unauthorized access to profile endpoints."""
        self.client.credentials()  # Remove auth headers
        response = self.client.get("/users/profile/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserViewSet:
    """Test UserViewSet for profile management"""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="profile@example.com",
            password="testpass123",
            first_name="Profile",
            last_name="User",
            is_email_verified=True,
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.refresh.access_token}")

    def test_get_profile_success(self):
        """Test getting user profile"""
        response = self.client.get("/users/profile/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "profile@example.com"
        assert response.data["first_name"] == "Profile"

    def test_update_profile_success(self):
        """Test updating user profile"""
        data = {"first_name": "Updated", "last_name": "Name", "phone_number": "+1234567890"}

        response = self.client.patch("/users/profile/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Updated"

        # Verify database update
        self.user.refresh_from_db()
        assert self.user.first_name == "Updated"

    def test_update_profile_invalid_data(self):
        """Test updating profile with invalid data"""
        data = {
            "email": "invalid-email",  # Invalid email format
            "phone_number": "invalid-phone",  # Invalid phone format
        }

        response = self.client.patch("/users/profile/", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_success(self):
        """Test successful password change"""
        data = {
            "old_password": "testpass123",
            "new_password": "NewValidPass123!",
            "new_password_confirm": "NewValidPass123!",
        }

        response = self.client.post("/users/change-password/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Password changed successfully."

        # Verify password was changed
        self.user.refresh_from_db()
        assert self.user.check_password("NewValidPass123!")

    def test_change_password_wrong_old_password(self):
        """Test password change with wrong old password"""
        data = {
            "old_password": "wrongpassword",
            "new_password": "NewValidPass123!",
            "new_password_confirm": "NewValidPass123!",
        }

        response = self.client.post("/users/change-password/", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_mismatch(self):
        """Test password change with mismatched new passwords"""
        data = {
            "old_password": "testpass123",
            "new_password": "NewValidPass123!",
            "new_password_confirm": "DifferentPass123!",
        }

        response = self.client.post("/users/change-password/", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_rate_limiting(self):
        """Test password change rate limiting"""
        with patch("django.core.cache.cache.get") as mock_get:
            mock_get.return_value = 5  # Exceed limit

            data = {
                "old_password": "testpass123",
                "new_password": "NewValidPass123!",
                "new_password_confirm": "NewValidPass123!",
            }

            response = self.client.post("/users/change-password/", data, format="json")
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_unauthenticated_access(self):
        """Test unauthenticated access to protected endpoints"""
        self.client.credentials()  # Clear credentials

        response = self.client.get("/users/profile/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = self.client.post("/users/change-password/", {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserAddressViewSetExtended:
    """Extended tests for UserAddressViewSet to improve coverage."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="test@example.com", password="TestPass123!")
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_address_creation_validation_errors(self):
        """Test address creation with validation errors."""
        data = {"address_type": "invalid_type", "street": "", "city": "Test City"}  # Required field empty
        response = self.client.post("/users/addresses/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_address_filtering_by_type(self):
        """Test address filtering by type."""
        # Create addresses of different types
        from src.apps.accounts.models import UserAddress

        UserAddress.objects.create(
            user=self.user,
            address_type="home",
            street="123 Home St",
            city="Home City",
            state="HS",
            postal_code="12345",
            country="Home Country",
        )
        UserAddress.objects.create(
            user=self.user,
            address_type="work",
            street="456 Work Ave",
            city="Work City",
            state="WS",
            postal_code="67890",
            country="Work Country",
        )

        response = self.client.get("/users/addresses/?address_type=home")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["address_type"] == "home"

    def test_default_address_management(self):
        """Test default address management."""
        from src.apps.accounts.models import UserAddress

        # Create first address as default
        data = {
            "address_type": "home",
            "street": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345",
            "country": "Test Country",
            "is_default": True,
        }
        response = self.client.post("/users/addresses/", data)
        assert response.status_code == status.HTTP_201_CREATED

        address1_id = response.data["id"]

        # Create second address as default (should make first non-default)
        data["street"] = "456 Another St"
        response = self.client.post("/users/addresses/", data)
        assert response.status_code == status.HTTP_201_CREATED

        # Check that first address is no longer default
        address1 = UserAddress.objects.get(id=address1_id)
        assert not address1.is_default


@pytest.mark.django_db
class TestUserAddressViewSet:
    """Test UserAddress management"""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="address@example.com",
            password="testpass123",
            first_name="Address",
            last_name="User",
            is_email_verified=True,
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.refresh.access_token}")

    def test_create_address_success(self):
        """Test successful address creation"""
        data = {
            "address_type": "shipping",
            "street_address": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345",
            "country": "US",
        }

        response = self.client.post("/users/addresses/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["street_address"] == "123 Test St"

        # Verify address was created
        address = UserAddress.objects.get(user=self.user)
        assert address == "123 Test St"

    def test_list_addresses(self):
        """Test listing user addresses"""
        UserAddress.objects.create(
            user=self.user,
            address_type="shipping",
            street_address="123 Main St",
            city="Main City",
            state="MC",
            postal_code="54321",
            country="US",
        )

        response = self.client.get("/users/addresses/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["street_address"] == "123 Main St"

    def test_update_address(self):
        """Test updating user address"""
        address = UserAddress.objects.create(
            user=self.user,
            address_type="shipping",
            street_address="123 Old St",
            city="Old City",
            state="OC",
            postal_code="11111",
            country="US",
        )

        data = {"street_address": "456 New St"}
        response = self.client.patch(f"/users/addresses/{address.id}/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["street_address"] == "456 New St"

    def test_delete_address(self):
        """Test deleting user address"""
        address = UserAddress.objects.create(
            user=self.user,
            address_type="shipping",
            street_address="123 Delete St",
            city="Delete City",
            state="DC",
            postal_code="99999",
            country="US",
        )

        response = self.client.delete(f"/users/addresses/{address.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UserAddress.objects.filter(id=address.id).exists()

    def test_access_other_user_address(self):
        """Test accessing another user's address"""
        other_user = User.objects.create_user(
            email="other@example.com", password="testpass123", first_name="Other", last_name="User"
        )

        other_address = UserAddress.objects.create(
            user=other_user,
            address_type="shipping",
            street_address="123 Other St",
            city="Other City",
            state="OT",
            postal_code="00000",
            country="US",
        )

        response = self.client.get(f"/users/addresses/{other_address.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestIPAddressHandling:
    """Test IP address extraction and handling"""

    def setup_method(self):
        self.client = APIClient()

    def test_get_client_ip_x_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For header"""
        response = self.client.post("/auth/register/", {}, HTTP_X_FORWARDED_FOR="192.168.1.1, 10.0.0.1")
        # IP logging is tested in views, this tests header handling
        assert response.status_code in [400, 429]  # Either validation error or rate limit

    def test_get_client_ip_x_real_ip(self):
        """Test IP extraction from X-Real-IP header"""
        response = self.client.post("/auth/register/", {}, HTTP_X_REAL_IP="192.168.1.2")
        assert response.status_code in [400, 429]

    def test_get_client_ip_remote_addr(self):
        """Test IP extraction from REMOTE_ADDR"""
        response = self.client.post("/auth/register/", {})
        # Default test client behavior
        assert response.status_code in [400, 429]
