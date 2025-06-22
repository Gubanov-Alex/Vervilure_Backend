import logging

from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from src.core.testing.email_testing import EmailTester, create_email_tester

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Django management command for comprehensive email testing.

    Usage:
        python manage.py test_email
        python manage.py test_email --email admin@vervilure.com
        python manage.py test_email --comprehensive
        python manage.py test_email --mailpit-only
    """

    help = "Test email functionality with comprehensive checks"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--email",
            type=str,
            default="test@vervilure.local",
            help="Email address to send test emails to (default: test@vervilure.local)",
        )

        parser.add_argument(
            "--comprehensive", action="store_true", help="Run all email tests including user verification"
        )

        parser.add_argument("--mailpit-only", action="store_true", help="Only test Mailpit connection")

        parser.add_argument(
            "--template",
            type=str,
            default="test_email",
            help="Template name to use for test email (default: test_email)",
        )

        parser.add_argument("--site-name", type=str, help="Override site name in email")

    def handle(self, *args, **options):
        """Execute the email testing command."""
        self.style = no_style()

        # Extract options
        email = options["email"]
        comprehensive = options["comprehensive"]
        mailpit_only = options["mailpit_only"]
        template = options["template"]
        site_name = options["site_name"]

        # Create EmailTester instance
        try:
            email_tester = create_email_tester(site_name=site_name)
            self.stdout.write(self.style.SUCCESS(f"📧 Starting email tests for {email}..."))

            if mailpit_only:
                self._test_mailpit_only(email_tester)
            elif comprehensive:
                self._run_comprehensive_test(email_tester, email)
            else:
                self._run_basic_test(email_tester, email, template)

        except Exception as e:
            logger.error(f"Email test command failed: {e}", exc_info=True)
            raise CommandError(f"Email testing failed: {str(e)}")

    def _test_mailpit_only(self, email_tester: EmailTester) -> None:
        """Test only Mailpit connectivity."""
        self.stdout.write("🔍 Testing Mailpit connection...")

        result = email_tester.test_mailpit_connection()

        if result.success:
            self.stdout.write(self.style.SUCCESS(f"✅ {result.message}"))
            if result.details:
                self.stdout.write(f"   Details: {result.details}")
        else:
            self.stdout.write(self.style.ERROR(f"❌ {result.message}"))
            if result.error:
                self.stdout.write(f"   Error: {result.error}")

    def _run_basic_test(self, email_tester: EmailTester, email: str, template: str) -> None:
        """Run basic email test."""
        self.stdout.write(f"📤 Sending test email to {email}...")

        result = email_tester.send_test_email(to_email=email, template_name=template)

        if result.success:
            self.stdout.write(self.style.SUCCESS(f"✅ {result.message}"))
            if result.details:
                template_used = result.details.get("template_used", "unknown")
                self.stdout.write(f"   Template: {template_used}")
        else:
            self.stdout.write(self.style.ERROR(f"❌ {result.message}"))
            if result.error:
                self.stdout.write(f"   Error: {result.error}")

        # Also test Mailpit connection
        self.stdout.write("\n🔍 Testing Mailpit connection...")
        mailpit_result = email_tester.test_mailpit_connection()

        if mailpit_result.success:
            self.stdout.write(self.style.SUCCESS("✅ Mailpit connection successful"))
            self.stdout.write(self.style.HTTP_INFO("📧 Check emails at: http://localhost:8025"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️  {mailpit_result.message}"))

    def _run_comprehensive_test(self, email_tester: EmailTester, email: str) -> None:
        """Run comprehensive email testing."""
        self.stdout.write("🔄 Running comprehensive email tests...\n")

        results = email_tester.comprehensive_test(email)

        # Display results
        self._display_test_results(results)

        # Summary
        if results["overall_success"]:
            self.stdout.write(self.style.SUCCESS(f'\n🎉 {results["summary"]}'))
            self.stdout.write(self.style.HTTP_INFO("📧 Check all emails at: http://localhost:8025"))
        else:
            self.stdout.write(self.style.ERROR(f'\n❌ {results["summary"]}'))

            failed_tests = results.get("failed_tests", [])
            if failed_tests:
                self.stdout.write(self.style.WARNING(f'Failed tests: {", ".join(failed_tests)}'))

    def _display_test_results(self, results: dict) -> None:
        """Display formatted test results."""

        # Configuration
        config = results.get("config", {})
        self.stdout.write("⚙️  Configuration:")
        self.stdout.write(f'   Site Name: {config.get("site_name", "Unknown")}')
        self.stdout.write(f'   Mailpit URL: {config.get("mailpit_url", "Unknown")}')
        self.stdout.write(f'   Template Path: {config.get("template_base_path", "Unknown")}\n')

        # Test results
        test_sections = [
            ("mailpit_connection", "🔍 Mailpit Connection"),
            ("test_email", "📤 Test Email"),
            ("verification_email", "🔐 Verification Email"),
        ]

        for key, title in test_sections:
            if key in results:
                result = results[key]
                self._display_single_result(title, result)

        # User creation info
        if "user_created" in results:
            user_status = "Created new user" if results["user_created"] else "Used existing user"
            self.stdout.write(f"👤 User Status: {user_status}\n")

    def _display_single_result(self, title: str, result: dict) -> None:
        """Display a single test result."""
        success = result.get("success", False)
        message = result.get("message", "No message")

        status_icon = "✅" if success else "❌"
        style_method = self.style.SUCCESS if success else self.style.ERROR

        self.stdout.write(f"{title}:")
        self.stdout.write(style_method(f"{status_icon} {message}"))

        # Show additional details
        details = result.get("details", {})
        if details and success:
            for key, value in details.items():
                if key not in ["user_id"]:  # Skip technical details
                    self.stdout.write(f"   {key}: {value}")

        # Show error details
        error = result.get("error")
        if error and not success:
            self.stdout.write(f"   Error: {error}")

        self.stdout.write("")  # Empty line for spacing


# Legacy compatibility wrapper for your existing command
class LegacyEmailTester:
    """
    Legacy wrapper to maintain backward compatibility.
    Use this if you can't update your existing management command immediately.
    """

    @staticmethod
    def send_test_email(to_email: str, template_name: str = "test_email", context: dict = None) -> dict:
        """Legacy static method wrapper."""
        email_tester = create_email_tester()
        result = email_tester.send_test_email(to_email, template_name, context)
        return result.to_dict()

    @staticmethod
    def send_verification_email(user) -> dict:
        """Legacy static method wrapper."""
        email_tester = create_email_tester()
        result = email_tester.send_verification_email(user)
        return result.to_dict()

    @staticmethod
    def test_mailpit_connection() -> dict:
        """Legacy static method wrapper."""
        email_tester = create_email_tester()
        result = email_tester.test_mailpit_connection()
        return result.to_dict()

    @staticmethod
    def comprehensive_email_test(test_email: str = "test@vervilure.local") -> dict:
        """Legacy static method wrapper."""
        email_tester = create_email_tester()
        return email_tester.comprehensive_test(test_email)
