from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Rate throttle for login attempts.

    Limits login attempts to prevent brute force attacks.
    """

    scope = "login"


class RegistrationRateThrottle(AnonRateThrottle):
    """
    Rate throttle for registration attempts.

    Limits registration attempts to prevent spam.
    """

    scope = "registration"


class PasswordChangeRateThrottle(UserRateThrottle):
    """
    Rate throttle for password change attempts.

    Limits password changes to prevent abuse.
    """

    scope = "password_change"


class PasswordResetRateThrottle(AnonRateThrottle):
    """
    Rate throttle for password reset attempts.

    Limits password reset requests to prevent abuse.
    """

    scope = "password_reset"
