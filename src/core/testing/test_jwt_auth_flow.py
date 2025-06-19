import logging

from django.core.management.base import BaseCommand
from django.utils import timezone
from src.core.testing.jwt_auth_tester import JWTAuthTester

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Management command for comprehensive JWT authentication flow testing."""

    help = "Run comprehensive JWT authentication flow tests"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            default="jwt.testuser@vervilure.local",
            help="Email for test user (default: jwt.testuser@vervilure.local)",
        )

        parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

        parser.add_argument("--skip-cleanup", action="store_true", help="Skip cleanup after tests")

    def handle(self, *args, **options):
        """Execute JWT authentication flow tests."""
        email = options["email"]
        verbose = options["verbose"]
        skip_cleanup = options["skip_cleanup"]

        self.stdout.write(self.style.HTTP_INFO(f"Starting JWT authentication flow tests at {timezone.now()}"))

        # Initialize tester
        tester = JWTAuthTester()

        try:
            # Run complete JWT flow test (continue on errors)
            results = tester.test_complete_jwt_flow(email=email)

            # Display results
            self._display_results(results, verbose)

            # Count failures
            failures = sum(1 for result in results.values() if not result.success)
            total_tests = len(results)

            if failures == 0:
                self.stdout.write(self.style.SUCCESS(f"✅ All {total_tests} JWT tests passed!"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ {failures}/{total_tests} JWT tests failed"))

                # Show critical errors
                critical_errors = [
                    name for name, result in results.items() if not result.success and "critical" in name.lower()
                ]
                if critical_errors:
                    self.stdout.write(self.style.ERROR(f"Critical failures: {', '.join(critical_errors)}"))

            # Cleanup
            if not skip_cleanup:
                self._cleanup_test_data(email)

        except Exception as e:
            logger.exception("JWT flow test command failed")
            self.stdout.write(self.style.ERROR(f"Critical error: {str(e)}"))
            raise

    def _display_results(self, results: dict, verbose: bool = False):
        """Display test results in a formatted way."""
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.HTTP_INFO("JWT AUTHENTICATION FLOW TEST RESULTS"))
        self.stdout.write("=" * 60)

        for test_name, result in results.items():
            if result.success:
                status_icon = "✅"
                status_style = self.style.SUCCESS
            else:
                status_icon = "❌"
                status_style = self.style.ERROR

            # Format test name
            formatted_name = test_name.replace("_", " ").title()

            self.stdout.write(status_style(f"{status_icon} {formatted_name}: {result.message}"))

            # Display detailed data if verbose or on failure
            if verbose or not result.success:
                if result.data:
                    for key, value in result.data.items():
                        self.stdout.write(f"   - {key}: {value}")

                if result.error:
                    self.stdout.write(self.style.ERROR(f"   Error: {result.error}"))

    def _cleanup_test_data(self, email: str):
        """Clean up test data after testing."""
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

        User = get_user_model()

        try:
            # Remove test user
            User.objects.filter(email=email).delete()

            # Clean up blacklisted tokens (optional)
            BlacklistedToken.objects.filter(token__user__email=email).delete()

            self.stdout.write(self.style.WARNING(f"🧹 Cleaned up test data for {email}"))

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Cleanup warning: {str(e)}"))
