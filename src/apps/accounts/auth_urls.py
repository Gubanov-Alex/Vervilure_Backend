from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .jwt_views import (
    JWTTokenBlacklistView,
    JWTTokenObtainPairView,
    JWTTokenRefreshView,
    JWTTokenVerifyView,
)
from .views import AuthViewSet

# Authentication router for organized endpoints
auth_router = DefaultRouter()
auth_router.register(r"", AuthViewSet, basename="auth")

# Authentication module URLs
# Base path: /api/v1/auth/
urlpatterns = [
    # Core authentication endpoints
    path(
        "",
        include(
            [
                # User registration and authentication
                path("register/", AuthViewSet.as_view({"post": "register"}), name="register"),
                path("login/", AuthViewSet.as_view({"post": "login"}), name="login"),
                path("logout/", AuthViewSet.as_view({"post": "logout"}), name="logout"),
                # Social authentication
                path("google/", AuthViewSet.as_view({"post": "google_oauth"}), name="google_oauth"),
            ]
        ),
    ),
    # 🔑 JWT Authentication endpoints - отдельная группа
    path(
        "jwt/",
        include(
            [
                path("", JWTTokenObtainPairView.as_view(), name="token_obtain_pair"),
                path("refresh/", JWTTokenRefreshView.as_view(), name="token_refresh"),
                path("verify/", JWTTokenVerifyView.as_view(), name="token_verify"),
                path("blacklist/", JWTTokenBlacklistView.as_view(), name="token_blacklist"),
            ]
        ),
    ),
    # Email verification workflows
    path(
        "email/",
        include(
            [
                path("verify/", AuthViewSet.as_view({"post": "verify_email"}), name="verify_email"),
                path(
                    "resend-verification/",
                    AuthViewSet.as_view({"post": "resend_verification"}),
                    name="resend_verification",
                ),
            ]
        ),
    ),
    # Password management
    path(
        "password/",
        include(
            [
                path("reset/", AuthViewSet.as_view({"post": "password_reset"}), name="password_reset"),
                path(
                    "reset/confirm/",
                    AuthViewSet.as_view({"post": "password_reset_confirm"}),
                    name="password_reset_confirm",
                ),
            ]
        ),
    ),
    # Legacy token management (для обратной совместимости)
    path(
        "token/",
        include(
            [
                # Алиас для logout через token blacklist
                path("blacklist/", AuthViewSet.as_view({"post": "logout"}), name="legacy_token_blacklist"),
            ]
        ),
    ),
    # Two-factor authentication (future implementation)
    path(
        "2fa/",
        include(
            [
                # path('enable/', AuthViewSet.as_view({'post': 'enable_2fa'}), name='enable_2fa'),
                # path('disable/', AuthViewSet.as_view({'post': 'disable_2fa'}), name='disable_2fa'),
                # path('verify/', AuthViewSet.as_view({'post': 'verify_2fa'}), name='verify_2fa'),
            ]
        ),
    ),
]

# URL patterns for documentation and debugging
app_name = "auth"
