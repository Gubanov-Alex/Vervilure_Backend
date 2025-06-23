"""
Test-specific URL configuration for proper namespace resolution.
This file ensures that all authentication and user management endpoints have correct namespaces.
"""

from django.contrib import admin
from django.urls import include, path

# Import for email verification endpoint
from src.apps.accounts.views import AuthViewSet

urlpatterns = [
    path("admin/", admin.site.urls),
    # Primary authentication endpoints with 'auth' namespace
    path("api/v1/auth/", include(("src.apps.accounts.auth_urls", "auth"), namespace="auth")),
    # FIXED: Add proper namespace for user management endpoints
    path("api/v1/users/", include(("src.apps.accounts.user_urls", "users"), namespace="users")),
    # Legacy namespace for backward compatibility with existing tests
    path("accounts/", include(("src.apps.accounts.auth_urls", "accounts"), namespace="accounts")),
    # Alternative auth endpoints for different test scenarios
    path("auth/", include(("src.apps.accounts.auth_urls", "auth-alt"), namespace="auth-alt")),
    # Direct email verification endpoint (fallback)
    path("verify-email/<uuid:token>/", AuthViewSet.as_view({"get": "verify_email_link"}), name="verify_email_link"),
    # Django allauth URLs (if needed)
    path("allauth/", include("allauth.urls")),
    # Additional test-specific endpoints
    path(
        "test/",
        include(
            [
                # Debug endpoint for testing URL resolution
                path("auth/", include("src.apps.accounts.auth_urls")),
                # Add more test-specific patterns here if needed
            ]
        ),
    ),
]

# Debug: Print available URL patterns in test mode
import sys

if "pytest" in sys.modules or "test" in sys.argv:
    print("\n[Test URLs] Available namespaces:")
    print("  - auth:* (api/v1/auth/)")
    print("  - users:* (api/v1/users/) [FIXED]")
    print("  - accounts:* (accounts/)")
    print("  - auth-alt:* (auth/)")
    print("  - Direct patterns available")
