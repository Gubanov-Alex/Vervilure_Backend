from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from src.core.testing.google_oauth_tester import GoogleOAuthTester

User = get_user_model()


@pytest.mark.django_db
class TestGoogleOAuthIntegration:
    """Google OAuth integration tests for CI/CD."""

    def test_google_oauth_management_command(self):
        """Test Google OAuth management command execution."""
        out = StringIO()

        call_command("test_google_oauth", skip_cleanup=True, stdout=out)

        output = out.getvalue()
        assert "GOOGLE OAUTH TEST RESULTS" in output

    def test_google_oauth_configuration_validation(self):
        """Test Google OAuth configuration validation."""
        tester = GoogleOAuthTester()
        result = tester._test_oauth_configuration()

        # Should either be configured or properly report missing config
        assert result.success or "not configured" in result.message.lower()

    def test_oauth_user_creation_flow(self):
        """Test OAuth user creation process."""
        tester = GoogleOAuthTester()
        result = tester._test_oauth_user_creation()

        assert result.success
        assert result.data["email"] == "oauth.testuser@gmail.com"

    def test_jwt_generation_for_oauth_user(self):
        """Test JWT generation for OAuth users."""
        tester = GoogleOAuthTester()

        # First create OAuth user
        user_result = tester._test_oauth_user_creation()
        assert user_result.success

        # Then test JWT generation
        jwt_result = tester._test_jwt_for_oauth_user()
        assert jwt_result.success
        assert jwt_result.data["tokens_generated"] is True
