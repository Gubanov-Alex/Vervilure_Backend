from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenBlacklistView  # Добавлено
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import AuthViewSet

app_name = "auth"

# ViewSet для auth операций
router = DefaultRouter()
router.register("", AuthViewSet, basename="auth")

urlpatterns = [
    # JWT endpoints (standalone views)
    path("jwt/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("jwt/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("jwt/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("jwt/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),  # Добавлено
] + router.urls
