"""Tests for OAuth validators"""

from unittest.mock import Mock, patch

import pytest
from src.apps.accounts.utils.oauth_validators import GoogleOAuthValidator


class TestGoogleOAuthValidator:
    """Test OAuth validator for Google OAuth2 - testing existing implementation"""

    @pytest.fixture
    def validator(self):
        return GoogleOAuthValidator("test_client_id")

    def test_init_with_client_id(self):
        """Test validator initialization"""
        validator = GoogleOAuthValidator("test_client_id")
        assert validator.client_id == "test_client_id"

    @patch.object(GoogleOAuthValidator, "_get_token_info")
    @patch.object(GoogleOAuthValidator, "_get_user_info")
    @patch.object(GoogleOAuthValidator, "_process_user_info")
    def test_validate_token_success(self, mock_process, mock_user_info, mock_token_info, validator):
        """Test successful token validation"""
        # Mock the private methods that exist in the real implementation
        mock_token_info.return_value = {"audience": "test_client_id"}
        mock_user_info.return_value = {"email": "test@gmail.com", "id": "123"}
        mock_process.return_value = {
            "google_id": "123456789",
            "email": "test@gmail.com",
            "email_verified": True,
            "first_name": "Test",
            "last_name": "User",
        }

        is_valid, user_info, error = validator.validate_token("valid_token")

        assert is_valid is True
        assert user_info is not None
        assert error is None
        assert user_info["email"] == "test@gmail.com"

    def test_validate_token_empty_string(self, validator):
        """Test validation with empty token string"""
        is_valid, user_info, error = validator.validate_token("")

        assert is_valid is False
        assert user_info is None
        assert error is not None

    def test_validate_token_none(self, validator):
        """Test validation with None token"""
        is_valid, user_info, error = validator.validate_token(None)

        assert is_valid is False
        assert user_info is None
        assert error is not None

    @patch.object(GoogleOAuthValidator, "_get_token_info")
    def test_validate_token_invalid_token_info(self, mock_token_info, validator):
        """Test with invalid token info"""
        mock_token_info.return_value = None

        is_valid, user_info, error = validator.validate_token("invalid_token")

        assert is_valid is False
        assert user_info is None
        assert "Invalid token" in error

    @patch.object(GoogleOAuthValidator, "_get_token_info")
    def test_validate_token_wrong_audience(self, mock_token_info, validator):
        """Test with wrong audience"""
        mock_token_info.return_value = {"audience": "wrong_client_id"}

        is_valid, user_info, error = validator.validate_token("valid_token")

        assert is_valid is False
        assert user_info is None
        assert "not issued for this application" in error

    @patch.object(GoogleOAuthValidator, "_get_token_info")
    @patch.object(GoogleOAuthValidator, "_get_user_info")
    def test_validate_token_no_user_info(self, mock_user_info, mock_token_info, validator):
        """Test when user info cannot be retrieved"""
        mock_token_info.return_value = {"audience": "test_client_id"}
        mock_user_info.return_value = None

        is_valid, user_info, error = validator.validate_token("valid_token")

        assert is_valid is False
        assert user_info is None
        assert "Could not retrieve user information" in error

    @patch("requests.get")
    def test_get_token_info_success(self, mock_get, validator):
        """Test successful token info retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"audience": "test_client_id"}
        mock_get.return_value = mock_response

        result = validator._get_token_info("valid_token")

        assert result is not None
        assert result["audience"] == "test_client_id"

    @patch("requests.get")
    def test_get_token_info_failure(self, mock_get, validator):
        """Test failed token info retrieval"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_get.return_value = mock_response

        result = validator._get_token_info("invalid_token")

        assert result is None

    @patch("requests.get")
    def test_get_token_info_network_error(self, mock_get, validator):
        """Test network error during token info retrieval - fixed exception handling"""
        mock_get.side_effect = Exception("Network error")

        # The method should handle the exception and return None
        result = validator._get_token_info("valid_token")

        assert result is None

    @patch("requests.get")
    def test_get_user_info_success(self, mock_get, validator):
        """Test successful user info retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "email": "test@gmail.com",
            "id": "123456789",
            "given_name": "Test",
            "family_name": "User",
        }
        mock_get.return_value = mock_response

        result = validator._get_user_info("valid_token")

        assert result is not None
        assert result["email"] == "test@gmail.com"

    @patch("requests.get")
    def test_get_user_info_failure(self, mock_get, validator):
        """Test failed user info retrieval"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = validator._get_user_info("invalid_token")

        assert result is None

    @patch("requests.get")
    def test_get_user_info_network_error(self, mock_get, validator):
        """Test network error during user info retrieval - fixed exception handling"""
        mock_get.side_effect = Exception("Network error")

        # The method should handle the exception and return None
        result = validator._get_user_info("valid_token")

        assert result is None

    def test_process_user_info(self, validator):
        """Test user info processing"""
        raw_info = {
            "id": "123456789",
            "email": "test@gmail.com",
            "verified_email": True,
            "given_name": "Test",
            "family_name": "User",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
            "locale": "en",
        }

        result = validator._process_user_info(raw_info)

        assert result["google_id"] == "123456789"
        assert result["email"] == "test@gmail.com"
        assert result["email_verified"] is True
        assert result["first_name"] == "Test"
        assert result["last_name"] == "User"
        assert result["full_name"] == "Test User"
        assert result["picture_url"] == "https://example.com/photo.jpg"
        assert result["locale"] == "en"

    def test_process_user_info_minimal(self, validator):
        """Test user info processing with minimal data"""
        raw_info = {"id": "123456789", "email": "test@gmail.com"}

        result = validator._process_user_info(raw_info)

        assert result["google_id"] == "123456789"
        assert result["email"] == "test@gmail.com"
        assert result["email_verified"] is False  # Default value
        assert result["first_name"] == ""  # Default value
        assert result["last_name"] == ""  # Default value

    @patch("requests.get")
    def test_validate_token_request_exception(self, mock_get, validator):
        """Test request exception handling"""
        mock_get.side_effect = Exception("Connection failed")

        is_valid, user_info, error = validator.validate_token("valid_token")

        assert is_valid is False
        assert user_info is None
        assert "Token validation failed" in error

    @patch.object(GoogleOAuthValidator, "_get_token_info")
    @patch.object(GoogleOAuthValidator, "_get_user_info")
    @patch.object(GoogleOAuthValidator, "_process_user_info")
    def test_validate_token_processing_exception(self, mock_process, mock_user_info, mock_token_info, validator):
        """Test exception during user info processing"""
        mock_token_info.return_value = {"audience": "test_client_id"}
        mock_user_info.return_value = {"email": "test@gmail.com"}
        mock_process.side_effect = Exception("Processing failed")

        is_valid, user_info, error = validator.validate_token("valid_token")

        assert is_valid is False
        assert user_info is None
        assert "Token validation failed" in error

    @patch("requests.get")
    def test_get_token_info_timeout_handling(self, mock_get, validator):
        """Test timeout handling during token info retrieval"""
        import requests

        mock_get.side_effect = requests.Timeout("Request timed out")

        result = validator._get_token_info("valid_token")

        assert result is None

    @patch("requests.get")
    def test_get_user_info_timeout_handling(self, mock_get, validator):
        """Test timeout handling during user info retrieval"""
        import requests

        mock_get.side_effect = requests.Timeout("Request timed out")

        result = validator._get_user_info("valid_token")

        assert result is None

    @patch("requests.get")
    def test_get_token_info_connection_error(self, mock_get, validator):
        """Test connection error handling"""
        import requests

        mock_get.side_effect = requests.ConnectionError("Connection failed")

        result = validator._get_token_info("valid_token")

        assert result is None

    @patch("requests.get")
    def test_get_user_info_json_decode_error(self, mock_get, validator):
        """Test JSON decode error handling"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        result = validator._get_user_info("valid_token")

        assert result is None

    def test_process_user_info_missing_required_fields(self, validator):
        """Test processing user info with missing required fields"""
        raw_info = {}  # Empty info

        result = validator._process_user_info(raw_info)

        # Should handle missing fields gracefully
        assert result["google_id"] == ""
        assert result["email"] == ""
        assert result["email_verified"] is False

    def test_process_user_info_partial_name_data(self, validator):
        """Test processing user info with partial name data"""
        raw_info = {
            "id": "123456789",
            "email": "test@gmail.com",
            "given_name": "Test",  # Only first name
            # Missing family_name
        }

        result = validator._process_user_info(raw_info)

        assert result["first_name"] == "Test"
        assert result["last_name"] == ""  # Should default to empty string

    @patch.object(GoogleOAuthValidator, "_get_token_info")
    def test_validate_token_malformed_token_info(self, mock_token_info, validator):
        """Test handling of malformed token info response"""
        mock_token_info.return_value = {"malformed": "response"}  # Missing audience

        is_valid, user_info, error = validator.validate_token("valid_token")

        assert is_valid is False
        assert user_info is None
        assert error is not None

    def test_validate_token_with_whitespace(self, validator):
        """Test token validation with whitespace"""
        is_valid, user_info, error = validator.validate_token("   ")

        assert is_valid is False
        assert user_info is None
        assert error is not None
