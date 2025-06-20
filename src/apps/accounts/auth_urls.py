from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenBlacklistView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
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
                # JWT endpoints (standalone views)
                path("jwt/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
                path("jwt/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
                path("jwt/verify/", TokenVerifyView.as_view(), name="token_verify"),
                path("jwt/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
                # Future: path('facebook/', AuthViewSet.as_view({'post': 'facebook_oauth'}), name='facebook_oauth'),
                # Future: path('apple/', AuthViewSet.as_view({'post': 'apple_oauth'}), name='apple_oauth'),
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
    # Token management
    path(
        "token/",
        include(
            [
                # path('refresh/', include('rest_framework_simplejwt.urls')),  # JWT refresh endpoint
                path("blacklist/", AuthViewSet.as_view({"post": "logout"}), name="token_blacklist"),  # Alias for logout
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
