from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("src.apps.accounts.auth_urls")),
    path("api/v1/users/", include("src.apps.accounts.user_urls")),
    path("accounts/", include("allauth.urls")),  # Для email verification
]
