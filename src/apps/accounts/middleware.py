from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import BlacklistedToken


class JWTBlacklistMiddleware(MiddlewareMixin):
    """
    Middleware to check if JWT token is blacklisted.

    Automatically rejects requests with blacklisted tokens.
    """

    def process_request(self, request):
        """Check if JWT token is blacklisted before processing request."""
        # Skip check for non-API requests
        if not request.path.startswith("/api/"):
            return None

        # Skip blacklist check for logout and auth endpoints
        skip_paths = [
            "/logout/",
            "/auth/logout",
            "/auth/jwt/",
            "/auth/jwt/refresh/",
        ]

        if any(skip_path in request.path for skip_path in skip_paths):
            return None

        # Get JWT token from request
        jwt_auth = JWTAuthentication()

        try:
            # Extract token from request
            raw_token = jwt_auth.get_raw_token(jwt_auth.get_header(request))
            if raw_token is None:
                return None

            # Validate token format
            validated_token = jwt_auth.get_validated_token(raw_token)
            jti = validated_token.get("jti")

            # Check if token is blacklisted
            if jti and BlacklistedToken.objects.filter(token_jti=jti).exists():
                return JsonResponse({"error": "Token has been blacklisted."}, status=401)

        except (InvalidToken, TokenError):
            # Token validation will be handled by DRF authentication
            pass

        return None


class IPTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track user IP addresses for security purposes.
    """

    def process_request(self, request):
        """Track user IP address in request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")

        request.user_ip = ip
        return None
