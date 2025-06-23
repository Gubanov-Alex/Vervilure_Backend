import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from src.core.testing.google_oauth_tester import GoogleOAuthTester

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Management command for Google OAuth testing."""

    help = "Run comprehensive Google OAuth authentication tests"

    def add_arguments(self, parser):
        parser.add_argument("--security-only", action="store_true", help="Run only security-focused tests")

        parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

        parser.add_argument("--skip-cleanup", action="store_true", help="Skip cleanup after tests")

    def handle(self, *args, **options):
        """Execute Google OAuth tests."""
        verbose = options["verbose"]
        skip_cleanup = options["skip_cleanup"]

        self.stdout.write(self.style.HTTP_INFO(f"Starting Google OAuth tests at {timezone.now()}"))

        try:
            # Initialize tester
            # Run full OAuth test suite
            tester = GoogleOAuthTester()
            results = tester.run_all_google_oauth_tests()
            self.stdout.write("Running Complete OAuth Test Suite")

            # Display results
            self._display_oauth_results(results, verbose)

            # Count failures
            failures = sum(1 for result in results.values() if not result.success)
            total_tests = len(results)

            if failures == 0:
                self.stdout.write(self.style.SUCCESS(f"✅ All {total_tests} Google OAuth tests passed!"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ {failures}/{total_tests} Google OAuth tests failed"))

            # Cleanup
            if not skip_cleanup:
                self._cleanup_oauth_test_data()

        except Exception as e:
            logger.exception("Google OAuth test command failed")
            self.stdout.write(self.style.ERROR(f"Critical error: {str(e)}"))
            raise

    def _display_oauth_results(self, results: dict, verbose: bool = False):
        """Display Google OAuth test results."""
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.HTTP_INFO("GOOGLE OAUTH TEST RESULTS"))
        self.stdout.write("=" * 60)

        # Group results by category
        categories = {
            "Configuration": ["config_validation", "django_allauth_setup", "site_configuration"],
            "OAuth Flow": ["oauth_flow_simulation", "token_exchange", "user_info_retrieval"],
            "User Management": ["oauth_user_creation", "oauth_user_linking", "duplicate_oauth_handling"],
            "JWT Integration": ["jwt_for_oauth_user", "oauth_jwt_endpoints"],
            "Security": ["invalid_token_handling", "oauth_csrf_protection", "oauth_state_validation"],
            "Edge Cases": ["email_domain_restrictions", "oauth_logout_flow"],
        }

        for category, test_names in categories.items():
            self.stdout.write(f"\n{self.style.WARNING(f'--- {category} ---')}")

            for test_name in test_names:
                if test_name in results:
                    result = results[test_name]

                    if result.success:
                        status_icon = "✅"
                        status_style = self.style.SUCCESS
                    else:
                        status_icon = "❌"
                        status_style = self.style.ERROR

                    formatted_name = test_name.replace("_", " ").title()
                    self.stdout.write(status_style(f"{status_icon} {formatted_name}: {result.message}"))

                    # Display detailed data if verbose or on failure
                    if verbose or not result.success:
                        if result.data:
                            for key, value in result.data.items():
                                self.stdout.write(f"   - {key}: {value}")

                        if result.error:
                            self.stdout.write(self.style.ERROR(f"   Error: {result.error}"))

    def _cleanup_oauth_test_data(self):
        """Clean up Google OAuth test data."""
        from django.contrib.auth import get_user_model

        from allauth.socialaccount.models import SocialAccount

        User = get_user_model()

        try:
            # Remove OAuth test users
            test_emails = ["oauth.testuser@gmail.com", "oauth.test@gmail.com"]

            for email in test_emails:
                User.objects.filter(email=email).delete()

            # Clean up test social accounts
            SocialAccount.objects.filter(uid__startswith="test_google_user").delete()

            self.stdout.write(self.style.WARNING("🧹 Cleaned up Google OAuth test data"))

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Cleanup warning: {str(e)}"))
