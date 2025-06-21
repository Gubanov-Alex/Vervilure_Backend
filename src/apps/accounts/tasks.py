import logging
from typing import Optional

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import close_old_connections
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.html import strip_tags

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_verification_email(self, user_id: int, email: Optional[str] = None) -> Optional[str]:
    """
    Send email verification with backend verification URL.

    Improved with:
    - Better retry logic for transient DB issues
    - Connection management
    - More detailed logging
    """
    # Ensure clean DB connections
    close_old_connections()

    try:
        # Add retry for transient DB issues
        user = None
        attempt = 0
        max_db_attempts = 3

        while attempt < max_db_attempts and not user:
            try:
                user = User.objects.filter(
                    Q(id=user_id) if user_id else Q(email=email)
                ).first()

                if not user and attempt < max_db_attempts - 1:
                    # Wait a bit before retry
                    import time
                    time.sleep(0.5 * (attempt + 1))
                    logger.warning(
                        f"User not found on attempt {attempt + 1}, retrying...",
                        extra={"user_id": user_id, "email": email}
                    )

                attempt += 1

            except Exception as db_error:
                logger.error(
                    f"Database error on attempt {attempt}: {db_error}",
                    extra={"user_id": user_id, "email": email}
                )
                if attempt >= max_db_attempts:
                    raise

        if not user:
            # This is a real issue - user doesn't exist after retries
            logger.error(
                f"User not found after {max_db_attempts} attempts: ID={user_id}, email={email}"
            )
            # Don't retry this - it's not a transient issue
            return None

        if not hasattr(user, "is_email_verified"):
            logger.error(f"User {user.email} missing is_email_verified attribute")
            return None

        if user.is_email_verified:
            logger.info(f"User {user.email} already verified")
            return "User already verified"

        # Generate fresh token
        user.regenerate_verification_token()

        verification_url = (
            f"{settings.BACKEND_URL}/verify-email/"
            f"{user.email_verification_token}/"
        )

        context = {
            "user": user,
            "verification_url": verification_url,
            "site_name": "Vervilure",
            "token_expires_hours": 24,
            "subject": "Verify your email address",
        }

        logger.debug(f"Email context prepared for: {user.email}")
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
        logger.error(f"User with ID {user_id} not found in database")
        return None

    except Exception as exc:
        logger.error(
            f"Failed to send verification email: {exc}",
            extra={"user_id": user_id, "email": email},
            exc_info=True
        )

        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)

        try:
            raise self.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            logger.error(
                f"Max retries exceeded for verification email",
                extra={"user_id": user_id, "email": email}
            )
            return None


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_password_reset_email(self, user_id: int, reset_token: str) -> Optional[str]:
    """
    Send password reset email to user.

    Args:
        user_id: User ID
        reset_token: Password reset token

    Returns:
        Success message or None if failed
    """
    # Ensure clean DB connections
    close_old_connections()

    try:
        user = User.objects.get(id=user_id)

        # Generate reset URL
        reset_url = (
            f"{settings.FRONTEND_URL}/reset-password/"
            f"{reset_token}/"
        )

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
        logger.error(
            f"Failed to send password reset email: {exc}",
            extra={"user_id": user_id},
            exc_info=True
        )

        countdown = 60 * (2 ** self.request.retries)

        try:
            raise self.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            logger.error(
                f"Max retries exceeded for password reset email",
                extra={"user_id": user_id}
            )
            return None


@shared_task
def cleanup_expired_tokens() -> str:
    """
    Clean up expired blacklisted tokens from database.

    Should be run periodically via cron.
    """
    from django.utils import timezone
    from .models import BlacklistedToken

    # Ensure clean DB connections
    close_old_connections()

    expired_count = BlacklistedToken.objects.filter(
        expires_at__lt=timezone.now()
    ).count()

    BlacklistedToken.objects.filter(expires_at__lt=timezone.now()).delete()

    logger.info(f"Cleaned up {expired_count} expired tokens")
    return f"Cleaned up {expired_count} expired tokens"
