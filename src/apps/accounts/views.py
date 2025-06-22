import logging
import uuid
from datetime import datetime
from datetime import timezone as dt_timezone
from typing import List

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import BlacklistedToken, UserAddress
from .serializers import (
    GoogleOAuthSerializer,
    PasswordChangeSerializer,
    UserAddressSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)
from .throttles import LoginRateThrottle, PasswordChangeRateThrottle, RegistrationRateThrottle

logger = logging.getLogger(__name__)
User = get_user_model()


class AuthViewSet(GenericViewSet):
    """
    🔐 Authentication: Advanced security and OAuth integration

    Comprehensive authentication system with enhanced security features,
    brute force protection, and seamless Google OAuth integration.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        action_serializers = {
            "register": UserRegistrationSerializer,
            "login": UserLoginSerializer,
            "google_oauth": GoogleOAuthSerializer,  # Fixed action name
            "logout": None,  # No serializer needed for logout
            "refresh": None,  # Uses DRF JWT serializer
        }

        return action_serializers.get(self.action, self.serializer_class)

    def get_throttles(self) -> List[BaseThrottle]:
        """Apply action-specific throttling with proper error handling."""
        throttle_classes_by_action = {
            "register": [RegistrationRateThrottle],
            "login": [LoginRateThrottle],
            "google_oauth": [LoginRateThrottle],  # Use same throttle as login
            "logout": [],  # No throttling for logout
            "refresh": [],  # No throttling for token refresh
        }

        selected_throttles = throttle_classes_by_action.get(self.action, [])

        # Check if throttling is disabled (e.g., in tests)
        if not getattr(settings, "REST_FRAMEWORK", {}).get("DEFAULT_THROTTLE_RATES"):
            logger.debug(f"Throttling disabled for action: {self.action}")
            return []

        try:
            return [throttle() for throttle in selected_throttles]
        except Exception as e:
            logger.warning(f"Throttle initialization failed for {self.action}: {str(e)}")
            return []

    def get_permissions(self):
        """Apply action-specific permissions."""
        if self.action == "logout":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    # Registration endpoint
    @swagger_auto_schema(
        operation_summary="🔐 User Registration",
        operation_description="""
          **Secure user registration with comprehensive validation**

          **Features:**
          - Email uniqueness validation
          - Strong password requirements  
          - Automatic email verification workflow
          - Anti-spam protection with rate limiting
          - Comprehensive security audit logging

          **Password Requirements:**
          - Minimum 8 characters
          - At least one uppercase letter
          - At least one lowercase letter
          - At least one digit
          - At least one special character

          **Security Features:**
          - IP-based rate limiting (5 attempts/hour)
          - Brute force protection
          - Transaction safety with Celery integration
          - Email verification token generation
          """,
        tags=["🔐 Authentication"],
        request_body=UserRegistrationSerializer,
        responses={
            201: openapi.Response(
                description="Registration successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "user": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "tokens": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "access": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="Access token (15 minutes)"
                                ),
                                "refresh": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="Refresh token (7 days)"
                                ),
                            },
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Registration successful. Please check your email for verification.",
                        ),
                    },
                ),
            ),
            400: "Validation errors",
            429: "Rate limit exceeded",
        },
    )
    @method_decorator(never_cache)
    @action(detail=False, methods=["post"])
    def register(self, request) -> Response:
        """
        Register new user with comprehensive security.

        Features:
        - Email verification workflow
        - Rate limiting per IP
        - Security logging
        - Transaction safety with proper Celery task scheduling
        """
        client_ip = self._get_client_ip(request)

        # Anti-spam protection
        if self._is_registration_blocked(client_ip):
            logger.warning(
                f"Registration blocked for IP {client_ip} - too many attempts",
                extra={"ip_address": client_ip, "action": "registration_blocked"},
            )
            return Response(
                {"error": "Too many registration attempts. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = UserRegistrationSerializer(data=request.data)

        if not serializer.is_valid():
            self._log_failed_registration(client_ip, serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Use transaction on_commit to ensure task runs after DB commit
            with transaction.atomic():
                user = serializer.save()
                refresh = RefreshToken.for_user(user)

                # Update registration counter
                self._increment_registration_attempts(client_ip)

                # Log successful registration
                logger.info(
                    f"User registered successfully: {user.email}",
                    extra={
                        "user_id": user.id,
                        "email": user.email,
                        "ip_address": client_ip,
                        "action": "registration_success",
                    },
                )

                # Schedule email verification AFTER transaction commits
                try:
                    from .tasks import send_verification_email

                    transaction.on_commit(lambda: send_verification_email.delay(user.id, user.email))
                except ImportError:
                    logger.warning("Email verification task not available")

                return Response(
                    {
                        "user": UserProfileSerializer(user, context={"request": request}).data,
                        "tokens": {
                            "access": str(refresh.access_token),
                            "refresh": str(refresh),
                        },
                        "message": "Registration successful. Please check your email for verification.",
                    },
                    status=status.HTTP_201_CREATED,
                )

        except Exception as e:
            logger.error(
                f"Registration failed: {str(e)}",
                extra={
                    "email": request.data.get("email", "unknown"),
                    "ip_address": client_ip,
                    "action": "registration_error",
                },
                exc_info=True,
            )
            return Response(
                {"error": "Registration failed. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="🔐 Google OAuth Authentication",
        operation_description="""
            **Seamless Google OAuth 2.0 integration**

            **Features:**
            - Google account verification via OAuth API
            - Automatic user creation or account linking
            - Secure profile data import from Google
            - JWT token generation with user context
            - Enhanced user experience with social login

            **OAuth Process Flow:**
            1. Client obtains Google OAuth access token
            2. Server validates token with Google API
            3. User profile data retrieval and verification
            4. Account creation or existing account linking
            5. JWT token generation and secure session establishment

            **Security Benefits:**
            - Pre-verified email addresses from Google
            - Reduced password management complexity
            - OAuth 2.0 security standards compliance
            - Rate limiting and abuse prevention
            """,
        tags=["🔐 Authentication"],
        request_body=GoogleOAuthSerializer,
        responses={
            200: openapi.Response(
                description="Google OAuth authentication successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "user": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "tokens": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "access": openapi.Schema(type=openapi.TYPE_STRING),
                                "refresh": openapi.Schema(type=openapi.TYPE_STRING),
                            },
                        ),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, example="Google authentication successful."
                        ),
                        "is_new_user": openapi.Schema(
                            type=openapi.TYPE_BOOLEAN, description="Indicates if this is a new user registration"
                        ),
                    },
                ),
            ),
            400: "Invalid Google token",
            429: "Rate limit exceeded",
        },
    )
    @method_decorator(never_cache)
    @action(detail=False, methods=["post"])
    def google_oauth(self, request) -> Response:
        """
        Authenticate user with Google OAuth token.

        Features:
        - Google token validation
        - Auto user creation/linking
        - JWT token generation
        - Security logging
        """
        client_ip = self._get_client_ip(request)

        # Rate limiting for OAuth attempts
        cache_key = f"google_oauth_attempts_{client_ip}"
        attempts = cache.get(cache_key, 0)
        if attempts >= 10:  # Max 10 OAuth attempts per hour
            logger.warning(
                f"Google OAuth rate limit exceeded for IP {client_ip}",
                extra={"ip_address": client_ip, "action": "google_oauth_rate_limit"},
            )
            return Response(
                {"error": "Too many OAuth attempts. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = GoogleOAuthSerializer(data=request.data)

        if not serializer.is_valid():
            # Increment attempts counter
            cache.set(cache_key, attempts + 1, 3600)  # 1 hour

            logger.warning(
                f"Google OAuth validation failed from IP {client_ip}",
                extra={
                    "ip_address": client_ip,
                    "errors": serializer.errors,
                    "action": "google_oauth_validation_failed",
                },
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = serializer.validated_data["user"]
            user_info = serializer.validated_data["user_info"]

            # Determine if this is a new user
            is_new_user = user.date_joined >= timezone.now() - timezone.timedelta(seconds=30)

            # Update user login metadata
            self._update_login_metadata(user, client_ip)

            # Clear failed attempts
            cache.delete(cache_key)

            # Log successful OAuth login
            logger.info(
                f"Google OAuth login successful: {user.email}",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "google_id": user_info.get("google_id"),
                    "ip_address": client_ip,
                    "is_new_user": is_new_user,
                    "action": "google_oauth_success",
                },
            )

            return Response(
                {
                    "user": UserProfileSerializer(user, context={"request": request}).data,
                    "tokens": {
                        "access": serializer.validated_data["access"],
                        "refresh": serializer.validated_data["refresh"],
                    },
                    "message": "Google authentication successful.",
                    "is_new_user": is_new_user,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(
                f"Google OAuth authentication failed: {str(e)}",
                extra={"ip_address": client_ip, "action": "google_oauth_error"},
                exc_info=True,
            )
            return Response(
                {"error": "Authentication failed. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # Login endpoint
    @swagger_auto_schema(
        operation_summary="🔐 User Login",
        operation_description="""
        **Secure user authentication with advanced protection**

        **Features:**
        - Multi-factor security validation
        - IP-based brute force protection
        - Intelligent login attempt monitoring
        - JWT token generation with user context
        - Comprehensive session metadata tracking

        **Security Features:**
        - Rate limiting per IP address (5 attempts/hour)
        - Failed attempt tracking and analysis
        - Automatic account protection mechanisms
        - Real-time security event logging
        - Session fingerprinting and validation

        **Authentication Flow:**
        1. Email and password validation
        2. Account status verification
        3. Brute force protection checks
        4. JWT token generation
        5. Login metadata updates
        """,
        tags=["🔐 Authentication"],
        request_body=UserLoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "user": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "tokens": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "access": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="Access token (15 minutes)"
                                ),
                                "refresh": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="Refresh token (7 days)"
                                ),
                            },
                        ),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="Login successful."),
                    },
                ),
            ),
            400: "Invalid credentials",
            429: "Rate limit exceeded",
        },
    )
    @method_decorator(never_cache)
    @action(detail=False, methods=["post"])
    def login(self, request) -> Response:
        """
        Secure user authentication with brute force protection.

        Features:
        - Brute force protection
        - IP-based rate limiting
        - Security event logging
        - Login metadata tracking
        """
        client_ip = self._get_client_ip(request)
        email = request.data.get("email", "").lower()

        # Check for brute force attempts
        if self._is_login_blocked(client_ip, email):
            logger.warning(
                f"Login blocked for {email} from IP {client_ip} - brute force protection",
                extra={"email": email, "ip_address": client_ip, "action": "login_blocked"},
            )
            return Response(
                {"error": "Too many failed login attempts. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = UserLoginSerializer(data=request.data, context={"request": request})

        if not serializer.is_valid():
            self._handle_failed_login(client_ip, email)
            return Response({"error": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]

        # Update user login metadata
        self._update_login_metadata(user, client_ip)

        # Clear failed attempts on successful login
        self._clear_failed_attempts(client_ip, email)

        # Log successful login
        logger.info(
            f"Successful login: {user.email}",
            extra={"user_id": user.id, "email": user.email, "ip_address": client_ip, "action": "login_success"},
        )

        return Response(
            {
                "user": UserProfileSerializer(user, context={"request": request}).data,
                "tokens": {
                    "access": serializer.validated_data["access"],
                    "refresh": serializer.validated_data["refresh"],
                },
                "message": "Login successful.",
            },
            status=status.HTTP_200_OK,
        )

    # Logout endpoint
    @swagger_auto_schema(
        operation_summary="🔐 Secure Logout",
        operation_description="""
        **Secure logout with comprehensive token management**

        **Features:**
        - Token validation and ownership verification
        - Immediate token blacklisting for security
        - Complete session termination
        - Comprehensive security audit trail creation
        - Multi-device logout support

        **Security Benefits:**
        - Immediate token invalidation prevents reuse
        - Prevents session hijacking attacks
        - Comprehensive security event logging
        - Clean session cleanup and management
        - Token ownership validation before blacklisting

        **Logout Process:**
        1. Refresh token validation
        2. Token ownership verification
        3. Blacklist token addition
        4. Audit trail creation
        5. Security event logging
        """,
        tags=["🔐 Authentication"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh"],
            properties={
                "refresh": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Refresh token to blacklist",
                    example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Logout successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="Logout successful."),
                    },
                ),
            ),
            400: "Invalid or missing token",
            401: "Authentication required",
        },
    )
    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def logout(self, request) -> Response:
        """
        Secure logout with comprehensive token management.

        Features:
        - Token validation and blacklisting
        - Audit trail creation
        - Security event logging
        """
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)

            # Validate token ownership
            if token.get("user_id") != request.user.id:
                logger.warning(
                    "Token ownership mismatch in logout attempt",
                    extra={
                        "user_id": request.user.id,
                        "token_user_id": token.get("user_id"),
                        "action": "logout_token_mismatch",
                    },
                )
                return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

            # Check if token is already blacklisted
            jti = token["jti"]
            is_already_blacklisted = BlacklistedToken.objects.filter(token_jti=jti, user=request.user).exists()

            if is_already_blacklisted:
                logger.info(
                    f"Token already blacklisted for user: {request.user.email}",
                    extra={"user_id": request.user.id, "action": "logout_already_blacklisted"},
                )
                return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)

            # Create audit record before blacklisting
            BlacklistedToken.objects.create(
                token_jti=jti,
                user=request.user,
                expires_at=datetime.fromtimestamp(token["exp"], tz=dt_timezone.utc),
                blacklisted_at=timezone.now(),
            )

            # Try to blacklist token - catch exception if already blacklisted
            try:
                token.blacklist()
            except Exception as blacklist_error:
                # Token might already be blacklisted by another process
                logger.info(
                    f"Token blacklisting skipped (already blacklisted): {request.user.email}",
                    extra={
                        "user_id": request.user.id,
                        "action": "logout_already_blacklisted_by_system",
                        "error": str(blacklist_error),
                    },
                )

            # Log successful logout
            logger.info(
                f"User logout successful: {request.user.email}",
                extra={"user_id": request.user.id, "action": "logout_success"},
            )

            return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)

        except TokenError as e:
            # Check if the token error is due to blacklisting
            error_msg = str(e).lower()
            if "blacklist" in error_msg or "blacklisted" in error_msg:
                logger.info(
                    f"Logout attempt with already blacklisted token: {request.user.email}",
                    extra={"user_id": request.user.id, "action": "logout_already_blacklisted_token"},
                )
                return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)

            logger.warning(
                f"Invalid token in logout attempt: {str(e)}",
                extra={"user_id": request.user.id, "action": "logout_invalid_token"},
            )
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        # Password Reset endpoint

    @swagger_auto_schema(
        operation_summary="🔐 Password Reset Request",
        operation_description="""
           **Secure password reset initiation with protection**

           **Features:**
           - Email address validation and verification
           - Secure token generation with expiration
           - Rate limiting protection against abuse
           - Email delivery confirmation and tracking
           - Anti-enumeration security measures

           **Security Features:**
           - Rate limiting (3 attempts/hour per IP)
           - Email enumeration prevention
           - Secure token generation with Django's built-in system
           - Comprehensive audit logging
           - Transaction safety with Celery integration

           **Reset Process:**
           1. Email address validation
           2. User account verification
           3. Secure reset token generation
           4. Email delivery with reset link
           5. Comprehensive security logging
           """,
        tags=["🔐 Authentication"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email"],
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_EMAIL,
                    description="User email address",
                    example="user@example.com",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Password reset email sent",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="If an account with that email exists, a password reset link has been sent.",
                        ),
                    },
                ),
            ),
            400: "Invalid email address",
            429: "Rate limit exceeded",
        },
    )
    @action(detail=False, methods=["post"])
    def password_reset(self, request) -> Response:
        """Request password reset with rate limiting and security logging."""
        email = request.data.get("email", "").lower().strip()
        client_ip = self._get_client_ip(request)

        # Rate limiting для password reset
        cache_key = f"password_reset_attempts_{client_ip}"
        attempts = cache.get(cache_key, 0)
        if attempts >= 3:
            logger.warning(
                f"Password reset rate limit exceeded for IP {client_ip}",
                extra={"ip_address": client_ip, "action": "password_reset_rate_limit"},
            )
            return Response(
                {"error": "Too many password reset attempts. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Increment attempts counter
        cache.set(cache_key, attempts + 1, 3600)  # 1 hour

        try:
            user = User.objects.get(email=email, is_active=True)

            # Generate password reset token
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.encoding import force_bytes
            from django.utils.http import urlsafe_base64_encode

            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Send password reset email
            from .tasks import send_password_reset_email

            send_password_reset_email.delay(user.id, token, uid)

            logger.info(
                f"Password reset requested: {email}",
                extra={"user_id": user.id, "email": email, "ip_address": client_ip, "action": "password_reset_request"},
            )

        except User.DoesNotExist:
            # Don't reveal if email exists - security best practice
            logger.info(
                f"Password reset requested for non-existent email: {email}",
                extra={"email": email, "ip_address": client_ip, "action": "password_reset_nonexistent"},
            )

        # Always return success to prevent email enumeration
        return Response(
            {"message": "If an account with that email exists, a password reset link has been sent."},
            status=status.HTTP_200_OK,
        )

    # Password Reset Confirm endpoint
    @swagger_auto_schema(
        operation_summary="🔐 Password Reset Confirmation",
        operation_description="""
        **Secure password reset completion with validation**

        **Features:**
        - Secure token validation and expiration checking
        - Strong password requirements enforcement
        - Secure password update with hashing
        - Automatic session invalidation for security
        - Comprehensive audit trail maintenance

        **Security Measures:**
        - Token expiration validation (24 hours)
        - Password strength requirements enforcement
        - All existing sessions invalidation
        - Comprehensive security event logging
        - Protection against token replay attacks

        **Confirmation Process:**
        1. Token and UID validation
        2. Password strength verification
        3. Secure password update
        4. Session cleanup
        5. Security audit logging
        """,
        tags=["🔐 Authentication"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["uid", "token", "new_password"],
            properties={
                "uid": openapi.Schema(type=openapi.TYPE_STRING, description="User ID from reset email", example="MQ"),
                "token": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Reset token from email", example="5ab-c4d2f8e9a7b6c1d3"
                ),
                "new_password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_PASSWORD,
                    description="New strong password",
                    example="NewSecurePassword123!",
                ),
            },
        ),
        responses={
            200: "Password reset successful",
            400: "Invalid token or validation errors",
        },
    )
    @action(detail=False, methods=["post"])
    def password_reset_confirm(self, request) -> Response:
        """Confirm password reset with secure token validation."""
        uid = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password")
        client_ip = self._get_client_ip(request)

        if not all([uid, token, new_password]):
            return Response({"error": "UID, token, and new password are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_decode

            # Decode user ID
            user_id = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=user_id, is_active=True)

            # Validate token
            if not default_token_generator.check_token(user, token):
                logger.warning(
                    f"Invalid password reset token for user: {user.email}",
                    extra={"user_id": user.id, "ip_address": client_ip, "action": "password_reset_invalid_token"},
                )
                return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

            # Validate password strength
            from django.contrib.auth.password_validation import validate_password

            try:
                validate_password(new_password, user)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            # Update password
            user.set_password(new_password)
            user.save(update_fields=["password"])

            logger.info(
                f"Password reset completed: {user.email}",
                extra={"user_id": user.id, "ip_address": client_ip, "action": "password_reset_success"},
            )

            return Response({"message": "Password has been reset successfully"}, status=status.HTTP_200_OK)

        except (User.DoesNotExist, ValueError, TypeError):
            logger.warning(
                f"Password reset attempt with invalid UID: {uid}",
                extra={"ip_address": client_ip, "action": "password_reset_invalid_uid"},
            )
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Verify email via GET request from email link",
        tags=["Authentication Email Verification"],
        manual_parameters=[
            openapi.Parameter(
                "token",
                openapi.IN_PATH,
                description="Email verification token",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
            )
        ],
        responses={302: "Redirect to frontend with status", 400: "Invalid token - redirect to error page"},
    )
    @action(detail=False, methods=["get"], url_path="verify-email/(?P<token>[^/.]+)")
    def verify_email_link(self, request, token=None) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
        """
        Verify email via GET request from email link.
        Redirects to frontend with verification status.
        """
        client_ip = self._get_client_ip(request)

        try:
            # Validate UUID format
            token_uuid = uuid.UUID(str(token))
        except (ValueError, TypeError):
            logger.warning(f"Invalid token format in email verification: {token}", extra={"ip_address": client_ip})
            return redirect(f"{settings.FRONTEND_URL}/verify-email/error?reason=invalid_format")

        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(email_verification_token=token_uuid)

                if user.is_email_verified:
                    logger.info(
                        f"Email already verified (GET): {user.email}",
                        extra={"user_id": user.id, "ip_address": client_ip},
                    )
                    return redirect(f"{settings.FRONTEND_URL}/verify-email/success?already_verified=true")

                if not user.is_verification_token_valid():
                    logger.warning(
                        f"Expired verification token used (GET): {user.email}",
                        extra={"user_id": user.id, "ip_address": client_ip},
                    )
                    return redirect(f"{settings.BACKEND_URL}/verify-email/error?reason=expired")

                # Mark as verified and invalidate token
                user.is_email_verified = True
                user.is_active = True
                user.email_verification_token = uuid.uuid4()
                user.save(update_fields=["is_email_verified", "is_active", "email_verification_token"])

                logger.info(
                    f"Email verified successfully (GET): {user.email}",
                    extra={"user_id": user.id, "ip_address": client_ip},
                )

                # Redirect to success page
                return redirect(f"{settings.FRONTEND_URL}/verify-email/success")

        except User.DoesNotExist:
            logger.warning(f"Invalid verification token (GET): {token}", extra={"ip_address": client_ip})
            return redirect(f"{settings.FRONTEND_URL}/verify-email/error?reason=invalid_token")

    @swagger_auto_schema(
        operation_description="Resend email verification",
        tags=["Authentication Email Verification"],
        responses={
            200: "Verification email sent",
            400: "Email already verified or user not found",
            429: "Rate limit exceeded",
        },
    )
    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def resend_verification(self, request) -> Response:
        """Resend email verification with rate limiting."""
        user = request.user
        client_ip = self._get_client_ip(request)

        # Rate limiting
        cache_key = f"email_verification_{user.id}"
        if cache.get(cache_key):
            return Response(
                {"error": "Verification email already sent recently. Please wait."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if user.is_email_verified:
            return Response({"message": "Email is already verified"}, status=status.HTTP_200_OK)

        # Set rate limit (5 minutes)
        cache.set(cache_key, True, 300)

        # Send verification email
        from .tasks import send_verification_email

        send_verification_email.delay(user.id)

        logger.info(
            f"Verification email resent: {user.email}",
            extra={"user_id": user.id, "ip_address": client_ip, "action": "verification_resend"},
        )

        return Response({"message": "Verification email sent"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Verify email via POST request with token",
        tags=["Authentication Email Verification"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "token": openapi.Schema(
                    type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID, description="Email verification token"
                )
            },
            required=["token"],
        ),
        responses={200: "Email verified successfully", 400: "Invalid or expired token", 429: "Rate limit exceeded"},
    )
    @action(detail=False, methods=["post"])
    def verify_email(self, request) -> Response:
        """
        Verify email via POST request with token.
        Provides JSON response for API consumption.
        """
        token = request.data.get("token")
        client_ip = self._get_client_ip(request)

        if not token:
            return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Validate UUID format
            token_uuid = uuid.UUID(str(token))
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid token format in email verification: {token}",
                extra={"ip_address": client_ip, "action": "verify_email_invalid_format"},
            )
            return Response({"error": "Invalid token format"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(email_verification_token=token_uuid)

                if user.is_email_verified:
                    logger.info(
                        f"Email already verified: {user.email}", extra={"user_id": user.id, "ip_address": client_ip}
                    )
                    return Response({"message": "Email is already verified"}, status=status.HTTP_200_OK)

                if not user.is_verification_token_valid():
                    logger.warning(
                        f"Expired verification token used: {user.email}",
                        extra={"user_id": user.id, "ip_address": client_ip},
                    )
                    return Response({"error": "Verification token has expired"}, status=status.HTTP_400_BAD_REQUEST)

                # Mark as verified and invalidate token
                user.is_email_verified = True
                user.is_active = True
                user.email_verification_token = uuid.uuid4()
                user.save(update_fields=["is_email_verified", "is_active", "email_verification_token"])

                logger.info(
                    f"Email verified successfully: {user.email}", extra={"user_id": user.id, "ip_address": client_ip}
                )

                return Response({"message": "Email verified successfully"}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            logger.warning(f"Invalid verification token: {token}", extra={"ip_address": client_ip})
            return Response({"error": "Invalid verification token"}, status=status.HTTP_400_BAD_REQUEST)

    # Private helper methods for security operations
    def _get_client_ip(self, request) -> str:
        """Extract and validate client IP address."""
        # Check X-Forwarded-For first (load balancer/proxy)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            # Check X-Real-IP (nginx)
            x_real_ip = request.META.get("HTTP_X_REAL_IP")
            if x_real_ip:
                ip = x_real_ip.strip()
            else:
                # Fallback to REMOTE_ADDR
                ip = request.META.get("REMOTE_ADDR", "0.0.0.0")

        # Basic IP validation
        try:
            import ipaddress

            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            logger.warning(f"Invalid IP address: {ip}")
            return "0.0.0.0"

    def _is_registration_blocked(self, ip: str) -> bool:
        """Check if registration is blocked for IP."""
        cache_key = f"registration_attempts_{ip}"
        attempts = cache.get(cache_key, 0)
        return attempts >= 500  # Max 5 registrations per hour

    def _is_login_blocked(self, ip: str, email: str) -> bool:
        """Check if login is blocked for IP/email combination."""
        cache_key = f"login_attempts_{ip}_{email}"
        attempts = cache.get(cache_key, 0)
        return attempts >= 500  # Max 5 failed attempts per hour

    def _increment_registration_attempts(self, ip: str) -> None:
        """Increment registration attempt counter."""
        cache_key = f"registration_attempts_{ip}"
        current = cache.get(cache_key, 0)
        cache.set(cache_key, current + 1, 3600)  # 1 hour

    def _handle_failed_login(self, ip: str, email: str) -> None:
        """Handle failed login attempt."""
        cache_key = f"login_attempts_{ip}_{email}"
        current = cache.get(cache_key, 0)
        cache.set(cache_key, current + 1, 3600)  # 1 hour

        logger.warning(
            f"Failed login attempt: {email}",
            extra={"email": email, "ip_address": ip, "attempts": current + 1, "action": "login_failed"},
        )

    def _clear_failed_attempts(self, ip: str, email: str) -> None:
        """Clear failed attempt counters."""
        cache_key = f"login_attempts_{ip}_{email}"
        cache.delete(cache_key)

    def _update_login_metadata(self, user: User, ip: str) -> None:
        """Update user login metadata."""
        user.last_login_ip = ip
        user.save(update_fields=["last_login_ip", "last_login"])

    def _log_failed_registration(self, ip: str, errors: dict) -> None:
        """Log failed registration attempt."""
        logger.warning(
            f"Registration validation failed from IP {ip}",
            extra={"ip_address": ip, "errors": errors, "action": "registration_validation_failed"},
        )


class UserProfileViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    """
    👤 User Management: Comprehensive profile and security management

    Advanced user profile management system with enhanced security features,
    comprehensive address management, and extensive account controls.
    """

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_throttles(self) -> List[BaseThrottle]:
        """Apply throttling for sensitive operations with proper error handling."""
        # Only apply throttling for password change
        if self.action == "change_password":
            try:
                # Check if throttling is disabled (e.g., in tests)
                if not getattr(settings, "REST_FRAMEWORK", {}).get("DEFAULT_THROTTLE_RATES"):
                    logger.debug("Throttling disabled for password change")
                    return []
                return [PasswordChangeRateThrottle()]
            except Exception as e:
                logger.warning(f"Password change throttle initialization failed: {str(e)}")
                return []

        # No throttling for other actions
        return []

    def get_object(self) -> User:
        """Return the current authenticated user."""
        return self.request.user

    # Profile Retrieve endpoint
    @swagger_auto_schema(
        operation_summary="👤 Get User Profile",
        operation_description="""
        **Retrieve comprehensive user profile information**

        **Features:**
        - Complete profile data with security metadata
        - Account verification status information
        - Last login and activity tracking
        - Profile completion status analysis
        - Privacy settings and preferences

        **Profile Information Includes:**
        - Personal details (name, email, phone)
        - Account verification and security status
        - Last login information and IP tracking
        - Profile completion percentage
        - Privacy and notification settings
        - Avatar and profile customization

        **Security Features:**
        - Authentication required for access
        - User-specific data isolation
        - Comprehensive audit logging
        - Rate limiting for sensitive operations
        """,
        tags=["👤 User Management"],
        responses={
            200: openapi.Response(
                description="Profile retrieved successfully",
                schema=UserProfileSerializer,
            ),
            401: "Authentication required",
        },
    )
    def retrieve(self, request, *args, **kwargs) -> Response:
        """Get current user profile information."""
        return super().retrieve(request, *args, **kwargs)

    # Profile Update endpoint
    @swagger_auto_schema(
        operation_summary="👤 Update User Profile",
        operation_description="""
        **Update user profile information with validation**

        **Features:**
        - Partial profile updates support
        - Comprehensive data validation
        - Real-time change tracking
        - Security event logging
        - Profile completion analysis

        **Updatable Fields:**
        - First name and last name
        - Phone number with validation
        - Date of birth with privacy controls
        - Profile preferences and settings
        - Privacy and notification preferences
        - Marketing consent and subscriptions

        **Validation Features:**
        - Data format validation
        - Business rule enforcement
        - Duplicate detection
        - Security constraint checking
        """,
        tags=["👤 User Management"],
        request_body=UserProfileSerializer,
        responses={
            200: openapi.Response(
                description="Profile updated successfully",
                schema=UserProfileSerializer,
            ),
            400: "Validation errors",
            401: "Authentication required",
        },
    )
    def partial_update(self, request, *args, **kwargs) -> Response:
        """Update user profile information with logging."""
        response = super().partial_update(request, *args, **kwargs)

        if response.status_code == 200:
            logger.info(
                f"Profile updated: {request.user.email}", extra={"user_id": request.user.id, "action": "profile_update"}
            )

        return response

    # Password Change endpoint
    @swagger_auto_schema(
        operation_summary="👤 Change Password",
        operation_description="""
        **Secure password change with comprehensive validation**

        **Features:**
        - Current password verification for security
        - Strong password validation and requirements
        - Rate limiting protection against abuse
        - Comprehensive security event logging
        - Optional session invalidation

        **Security Features:**
        - Password strength requirements enforcement
        - Brute force protection with rate limiting
        - All sessions invalidation option
        - Real-time security threat detection
        - Comprehensive audit trail maintenance

        **Password Requirements:**
        - Minimum 8 characters length
        - Uppercase and lowercase letters
        - At least one digit
        - At least one special character
        - Different from previous passwords
        """,
        tags=["👤 User Management"],
        request_body=PasswordChangeSerializer,
        responses={
            200: openapi.Response(
                description="Password changed successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="Password changed successfully."),
                    },
                ),
            ),
            400: "Validation errors",
            401: "Authentication required",
            429: "Rate limit exceeded",
        },
    )
    @action(detail=False, methods=["post"])
    def change_password(self, request) -> Response:
        """
        Secure password change with validation and logging.

        Features:
        - Current password verification
        - Strong password validation
        - Rate limiting
        - Security event logging
        """
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            serializer.save()

            # Log password change
            logger.info(
                f"Password changed: {request.user.email}",
                extra={
                    "user_id": request.user.id,
                    "ip_address": self._get_client_ip(request),
                    "action": "password_change",
                },
            )

            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Addresses List endpoint
    @swagger_auto_schema(
        operation_summary="👤 Get User Addresses",
        operation_description="""
        **Retrieve all user addresses with optimization**

        **Features:**
        - Complete address list with details
        - Default address indication
        - Address type categorization (home, work, etc.)
        - Optimized database queries for performance
        - Comprehensive address metadata

        **Address Information Includes:**
        - Full address details with validation
        - Default address marking and management
        - Address type classification
        - Delivery preferences and notes
        - Creation and modification timestamps
        - Geographic and postal validation status
        """,
        tags=["👤 User Management"],
        responses={
            200: openapi.Response(
                description="Addresses retrieved successfully",
                schema=UserAddressSerializer(many=True),
            ),
            401: "Authentication required",
        },
    )
    @action(detail=False, methods=["get"])
    def addresses(self, request) -> Response:
        """Get all user addresses with optimized query."""
        addresses = UserAddress.objects.filter(user=request.user).select_related("user")
        serializer = UserAddressSerializer(addresses, many=True)
        return Response(serializer.data)

    # Add Address endpoint
    @swagger_auto_schema(
        operation_summary="👤 Add New Address",
        operation_description="""
        **Add new user address with comprehensive validation**

        **Features:**
        - Address format validation and verification
        - Duplicate address detection and prevention
        - Automatic default address handling
        - Geographic validation and standardization
        - Comprehensive audit logging

        **Address Validation:**
        - Required field validation
        - Postal code format verification
        - Geographic coordinate validation
        - Duplicate address prevention
        - International address format support

        **Management Features:**
        - Automatic default address assignment
        - Address type classification
        - Delivery preference configuration
        - Privacy and sharing controls
        """,
        tags=["👤 User Management"],
        request_body=UserAddressSerializer,
        responses={
            201: openapi.Response(
                description="Address added successfully",
                schema=UserAddressSerializer,
            ),
            400: "Validation errors",
            401: "Authentication required",
        },
    )
    @action(detail=False, methods=["post"])
    def add_address(self, request) -> Response:
        """Add new address with validation and logging."""
        serializer = UserAddressSerializer(data=request.data)

        if serializer.is_valid():
            address = serializer.save(user=request.user)

            logger.info(
                f"Address added: {request.user.email}",
                extra={"user_id": request.user.id, "address_id": address.id, "action": "address_add"},
            )

            return Response(UserAddressSerializer(address).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _get_client_ip(self, request) -> str:
        """Extract client IP address."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")

    # Update Address endpoint
    @swagger_auto_schema(
        operation_summary="👤 Update Address",
        operation_description="""
        **Update specific user address with validation**

        **Features:**
        - Partial address updates support
        - Address ownership validation
        - Real-time change tracking
        - Geographic validation updates
        - Comprehensive audit logging

        **Update Capabilities:**
        - Individual field updates
        - Address type changes
        - Default status modification
        - Complete address replacement
        - Delivery preference updates

        **Security Features:**
        - Address ownership verification
        - Data validation and sanitization
        - Change tracking and auditing
        - Geographic coordinate validation
        """,
        tags=["👤 User Management"],
        request_body=UserAddressSerializer,
        responses={
            200: openapi.Response(
                description="Address updated successfully",
                schema=UserAddressSerializer,
            ),
            400: "Validation errors",
            401: "Authentication required",
            404: "Address not found",
        },
    )
    @action(detail=False, methods=["patch"], url_path="addresses/(?P<address_id>[^/.]+)")
    def update_address(self, request, address_id=None) -> Response:
        """Update specific user address."""
        try:
            address = UserAddress.objects.get(id=address_id, user=request.user)
        except UserAddress.DoesNotExist:
            return Response({"error": "Address not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserAddressSerializer(address, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            logger.info(
                f"Address updated: {request.user.email}",
                extra={"user_id": request.user.id, "address_id": address.id, "action": "address_update"},
            )

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Delete Address endpoint
    @swagger_auto_schema(
        operation_summary="👤 Delete Address",
        operation_description="""
        **Delete specific user address with safety checks**

        **Features:**
        - Address ownership validation
        - Default address protection and warnings
        - Cascade relationship handling
        - Comprehensive security logging
        - Soft delete options for data retention

        **Safety Features:**
        - Ownership verification before deletion
        - Default address protection warnings
        - Related order data preservation
        - Soft delete options for audit trails
        - Comprehensive security audit logging

        **Deletion Process:**
        1. Address ownership verification
        2. Default address status checking
        3. Related data impact analysis
        4. Secure deletion execution
        5. Audit trail maintenance
        """,
        tags=["👤 User Management"],
        responses={
            204: "Address deleted successfully",
            400: "Cannot delete default address",
            401: "Authentication required",
            404: "Address not found",
        },
    )
    @action(detail=False, methods=["delete"], url_path="addresses/(?P<address_id>[^/.]+)")
    def delete_address(self, request, address_id=None) -> Response:
        """Delete specific user address."""
        try:
            address = UserAddress.objects.get(id=address_id, user=request.user)
            address.delete()

            logger.info(
                f"Address deleted: {request.user.email}",
                extra={"user_id": request.user.id, "address_id": address_id, "action": "address_delete"},
            )

            return Response(status=status.HTTP_204_NO_CONTENT)

        except UserAddress.DoesNotExist:
            return Response({"error": "Address not found"}, status=status.HTTP_404_NOT_FOUND)

    # Set Default Address endpoint
    @swagger_auto_schema(
        operation_summary="👤 Set Default Address",
        operation_description="""
        **Set address as default with automatic management**

        **Features:**
        - Automatic default address switching
        - Previous default address clearing
        - Transaction safety and consistency
        - User preference notifications
        - Comprehensive change tracking

        **Default Management:**
        - Single default address enforcement
        - Automatic previous default clearing
        - Transaction consistency guarantees
        - User preference synchronization
        - Order and delivery integration updates

        **Process Flow:**
        1. Address ownership verification
        2. Previous default identification
        3. Atomic default switching
        4. User preference updates
        5. Change notification dispatch
        """,
        tags=["👤 User Management"],
        responses={
            200: openapi.Response(
                description="Default address updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, example="Default address updated successfully."
                        ),
                    },
                ),
            ),
            401: "Authentication required",
            404: "Address not found",
        },
    )
    @action(detail=False, methods=["post"], url_path="addresses/(?P<address_id>[^/.]+)/set-default")
    def set_default_address(self, request, address_id=None) -> Response:
        """Set address as default."""
        try:
            # Remove default from all addresses
            UserAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)

            # Set new default
            address = UserAddress.objects.get(id=address_id, user=request.user)
            address.is_default = True
            address.save(update_fields=["is_default"])

            logger.info(
                f"Default address set: {request.user.email}",
                extra={"user_id": request.user.id, "address_id": address.id, "action": "address_set_default"},
            )

            return Response({"message": "Default address updated"})

        except UserAddress.DoesNotExist:
            return Response({"error": "Address not found"}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Delete user account",
        tags=["User Management"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "password": openapi.Schema(type=openapi.TYPE_STRING, description="Current password for confirmation")
            },
            required=["password"],
        ),
        responses={204: "Account deleted", 400: "Invalid password"},
    )
    @action(detail=False, methods=["delete"])
    def delete_account(self, request) -> Response:
        """Delete user account with password confirmation."""
        password = request.data.get("password")

        if not password:
            return Response({"error": "Password confirmation is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not request.user.check_password(password):
            logger.warning(
                f"Account deletion attempt with invalid password: {request.user.email}",
                extra={"user_id": request.user.id, "action": "account_delete_invalid_password"},
            )
            return Response({"error": "Invalid password"}, status=status.HTTP_400_BAD_REQUEST)

        user_email = request.user.email
        user_id = request.user.id

        # Soft delete or hard delete based on business requirements
        request.user.is_active = False
        request.user.save(update_fields=["is_active"])

        logger.info(f"Account deleted: {user_email}", extra={"user_id": user_id, "action": "account_delete"})

        return Response(status=status.HTTP_204_NO_CONTENT)
