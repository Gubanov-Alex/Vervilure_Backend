"""
Test-specific URL configuration for CI environment.
This ensures proper URL routing during automated testing.
"""

from django.contrib import admin
from django.urls import include, path

# Import for email verification endpoint
from src.apps.accounts.views import AuthViewSet

urlpatterns = [
    path("admin/", admin.site.urls),
    # Authentication endpoints with proper namespace
    path("api/v1/auth/", include(("src.apps.accounts.auth_urls", "auth"), namespace="auth")),
    path("api/v1/users/", include("src.apps.accounts.user_urls")),
    # Legacy namespace for backward compatibility
    path("accounts/", include(("src.apps.accounts.auth_urls", "accounts"), namespace="accounts")),
    # Direct email verification endpoint (fallback)
    path("verify-email/<uuid:token>/", AuthViewSet.as_view({"get": "verify_email_link"}), name="verify_email_link"),
    # Django allauth URLs (if needed)
    path("allauth/", include("allauth.urls")),
]

# Additional test-specific configurations
if True:  # Always True for test environment
    # Add debug endpoints for testing
    urlpatterns += [
        # Test endpoints for debugging
        path(
            "test/",
            include(
                [
                    path("auth/", include("src.apps.accounts.auth_urls")),
                ]
            ),
        ),
    ]
