"""Tests for OAuth validators"""

from unittest.mock import Mock, patch

import pytest
from src.apps.accounts.utils.oauth_validators import GoogleOAuthValidator


class TestGoogleOAuthValidator:
    """Test OAuth validator for Google OAuth2 - testing existing implementation"""

    @pytest.fixture
    def validator(self):
        """Create validator instance for testing."""
        return GoogleOAuthValidator("test_client_id")

    def test_init_with_client_id(self):
        """Test validator initialization - БЕЗ использования БД"""
        validator = GoogleOAuthValidator("test_client_id")
        assert validator.client_id == "test_client_id"

    @patch.object(GoogleOAuthValidator, "_get_token_info")
    @patch.object(GoogleOAuthValidator, "_get_user_info")
    @patch.object(GoogleOAuthValidator, "_process_user_info")
    def test_validate_token_success(self, mock_process, mock_user_info, mock_token_info, validator):
        """Test successful token validation - БЕЗ использования БД"""
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
        """Test validation with empty token string - БЕЗ использования БД"""
        is_valid, user_info, error = validator.validate_token("")

        assert is_valid is False
        assert user_info is None
        assert error is not None

    def test_validate_token_none(self, validator):
        """Test validation with None token - БЕЗ использования БД"""
        is_valid, user_info, error = validator.validate_token(None)

        assert is_valid is False
        assert user_info is None
        assert error is not None

    @patch("requests.get")
    def test_get_token_info_network_error(self, mock_get, validator):
        """Test network error during token info retrieval - ИСПРАВЛЕНО, БЕЗ БД"""
        mock_get.side_effect = Exception("Network error")

        result = validator._get_token_info("valid_token")

        assert result is None

    @patch("requests.get")
    def test_get_user_info_network_error(self, mock_get, validator):
        """Test network error during user info retrieval - ИСПРАВЛЕНО, БЕЗ БД"""
        mock_get.side_effect = Exception("Network error")

        result = validator._get_user_info("valid_token")

        assert result is None

    @patch("requests.get")
    def test_get_user_info_json_decode_error(self, mock_get, validator):
        """Test JSON decode error handling - ИСПРАВЛЕНО, БЕЗ БД"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        result = validator._get_user_info("valid_token")

        assert result is None

    def test_process_user_info_missing_required_fields(self, validator):
        """Test processing user info with missing required fields - ИСПРАВЛЕНО, БЕЗ БД"""
        raw_info = {}  # Empty info

        result = validator._process_user_info(raw_info)

        assert result["google_id"] == ""
        assert result["email"] == ""
        assert result["email_verified"] is False

    @patch.object(GoogleOAuthValidator, "_get_token_info")
    def test_validate_token_invalid_token_info(self, mock_token_info, validator):
        """Test with invalid token info - БЕЗ использования БД"""
        mock_token_info.return_value = None

        is_valid, user_info, error = validator.validate_token("invalid_token")

        assert is_valid is False
        assert user_info is None
        assert "Invalid token" in error

    @patch.object(GoogleOAuthValidator, "_get_token_info")
    def test_validate_token_wrong_audience(self, mock_token_info, validator):
        """Test with wrong audience - БЕЗ использования БД"""
        mock_token_info.return_value = {"audience": "wrong_client_id"}

        is_valid, user_info, error = validator.validate_token("valid_token")

        assert is_valid is False
        assert user_info is None
        assert "not issued for this application" in error

    def test_process_user_info(self, validator):
        """Test user info processing - БЕЗ использования БД"""
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
