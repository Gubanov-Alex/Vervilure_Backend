from unittest.mock import patch

import pytest
from src.apps.accounts.utils import GoogleOAuthValidator


class TestGoogleOAuthValidator:
    """Test OAuth validator for Google OAuth2"""

    @pytest.fixture
    def validator(self):
        return GoogleOAuthValidator("test_client_id")

    def test_init_with_client_id(self):
        """Test validator initialization"""
        validator = GoogleOAuthValidator("test_client_id")
        assert validator.client_id == "test_client_id"

    @pytest.mark.parametrize(
        "token,expected_valid",
        [
            ("valid_token_string", True),
            ("", False),
            (None, False),
            ("   ", False),
            ("short", False),
        ],
    )
    def test_validate_token_format(self, validator, token, expected_valid):
        """Test basic token format validation"""
        with patch.object(validator, "_verify_with_google") as mock_verify:
            mock_verify.return_value = (True, {"email": "test@test.com"}, None)

            is_valid, user_info, error = validator.validate_token(token)

            if expected_valid and token and token.strip():
                assert is_valid is True
                mock_verify.assert_called_once()
            else:
                assert is_valid is False
                assert error is not None

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_verify_with_google_success(self, mock_verify, validator):
        """Test successful Google verification"""
        mock_verify.return_value = {
            "iss": "accounts.google.com",
            "aud": "test_client_id",
            "sub": "123456789",
            "email": "test@gmail.com",
            "email_verified": True,
            "given_name": "Test",
            "family_name": "User",
        }

        is_valid, user_info, error = validator._verify_with_google("valid_token")

        assert is_valid is True
        assert user_info["email"] == "test@gmail.com"
        assert user_info["google_id"] == "123456789"
        assert error is None

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_verify_with_google_invalid_token(self, mock_verify, validator):
        """Test invalid token handling"""
        mock_verify.side_effect = ValueError("Token verification failed")

        is_valid, user_info, error = validator._verify_with_google("invalid_token")

        assert is_valid is False
        assert user_info is None
        assert "Token verification failed" in error

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_verify_with_google_network_error(self, mock_verify, validator):
        """Test network error handling"""
        mock_verify.side_effect = Exception("Network timeout")

        is_valid, user_info, error = validator._verify_with_google("token")

        assert is_valid is False
        assert user_info is None
        assert "Network timeout" in error

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_verify_wrong_audience(self, mock_verify, validator):
        """Test wrong client_id in token"""
        mock_verify.return_value = {
            "iss": "accounts.google.com",
            "aud": "wrong_client_id",
            "sub": "123456789",
            "email": "test@gmail.com",
        }

        is_valid, user_info, error = validator._verify_with_google("token")

        assert is_valid is False
        assert "Invalid audience" in error

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_verify_unverified_email(self, mock_verify, validator):
        """Test unverified email from Google"""
        mock_verify.return_value = {
            "iss": "accounts.google.com",
            "aud": "test_client_id",
            "sub": "123456789",
            "email": "test@gmail.com",
            "email_verified": False,
        }

        is_valid, user_info, error = validator._verify_with_google("token")

        assert is_valid is False
        assert "Email not verified" in error

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_verify_missing_required_fields(self, mock_verify, validator):
        """Test token missing required fields"""
        mock_verify.return_value = {
            "iss": "accounts.google.com",
            "aud": "test_client_id",
            # Missing sub and email
        }

        is_valid, user_info, error = validator._verify_with_google("token")

        assert is_valid is False
        assert "Missing required fields" in error

    def test_full_validation_flow_success(self, validator):
        """Test complete validation flow"""
        with patch.object(validator, "_verify_with_google") as mock_verify:
            mock_verify.return_value = (
                True,
                {
                    "email": "test@gmail.com",
                    "google_id": "123456789",
                    "first_name": "Test",
                    "last_name": "User",
                    "email_verified": True,
                },
                None,
            )

            is_valid, user_info, error = validator.validate_token("valid_token")

            assert is_valid is True
            assert user_info["email"] == "test@gmail.com"
            assert error is None

    def test_validate_token_empty_string(self, validator):
        """Test validation with empty token string"""
        is_valid, user_info, error = validator.validate_token("")

        assert is_valid is False
        assert user_info is None
        assert "Token cannot be empty" in error

    def test_validate_token_none(self, validator):
        """Test validation with None token"""
        is_valid, user_info, error = validator.validate_token(None)

        assert is_valid is False
        assert user_info is None
        assert "Token cannot be empty" in error
