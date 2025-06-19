from django.urls import path

from .views import UserProfileViewSet

app_name = "users"

profile_list = UserProfileViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "delete_account"}  # Добавлено
)

urlpatterns = [
    # User profile endpoints
    path("me/", profile_list, name="profile"),
    path("me/change-password/", UserProfileViewSet.as_view({"post": "change_password"}), name="change_password"),
    # Address management
    path("me/addresses/", UserProfileViewSet.as_view({"get": "addresses"}), name="addresses"),
    path("me/addresses/add/", UserProfileViewSet.as_view({"post": "add_address"}), name="add_address"),
    path(
        "me/addresses/<int:address_id>/",
        UserProfileViewSet.as_view({"patch": "update_address", "delete": "delete_address"}),
        name="address_detail",
    ),
    path(
        "me/addresses/<int:address_id>/set-default/",
        UserProfileViewSet.as_view({"post": "set_default_address"}),
        name="address_set_default",
    ),
]
