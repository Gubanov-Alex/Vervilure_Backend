import logging
from typing import Optional

from django.conf import settings
from rest_framework.request import Request
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class BaseRobustThrottle:
    """Base mixin for robust throttling with error handling."""

    def get_rate(self) -> Optional[str]:
        """
        Get throttle rate with robust error handling.

        Returns None if throttling is disabled or rate not configured.
        """
        if not getattr(self, "scope", None):
            logger.debug(f"No scope defined for {self.__class__.__name__}")
            return None

        try:
            # Check if REST_FRAMEWORK settings exist
            rest_framework_settings = getattr(settings, "REST_FRAMEWORK", {})
            throttle_rates = rest_framework_settings.get("DEFAULT_THROTTLE_RATES", {})

            # Return None if throttling is disabled (empty dict)
            if not throttle_rates:
                logger.debug(f"Throttling disabled - no rates configured")
                return None

            # Get rate for this scope
            rate = throttle_rates.get(self.scope)
            if not rate:
                logger.debug(f"No rate configured for scope '{self.scope}'")
                return None

            return rate

        except Exception as e:
            logger.warning(f"Error getting throttle rate for scope '{self.scope}': {str(e)}")
            return None

    def allow_request(self, request: Request, view: APIView) -> bool:
        """
        Override allow_request to handle missing rates gracefully.
        """
        # If no rate is configured, allow all requests
        if self.get_rate() is None:
            return True

        # Use parent implementation if rate is configured
        try:
            return super().allow_request(request, view)
        except Exception as e:
            logger.error(f"Throttle error for {self.__class__.__name__}: {str(e)}")
            # Allow request on error to prevent blocking legitimate users
            return True


class LoginRateThrottle(BaseRobustThrottle, AnonRateThrottle):
    """
    Rate throttle for login attempts with robust error handling.

    Limits login attempts to prevent brute force attacks.
    Falls back gracefully when throttling is disabled.
    """

    scope = "login"

    def allow_request(self, request: Request, view: APIView) -> bool:
        """Check if login request should be allowed."""
        # Log throttle attempt for debugging
        logger.debug(f"Login throttle check for IP: {self.get_ident(request)}")
        return super().allow_request(request, view)


class RegistrationRateThrottle(BaseRobustThrottle, AnonRateThrottle):
    """
    Rate throttle for registration attempts with robust error handling.

    Limits registration attempts to prevent spam.
    Falls back gracefully when throttling is disabled.
    """

    scope = "registration"

    def allow_request(self, request: Request, view: APIView) -> bool:
        """Check if registration request should be allowed."""
        # Log throttle attempt for debugging
        logger.debug(f"Registration throttle check for IP: {self.get_ident(request)}")
        return super().allow_request(request, view)


class PasswordChangeRateThrottle(BaseRobustThrottle, UserRateThrottle):
    """
    Rate throttle for password change attempts with robust error handling.

    Limits password changes to prevent abuse.
    Falls back gracefully when throttling is disabled.
    """

    scope = "password_change"

    def allow_request(self, request: Request, view: APIView) -> bool:
        """Check if password change request should be allowed."""
        # Log throttle attempt for debugging
        logger.debug(f"Password change throttle check for user: {getattr(request.user, 'id', 'anonymous')}")
        return super().allow_request(request, view)


class PasswordResetRateThrottle(BaseRobustThrottle, AnonRateThrottle):
    """
    Rate throttle for password reset attempts with robust error handling.

    Limits password reset requests to prevent abuse.
    Falls back gracefully when throttling is disabled.
    """

    scope = "password_reset"

    def allow_request(self, request: Request, view: APIView) -> bool:
        """Check if password reset request should be allowed."""
        # Log throttle attempt for debugging
        logger.debug(f"Password reset throttle check for IP: {self.get_ident(request)}")
        return super().allow_request(request, view)


# Utility function for checking throttle configuration
def is_throttling_enabled() -> bool:
    """
    Check if throttling is enabled in Django settings.

    Returns:
        bool: True if throttling is configured, False otherwise
    """
    try:
        rest_framework_settings = getattr(settings, "REST_FRAMEWORK", {})
        throttle_rates = rest_framework_settings.get("DEFAULT_THROTTLE_RATES", {})
        return bool(throttle_rates)
    except Exception:
        return False


def get_throttle_rate(scope: str) -> Optional[str]:
    """
    Get throttle rate for a specific scope.

    Args:
        scope: The throttle scope name

    Returns:
        str or None: The throttle rate string or None if not configured
    """
    try:
        rest_framework_settings = getattr(settings, "REST_FRAMEWORK", {})
        throttle_rates = rest_framework_settings.get("DEFAULT_THROTTLE_RATES", {})
        return throttle_rates.get(scope)
    except Exception:
        return None
