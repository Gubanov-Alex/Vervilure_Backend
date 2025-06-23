"""JWT Views for User Authentication with English Documentation"""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt.views import TokenBlacklistView, TokenObtainPairView, TokenRefreshView, TokenVerifyView


class JWTTokenObtainPairView(TokenObtainPairView):
    """🔑 JWT: Obtain access and refresh tokens"""

    @swagger_auto_schema(
        operation_summary="🔑 Obtain JWT tokens",
        operation_description="""
        **User authentication and JWT token generation**

        This endpoint authenticates users via email/password and returns:
        - Access token (15 minutes) - for API requests
        - Refresh token (7 days) - for token renewal

        **Access token usage:**
        ```
        Authorization: Bearer <access_token>
        ```
        
        **Token Features:**
        - Access tokens have short lifespan for security
        - Refresh tokens are used to obtain new access tokens
        - All tokens are tied to specific users
        - Blacklist support for immediate token revocation
        
        **Security:**
        - Uses HS256 algorithm for signing
        - Includes JTI (JWT ID) for tracking
        - Supports blacklist for immediate revocation
        - Rate limiting and brute force protection
        """,
        tags=["🔑 JWT Authentication"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password"],
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_EMAIL,
                    description="User email address",
                    example="user@example.com",
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_PASSWORD,
                    description="User password",
                    example="SecurePassword123!",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Tokens obtained successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "access": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="JWT Access token (15 minutes)",
                            example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        ),
                        "refresh": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="JWT Refresh token (7 days)",
                            example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        ),
                    },
                ),
            ),
            401: "Invalid credentials",
            400: "Validation error",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class JWTTokenRefreshView(TokenRefreshView):
    """🔄 JWT: Refresh access token"""

    @swagger_auto_schema(
        operation_summary="🔄 Refresh access token",
        operation_description="""
        **Obtain new access token using refresh token**

        When access token expires (after 15 minutes), use this endpoint
        to get a new access token without re-authentication.

        **Token Rotation:**
        - Each refresh generates a new access token
        - Refresh tokens can be rotated (optional)
        - Old tokens automatically become invalid
        
        **Security:**
        - Validates refresh token integrity
        - Checks against blacklist
        - Protection against replay attacks
        - Limited token lifespan
        
        **Best Practices:**
        - Refresh tokens proactively before expiration
        - Implement automatic refresh in client applications
        - Handle refresh token expiration scenarios
        - Store tokens securely on client side
        """,
        tags=["🔑 JWT Authentication"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh"],
            properties={
                "refresh": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Valid JWT refresh token",
                    example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Token refreshed successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "access": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="New JWT access token",
                            example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        ),
                    },
                ),
            ),
            401: "Invalid or expired refresh token",
            400: "Invalid token format",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class JWTTokenVerifyView(TokenVerifyView):
    """✅ JWT: Verify token validity"""

    @swagger_auto_schema(
        operation_summary="✅ Verify token",
        operation_description="""
        **Verify JWT token validity**

        Use this endpoint to check:
        - Token expiration status (exp claim)
        - Token signature validity
        - Blacklist status
        - Token structure integrity

        **Verification Parameters:**
        - Expiration time (exp)
        - Token signature
        - Payload structure
        - Blacklist status
        - Signing algorithm
        
        **Use Cases:**
        - Validation before critical operations
        - Frontend application checks
        - Token debugging and troubleshooting
        - Authorization middleware validation
        
        **Important Notes:**
        - Token remains valid until expiration
        - Verification does not extend token lifetime
        - Use for validation in critical operations
        - Does not consume any token uses
        """,
        tags=["🔑 JWT Authentication"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["token"],
            properties={
                "token": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="JWT token to verify (access or refresh)",
                    example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Token is valid",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "token_type": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Type of verified token", example="access"
                        ),
                    },
                ),
            ),
            401: "Token is invalid or expired",
            400: "Invalid token format",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class JWTTokenBlacklistView(TokenBlacklistView):
    """🚫 JWT: Blacklist refresh token (Logout)"""

    @swagger_auto_schema(
        operation_summary="🚫 Blacklist token",
        operation_description="""
        **Add refresh token to blacklist (logout)**

        This endpoint blacklists a refresh token, effectively ending the user session.
        After blacklisting:
        - Refresh token cannot be used to obtain new access tokens
        - Access token continues to work until expiration
        - User must re-authenticate to get new tokens

        **Blacklist Mechanism:**
        - Token is added to database blacklist
        - Blacklist check occurs on every token use
        - Blacklisted tokens are auto-deleted after expiration
        - Supports both refresh and access tokens
        
        **Use Cases:**
        - User logout from application
        - Security incident response
        - Compromised token revocation
        - Session termination on suspicious activity
        
        **Security Benefits:**
        - Immediate token invalidation
        - Protection against token reuse
        - Audit trail for all blacklist operations
        - Integration with monitoring systems
        """,
        tags=["🔑 JWT Authentication"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh"],
            properties={
                "refresh": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="JWT refresh token to blacklist",
                    example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Token blacklisted successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(
                            type=openapi.TYPE_STRING, example="Token successfully added to blacklist"
                        ),
                    },
                ),
            ),
            400: "Invalid token format or already blacklisted",
            401: "Token is invalid",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
