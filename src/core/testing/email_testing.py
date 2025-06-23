import asyncio
import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Protocol

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils import timezone
from django.utils.html import strip_tags

import requests

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class EmailTestResult:
    """Result container for email test operations."""

    success: bool
    message: str
    details: Dict[str, Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class EmailConfig:
    """Email testing configuration."""

    site_name: str = "Vervilure"
    mailpit_url: str = "http://localhost:8025/api/v1/info"
    timeout: int = 5
    template_base_path: str = "emails"

    @classmethod
    def from_settings(cls) -> "EmailConfig":
        return cls(
            site_name=getattr(settings, "SITE_NAME", cls.site_name),
            mailpit_url=getattr(settings, "MAILPIT_URL", cls.mailpit_url),
            timeout=getattr(settings, "EMAIL_TIMEOUT", cls.timeout),
        )


class EmailServiceProtocol(Protocol):
    """Protocol for email service implementations."""

    def send_email(self, message: EmailMultiAlternatives) -> bool: ...


class DjangoEmailService:
    """Production email service using Django's email backend."""

    def send_email(self, message: EmailMultiAlternatives) -> bool:
        try:
            result = message.send(fail_silently=False)
            return result > 0
        except Exception as e:
            logger.error(f"Email send failed: {e}", exc_info=True)
            return False


class EmailTemplateRenderer:
    """Handles email template rendering with fallbacks."""

    def __init__(self, base_path: str = "emails"):
        self.base_path = base_path

    def render_email(self, template_name: str, context: Dict[str, Any]) -> tuple[str, str]:
        """
        Render email template to HTML and text.

        Returns:
            Tuple of (html_content, text_content)
        """
        # Ensure context contains only simple types that templates can handle
        safe_context = self._sanitize_context(context)

        try:
            template_path = f"{self.base_path}/{template_name}.html"
            template = get_template(template_path)
            html_content = template.render(safe_context)
            text_content = strip_tags(html_content)
            return html_content, text_content
        except TemplateDoesNotExist:
            logger.warning(f"Template {template_name} not found, using fallback")
            return self._render_fallback(safe_context)
        except Exception as e:
            logger.error(f"Template rendering error: {e}", exc_info=True)
            return self._render_fallback(safe_context)

    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure context only contains template-safe values."""
        safe_context = {}
        for key, value in context.items():
            # Convert complex objects to strings or simple types
            if isinstance(value, (str, int, float, bool)):
                safe_context[key] = value
            elif isinstance(value, dict):
                # Flatten dict to avoid nested access issues
                for sub_key, sub_value in value.items():
                    safe_key = f"{key}_{sub_key}"
                    if isinstance(sub_value, (str, int, float, bool)):
                        safe_context[safe_key] = sub_value
                    else:
                        safe_context[safe_key] = str(sub_value)
            elif hasattr(value, "__dict__"):
                # Convert objects to string representation
                safe_context[key] = str(value)
            else:
                safe_context[key] = str(value)

        return safe_context

    def _render_fallback(self, context: Dict[str, Any]) -> tuple[str, str]:
        """Generate fallback email content when template is missing."""
        site_name = context.get("site_name", "Test Site")
        test_message = context.get("test_message", "This is a test email.")
        timestamp = context.get("timestamp", timezone.now().strftime("%Y-%m-%d %H:%M:%S"))

        fallback_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Test Email</title></head>
        <body>
            <h1>{site_name}</h1>
            <p>{test_message}</p>
            <p><strong>Timestamp:</strong> {timestamp}</p>
            <hr>
            <p><em>This is a fallback template.</em></p>
        </body>
        </html>
        """
        return fallback_html, strip_tags(fallback_html)


class MailpitHealthChecker:
    """Handles Mailpit connectivity checks."""

    def __init__(self, config: EmailConfig):
        self.config = config

    def check_connection(self) -> EmailTestResult:
        """Test connection to Mailpit service."""
        try:
            response = requests.get(self.config.mailpit_url, timeout=self.config.timeout)

            if response.status_code == 200:
                return EmailTestResult(
                    success=True, message="Mailpit connection successful", details={"mailpit_info": response.json()}
                )
            else:
                return EmailTestResult(
                    success=False,
                    message=f"Mailpit returned status {response.status_code}",
                    error=f"HTTP {response.status_code}",
                )

        except requests.RequestException as e:
            return EmailTestResult(success=False, message=f"Cannot connect to Mailpit: {str(e)}", error=str(e))


class EmailTester:
    """
    Production-ready email testing utility with proper separation of concerns.

    Features:
    - Template rendering with fallbacks
    - Proper error handling and logging
    - Service abstraction for testability
    - Comprehensive health checks
    """

    def __init__(
        self,
        config: Optional[EmailConfig] = None,
        email_service: Optional[EmailServiceProtocol] = None,
        template_renderer: Optional[EmailTemplateRenderer] = None,
    ):
        self.config = config or EmailConfig.from_settings()
        self.email_service = email_service or DjangoEmailService()
        self.template_renderer = template_renderer or EmailTemplateRenderer(self.config.template_base_path)
        self.mailpit_checker = MailpitHealthChecker(self.config)

    def send_test_email(
        self, to_email: str, template_name: str = "test_email", context: Optional[Dict[str, Any]] = None
    ) -> EmailTestResult:
        """
        Send a test email to verify email integration.

        Args:
            to_email: Recipient email address
            template_name: Template name without .html extension
            context: Additional context for template rendering

        Returns:
            EmailTestResult with operation details
        """
        try:
            # Prepare context with defaults - ensure all values are template-safe
            email_context = {
                "site_name": str(self.config.site_name),
                "test_message": "This is a test email from Vervilure development environment!",
                "timestamp": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                "recipient": str(to_email),
            }

            # Safely merge additional context
            if context:
                for key, value in context.items():
                    # Ensure values are template-safe strings
                    email_context[key] = str(value) if not isinstance(value, (str, int, float, bool)) else value

            # Render email content
            html_content, text_content = self.template_renderer.render_email(template_name, email_context)

            # Create email message
            subject = f'[{self.config.site_name}] Email Test - {email_context["timestamp"]}'

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
                to=[to_email],
            )
            email.attach_alternative(html_content, "text/html")

            # Send email
            if self.email_service.send_email(email):
                success_msg = f"Test email sent successfully to {to_email}"
                logger.info(success_msg)

                return EmailTestResult(
                    success=True,
                    message=success_msg,
                    details={
                        "template_used": f"{self.config.template_base_path}/{template_name}.html",
                        "recipient": to_email,
                        "email_subject": subject,
                    },
                )
            else:
                raise Exception("Email service returned failure")

        except Exception as e:
            error_msg = f"Failed to send test email to {to_email}: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return EmailTestResult(success=False, message=error_msg, error=str(e), details={"recipient": to_email})

    def send_verification_email(self, user: User) -> EmailTestResult:
        """
        Send email verification for testing django-allauth integration.

        Args:
            user: User instance

        Returns:
            EmailTestResult with operation details
        """
        try:
            from django.test import RequestFactory

            from allauth.account.utils import send_email_confirmation

            # Create proper request object using RequestFactory
            factory = RequestFactory()
            request = factory.get("/")
            request.user = user  # Add user to request

            # Set site information properly
            try:
                current_site = Site.objects.get_current()
                request.META["HTTP_HOST"] = current_site.domain
            except Exception:
                request.META["HTTP_HOST"] = "localhost:8000"

            request.META["wsgi.url_scheme"] = "http"

            # Send verification email
            send_email_confirmation(request, user)

            success_msg = f"Verification email sent to {user.email}"
            logger.info(success_msg)

            return EmailTestResult(
                success=True,
                message=success_msg,
                details={
                    "user_email": user.email,
                    "user_id": user.id,
                    "user_name": f"{user.first_name} {user.last_name}".strip(),
                },
            )

        except Exception as e:
            error_msg = f"Failed to send verification email: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return EmailTestResult(
                success=False,
                message=error_msg,
                error=str(e),
                details={"user_email": getattr(user, "email", "unknown")},
            )

    def test_mailpit_connection(self) -> EmailTestResult:
        """Test connection to Mailpit service."""
        return self.mailpit_checker.check_connection()

    def comprehensive_test(self, test_email: str = "test@vervilure.local") -> Dict[str, Any]:
        """
        Run comprehensive email system test.

        Args:
            test_email: Email address for testing

        Returns:
            Complete test results dictionary
        """
        results = {
            "config": asdict(self.config),
            "mailpit_connection": self.test_mailpit_connection().to_dict(),
            "test_email": self.send_test_email(test_email).to_dict(),
        }

        # Test user creation and verification email
        try:
            user, created = User.objects.get_or_create(
                email=test_email,
                defaults={
                    "first_name": "Test",
                    "last_name": "User",
                    "is_active": True,
                    "username": test_email.split("@")[0],  # Generate username from email
                },
            )

            results["user_created"] = created
            results["verification_email"] = self.send_verification_email(user).to_dict()

        except Exception as e:
            results["verification_email"] = EmailTestResult(
                success=False, message=f"User creation/verification failed: {str(e)}", error=str(e)
            ).to_dict()

        # Calculate overall success
        test_results = [results["mailpit_connection"], results["test_email"], results["verification_email"]]

        all_success = all(result.get("success", False) for result in test_results)

        results["overall_success"] = all_success
        results["summary"] = "All email tests passed! ✅" if all_success else "Some email tests failed ❌"

        results["failed_tests"] = [
            key for key, result in results.items() if isinstance(result, dict) and not result.get("success", True)
        ]

        return results


# Factory function for easy instantiation
def create_email_tester(site_name: Optional[str] = None, mailpit_url: Optional[str] = None) -> EmailTester:
    """Factory function to create EmailTester with custom config."""
    config = EmailConfig.from_settings()

    if site_name:
        config.site_name = site_name
    if mailpit_url:
        config.mailpit_url = mailpit_url

    return EmailTester(config=config)


# Async version for high-performance scenarios
class AsyncEmailTester:
    """Async version of EmailTester for concurrent operations."""

    def __init__(self, email_tester: EmailTester):
        self.email_tester = email_tester

    async def send_test_email_async(
        self, to_email: str, template_name: str = "test_email", context: Optional[Dict[str, Any]] = None
    ) -> EmailTestResult:
        """Async wrapper for send_test_email."""
        return await asyncio.to_thread(self.email_tester.send_test_email, to_email, template_name, context)

    async def comprehensive_test_async(self, test_emails: list[str]) -> Dict[str, Any]:
        """Run comprehensive tests for multiple emails concurrently."""
        tasks = [self.send_test_email_async(email) for email in test_emails]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "concurrent_tests": len(test_emails),
            "results": [
                result.to_dict() if isinstance(result, EmailTestResult) else {"success": False, "error": str(result)}
                for result in results
            ],
            "success_rate": sum(1 for result in results if isinstance(result, EmailTestResult) and result.success)
            / len(results),
        }
