from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

# Swagger documentation setup
schema_view = get_schema_view(
    openapi.Info(
        title="Vervilure E-commerce API",
        default_version="v1",
        description="REST API for Vervilure e-commerce platform",
        terms_of_service="https://www.vervilure.com/terms/",
        contact=openapi.Contact(email="api@vervilure.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # API routes - четкое разделение по функциональности
    path("api/v1/auth/", include("src.apps.accounts.auth_urls")),  # JWT + authentication
    path("api/v1/users/", include("src.apps.accounts.user_urls")),  # User profiles
    path("api/v1/", include("src.api.urls")),  # Business logic modules
    # Swagger documentation
    path("swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    # Django allauth для web-интерфейса
    path("accounts/", include("allauth.urls")),
]

# Custom error handlers
handler400 = "src.core.views.api_400_handler"
handler401 = "src.core.views.api_401_handler"
handler404 = "src.core.views.api_404_handler"
handler500 = "src.core.views.api_500_handler"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
