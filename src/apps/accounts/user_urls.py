from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import UserProfileViewSet

# User management router
user_router = DefaultRouter()
user_router.register(r"", UserProfileViewSet, basename="users")

# User management module URLs
# Base path: /api/v1/users/
urlpatterns = [
    # Profile management
    path(
        "profile/",
        include(
            [
                path(
                    "",
                    UserProfileViewSet.as_view({"get": "retrieve", "patch": "partial_update", "put": "update"}),
                    name="profile",
                ),
                path("avatar/", UserProfileViewSet.as_view({"post": "update_avatar"}), name="update_avatar"),
                path(
                    "preferences/",
                    UserProfileViewSet.as_view({"get": "get_preferences", "patch": "update_preferences"}),
                    name="preferences",
                ),
            ]
        ),
    ),
    # Address management
    path(
        "addresses/",
        include(
            [
                path("", UserProfileViewSet.as_view({"get": "addresses", "post": "add_address"}), name="addresses"),
                path(
                    "<int:address_id>/",
                    UserProfileViewSet.as_view({"patch": "update_address", "delete": "delete_address"}),
                    name="address_detail",
                ),
                path(
                    "<int:address_id>/set-default/",
                    UserProfileViewSet.as_view({"post": "set_default_address"}),
                    name="set_default_address",
                ),
            ]
        ),
    ),
    # Security settings
    path(
        "security/",
        include(
            [
                path(
                    "password/change/", UserProfileViewSet.as_view({"post": "change_password"}), name="change_password"
                ),
                path(
                    "sessions/",
                    UserProfileViewSet.as_view({"get": "active_sessions", "delete": "revoke_all_sessions"}),
                    name="sessions",
                ),
                path(
                    "sessions/<str:session_id>/",
                    UserProfileViewSet.as_view({"delete": "revoke_session"}),
                    name="revoke_session",
                ),
            ]
        ),
    ),
    # Account management
    path(
        "account/",
        include(
            [
                path(
                    "deactivate/", UserProfileViewSet.as_view({"post": "deactivate_account"}), name="deactivate_account"
                ),
                path("delete/", UserProfileViewSet.as_view({"delete": "delete_account"}), name="delete_account"),
                path("export/", UserProfileViewSet.as_view({"get": "export_data"}), name="export_data"),
            ]
        ),
    ),
    # Communication preferences
    path(
        "notifications/",
        include(
            [
                path(
                    "",
                    UserProfileViewSet.as_view(
                        {"get": "notification_settings", "patch": "update_notification_settings"}
                    ),
                    name="notification_settings",
                ),
                path(
                    "email/",
                    UserProfileViewSet.as_view({"patch": "update_email_preferences"}),
                    name="email_preferences",
                ),
                path(
                    "push/", UserProfileViewSet.as_view({"patch": "update_push_preferences"}), name="push_preferences"
                ),
            ]
        ),
    ),
    # Shopping preferences and history
    path(
        "shopping/",
        include(
            [
                path(
                    "wishlist/",
                    UserProfileViewSet.as_view({"get": "wishlist", "post": "add_to_wishlist"}),
                    name="wishlist",
                ),
                path(
                    "wishlist/<int:item_id>/",
                    UserProfileViewSet.as_view({"delete": "remove_from_wishlist"}),
                    name="remove_from_wishlist",
                ),
                path(
                    "viewed-products/", UserProfileViewSet.as_view({"get": "viewed_products"}), name="viewed_products"
                ),
                path(
                    "recommendations/", UserProfileViewSet.as_view({"get": "recommendations"}), name="recommendations"
                ),
            ]
        ),
    ),
    # Social features (future implementation)
    path(
        "social/",
        include(
            [
                # path('followers/', UserProfileViewSet.as_view({'get': 'followers'}), name='followers'),
                # path('following/', UserProfileViewSet.as_view({'get': 'following'}), name='following'),
                # path('reviews/', UserProfileViewSet.as_view({'get': 'user_reviews'}), name='user_reviews'),
            ]
        ),
    ),
]

# URL patterns for documentation
app_name = "users"
