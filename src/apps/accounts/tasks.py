import logging
from typing import Optional

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import close_old_connections
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.html import strip_tags

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_verification_email(self, user_id: int, email: Optional[str] = None) -> Optional[str]:
    """Send email verification with backend verification URL."""
    try:
        user = User.objects.filter(Q(id=user_id) if user_id else Q(email=email)).first()

        if not user:
            logger.error(f"User not found: ID={user_id}, email={email}")
            return None

        if not hasattr(user, "is_email_verified"):
            logger.error(f"User {user.email} missing is_email_verified attribute")
            return None

        if user.is_email_verified:
            logger.info(f"User {user.email} already verified")
            return "User already verified"

        # Generate fresh token
        user.regenerate_verification_token()

        verification_url = f"{settings.BACKEND_URL}/verify-email/" f"{user.email_verification_token}/"

        context = {
            "user": user,
            "verification_url": verification_url,
            "site_name": "Vervilure",
            "token_expires_hours": 24,
            "subject": "Verify your email address",
        }

        logger.debug(f"Email context: {context}")
        html_message = render_to_string("accounts/emails/verification_email.html", context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject="Verify your Vervilure account",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(
            f"Verification email sent: {user.email}",
            extra={
                "user_id": user.id,
                "verification_url": verification_url,
                "token_id": str(user.email_verification_token)[:8] + "...",
            },
        )
        return f"Verification email sent to {user.email}"

    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return None
    except Exception as exc:
        logger.error(f"Failed to send verification email: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self, user_id: int, reset_token: str) -> Optional[str]:
    """
    Send password reset email to user.

    Args:
        user_id: User ID
        reset_token: Password reset token

    Returns:
        Success message or None if failed
    """
    try:
        user = User.objects.get(id=user_id)

        # Generate reset URL
        reset_url = f"{settings.FRONTEND_URL}/reset-password/" f"{reset_token}/"

        context = {
            "user": user,
            "reset_url": reset_url,
            "site_name": "Vervilure",
            "subject": "Reset your password",
        }

        html_message = render_to_string("accounts/emails/password_reset_email.html", context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject="Reset your Vervilure password",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Password reset email sent to {user.email}")
        return f"Password reset email sent to {user.email}"

    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return None

    except Exception as exc:
        logger.error(f"Failed to send password reset email: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task
def cleanup_expired_tokens() -> str:
    """
    Clean up expired blacklisted tokens from database.

    Should be run periodically via cron.
    """
    from django.utils import timezone

    from .models import BlacklistedToken

    expired_count = BlacklistedToken.objects.filter(expires_at__lt=timezone.now()).count()

    BlacklistedToken.objects.filter(expires_at__lt=timezone.now()).delete()

    logger.info(f"Cleaned up {expired_count} expired tokens")
    return f"Cleaned up {expired_count} expired tokens"
