from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

# Import for email verification endpoint
from src.apps.accounts.views import AuthViewSet

# Import health check views
from src.core.views import health_check, liveness_check, readiness_check

# Swagger documentation setup
schema_view = get_schema_view(
    openapi.Info(
        title="Vervilure E-commerce API",
        default_version="v1",
        description="REST API for Vervilure e-commerce platform",
        terms_of_service="https://www.vervilure.com/terms/",
        contact=openapi.Contact(
            email="future.htm@gmail.com", url="https://www.linkedin.com/in/oleksandr-gubanov-python-developer/"
        ),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # Health check endpoints (must be first for Docker)
    path("health/", health_check, name="health_check"),
    path("ready/", readiness_check, name="readiness_check"),
    path("alive/", liveness_check, name="liveness_check"),
    # Admin and core functionality
    path("admin/", admin.site.urls),
    path("verify-email/<uuid:token>/", AuthViewSet.as_view({"get": "verify_email_link"}), name="verify_email_link"),
    # API endpoints
    path("api/v1/auth/", include("src.apps.accounts.auth_urls"), name="jwt"),  # JWT + authentication
    path("api/v1/users/", include("src.apps.accounts.user_urls"), name="users"),  # User management
    # TODO: Uncomment when modules are implemented
    # path("api/v1/", include("src.api.urls"), name="Logic"),  # Business logic modules
    # Documentation endpoints
    path("swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    # Django allauth
    path("accounts/", include("allauth.urls")),
]

# Custom error handlers
handler400 = "src.core.views.api_400_handler"
handler401 = "src.core.views.api_401_handler"
handler404 = "src.core.views.api_404_handler"
handler500 = "src.core.views.api_500_handler"

# Development static files serving
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
