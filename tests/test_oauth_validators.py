from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError
from src.apps.accounts.utils.oauth_validators import GoogleOAuthValidator


class TestGoogleOAuthValidator:
    """Test OAuth validator for Google OAuth2"""

    @pytest.fixture
    def validator(self):
        return GoogleOAuthValidator("test_client_id")

    def test_init_with_client_id(self):
        """Test validator initialization"""
        validator = GoogleOAuthValidator("test_client_id")
        assert validator.client_id == "test_client_id"

    def test_validate_token_format_valid(self):
        """Test valid token format"""
        validator = GoogleOAuthValidator("test_client_id")

        # Test with proper mock
        with patch.object(validator, "verify_with_google") as mock_verify:
            mock_verify.return_value = {
                "email": "test@gmail.com",
                "email_verified": True,
                "given_name": "Test",
                "family_name": "User",
                "sub": "123456789",
                "aud": "test_client_id",
            }

            result = validator.validate("valid_token_string")
            assert result["email"] == "test@gmail.com"

    def test_validate_token_format_invalid(self):
        """Test invalid token formats"""
        validator = GoogleOAuthValidator("test_client_id")

        # Test empty string
        with pytest.raises(ValidationError):
            validator.validate("")

        # Test None
        with pytest.raises(ValidationError):
            validator.validate(None)

        # Test whitespace only
        with pytest.raises(ValidationError):
            validator.validate("   ")

    @patch("requests.get")
    def test_verify_with_google_success(self, mock_get, validator):
        """Test successful Google verification"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "iss": "accounts.google.com",
            "aud": "test_client_id",
            "sub": "123456789",
            "email": "test@gmail.com",
            "email_verified": True,
            "given_name": "Test",
            "family_name": "User",
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = validator.verify_with_google("valid_token")

        assert result["email"] == "test@gmail.com"
        assert result["sub"] == "123456789"

    @patch("requests.get")
    def test_verify_with_google_invalid_token(self, mock_get, validator):
        """Test invalid token handling"""
        mock_response = Mock()
        mock_response.json.return_value = {"error": "invalid_token", "error_description": "Token is invalid"}
        mock_response.status_code = 400
        mock_get.return_value = mock_response

        with pytest.raises(ValidationError) as exc_info:
            validator.verify_with_google("invalid_token")

        assert "invalid_token" in str(exc_info.value)

    @patch("requests.get")
    def test_verify_with_google_network_error(self, mock_get, validator):
        """Test network error handling"""
        mock_get.side_effect = ConnectionError("Network timeout")

        with pytest.raises(ValidationError) as exc_info:
            validator.verify_with_google("token")

        assert "network" in str(exc_info.value).lower() or "connection" in str(exc_info.value).lower()

    @patch("requests.get")
    def test_verify_wrong_audience(self, mock_get, validator):
        """Test wrong client_id in token"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "iss": "accounts.google.com",
            "aud": "wrong_client_id",
            "sub": "123456789",
            "email": "test@gmail.com",
            "email_verified": True,
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with pytest.raises(ValidationError) as exc_info:
            validator.verify_with_google("token")

        assert "audience" in str(exc_info.value).lower()

    @patch("requests.get")
    def test_verify_unverified_email(self, mock_get, validator):
        """Test unverified email from Google"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "iss": "accounts.google.com",
            "aud": "test_client_id",
            "sub": "123456789",
            "email": "test@gmail.com",
            "email_verified": False,
            "given_name": "Test",
            "family_name": "User",
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with pytest.raises(ValidationError) as exc_info:
            validator.verify_with_google("token")

        assert "verified" in str(exc_info.value).lower()

    @patch("requests.get")
    def test_verify_missing_required_fields(self, mock_get, validator):
        """Test token missing required fields"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "iss": "accounts.google.com",
            "aud": "test_client_id",
            # Missing sub and email
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with pytest.raises(ValidationError) as exc_info:
            validator.verify_with_google("token")

        assert "required" in str(exc_info.value).lower()

    def test_full_validation_flow_success(self, validator):
        """Test complete validation flow"""
        with patch.object(validator, "verify_with_google") as mock_verify:
            mock_verify.return_value = {
                "email": "test@gmail.com",
                "sub": "123456789",
                "given_name": "Test",
                "family_name": "User",
                "email_verified": True,
                "aud": "test_client_id",
            }

            result = validator.validate("valid_token")

            assert result["email"] == "test@gmail.com"
            assert result["google_id"] == "123456789"
            assert result["first_name"] == "Test"
            assert result["last_name"] == "User"

    def test_validate_token_empty_string(self, validator):
        """Test validation with empty token string"""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate("")

        assert "empty" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()

    def test_validate_token_none(self, validator):
        """Test validation with None token"""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(None)

        assert "empty" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()

    def test_validate_token_format_validation(self, validator):
        """Test token format validation"""
        # Test basic format validation
        with pytest.raises(ValidationError):
            validator.validate_token_format("")

        with pytest.raises(ValidationError):
            validator.validate_token_format(None)

        with pytest.raises(ValidationError):
            validator.validate_token_format("   ")

    @patch("requests.get")
    def test_http_error_handling(self, mock_get, validator):
        """Test HTTP error responses"""
        # Test 500 server error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with pytest.raises(ValidationError):
            validator.verify_with_google("token")

    @patch("requests.get")
    def test_json_decode_error(self, mock_get, validator):
        """Test JSON decode error handling"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        with pytest.raises(ValidationError):
            validator.verify_with_google("token")

    @patch("requests.get")
    def test_timeout_error(self, mock_get, validator):
        """Test timeout error handling"""
        import requests

        mock_get.side_effect = requests.Timeout("Request timeout")

        with pytest.raises(ValidationError) as exc_info:
            validator.verify_with_google("token")

        assert "timeout" in str(exc_info.value).lower()

    def test_user_info_validation_success(self, validator):
        """Test successful user info validation"""
        user_info = {
            "email": "test@example.com",
            "email_verified": True,
            "given_name": "Test",
            "family_name": "User",
            "sub": "google123",
            "aud": "test_client_id",
        }

        # This should not raise an exception
        validator.validate_user_info(user_info)

    def test_user_info_validation_missing_email(self, validator):
        """Test user info validation with missing email"""
        user_info = {
            "email_verified": True,
            "given_name": "Test",
            "family_name": "User",
            "sub": "google123",
            "aud": "test_client_id",
        }

        with pytest.raises(ValidationError):
            validator.validate_user_info(user_info)

    def test_audience_validation_success(self, validator):
        """Test successful audience validation"""
        user_info = {"aud": "test_client_id"}
        # Should not raise exception
        validator.validate_audience(user_info)

    def test_audience_validation_failure(self, validator):
        """Test audience validation failure"""
        user_info = {"aud": "wrong_client_id"}
        with pytest.raises(ValidationError):
            validator.validate_audience(user_info)
