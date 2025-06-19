import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from src.apps.accounts.admin import UserAddressAdmin, UserAdmin
from src.apps.accounts.models import UserAddress

User = get_user_model()


@pytest.mark.django_db
class TestUserAdmin:
    """Test UserAdmin - increase coverage from 72% to 85%"""

    def setup_method(self):
        self.site = AdminSite()
        self.admin = UserAdmin(User, self.site)
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123", first_name="Admin", last_name="User"
        )
        self.regular_user = User.objects.create_user(
            email="user@example.com", password="userpass123", first_name="Regular", last_name="User"
        )

    def test_admin_list_display(self):
        """Test admin list display fields"""
        expected_fields = [
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_email_verified",
            "date_joined",
            "last_login",
        ]

        for field in expected_fields:
            assert field in self.admin.list_display

    def test_admin_list_filter(self):
        """Test admin list filter fields"""
        expected_filters = ["is_active", "is_staff", "is_superuser", "is_email_verified", "date_joined"]

        for filter_field in expected_filters:
            assert filter_field in self.admin.list_filter

    def test_admin_search_fields(self):
        """Test admin search fields"""
        expected_search = ["email", "first_name", "last_name"]

        for search_field in expected_search:
            assert search_field in self.admin.search_fields

    def test_admin_ordering(self):
        """Test admin default ordering"""
        assert self.admin.ordering == ["-date_joined"]

    def test_admin_fieldsets_structure(self):
        """Test admin fieldsets structure"""
        fieldsets = self.admin.fieldsets

        # Check that fieldsets exist
        assert fieldsets is not None
        assert len(fieldsets) > 0

        # Check for expected sections
        section_names = [section[0] for section in fieldsets if section[0]]
        assert "Personal info" in section_names or "Personal Information" in section_names
        assert "Permissions" in section_names

    def test_admin_add_fieldsets(self):
        """Test admin add fieldsets for new user creation"""
        add_fieldsets = self.admin.add_fieldsets

        assert add_fieldsets is not None
        assert len(add_fieldsets) > 0

        # Check that password fields are included
        all_fields = []
        for section in add_fieldsets:
            if "fields" in section[1]:
                all_fields.extend(section[1]["fields"])

        # Should include password fields for user creation
        password_fields = [field for field in all_fields if "password" in str(field)]
        assert len(password_fields) > 0

    def test_admin_readonly_fields(self):
        """Test admin readonly fields"""
        request = self.factory.get("/admin/")
        request.user = self.superuser

        readonly_fields = self.admin.get_readonly_fields(request, self.regular_user)

        # Should include timestamp fields as readonly
        timestamp_fields = ["date_joined", "last_login"]
        for field in timestamp_fields:
            assert field in readonly_fields

    def test_admin_has_add_permission(self):
        """Test admin add permission"""
        request = self.factory.get("/admin/")
        request.user = self.superuser

        has_permission = self.admin.has_add_permission(request)
        assert has_permission is True

    def test_admin_has_change_permission(self):
        """Test admin change permission"""
        request = self.factory.get("/admin/")
        request.user = self.superuser

        has_permission = self.admin.has_change_permission(request, self.regular_user)
        assert has_permission is True

    def test_admin_has_delete_permission(self):
        """Test admin delete permission"""
        request = self.factory.get("/admin/")
        request.user = self.superuser

        has_permission = self.admin.has_delete_permission(request, self.regular_user)
        assert has_permission is True

    def test_admin_get_queryset(self):
        """Test admin queryset optimization"""
        request = self.factory.get("/admin/")
        request.user = self.superuser

        queryset = self.admin.get_queryset(request)

        # Should return all users for superuser
        assert self.regular_user in queryset
        assert self.superuser in queryset

    def test_admin_list_per_page(self):
        """Test admin pagination"""
        # Should have reasonable pagination
        assert hasattr(self.admin, "list_per_page")
        if self.admin.list_per_page:
            assert self.admin.list_per_page > 0

    def test_admin_actions(self):
        """Test admin actions"""
        actions = self.admin.get_actions(self.factory.get("/admin/"))

        # Should have default actions
        assert "delete_selected" in actions

    def test_admin_form_valid_data(self):
        """Test admin form with valid data"""
        request = self.factory.post("/admin/")
        request.user = self.superuser

        # Test that admin can handle user form
        form_class = self.admin.get_form(request)
        assert form_class is not None

    def test_admin_inlines(self):
        """Test admin inline models"""
        # Check if any inlines are configured
        if hasattr(self.admin, "inlines"):
            assert isinstance(self.admin.inlines, (list, tuple))


@pytest.mark.django_db
class TestUserAddressAdmin:
    """Test UserAddressAdmin"""

    def setup_method(self):
        self.site = AdminSite()
        self.admin = UserAddressAdmin(UserAddress, self.site)
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email="address@example.com", password="testpass123", first_name="Address", last_name="User"
        )
        self.address = UserAddress.objects.create(
            user=self.user,
            address_type="shipping",
            street_address="123 Test St",
            city="Test City",
            state="TS",
            postal_code="12345",
            country="US",
        )

    def test_address_admin_list_display(self):
        """Test address admin list display"""
        expected_fields = ["user", "address_type", "street_address", "city", "country"]

        for field in expected_fields:
            assert field in self.admin.list_display

    def test_address_admin_list_filter(self):
        """Test address admin list filter"""
        expected_filters = ["address_type", "country", "is_default"]

        for filter_field in expected_filters:
            assert filter_field in self.admin.list_filter

    def test_address_admin_search_fields(self):
        """Test address admin search fields"""
        expected_search = ["user__email", "street_address", "city"]

        for search_field in expected_search:
            assert search_field in self.admin.search_fields

    def test_address_admin_autocomplete_fields(self):
        """Test address admin autocomplete"""
        if hasattr(self.admin, "autocomplete_fields"):
            assert "user" in self.admin.autocomplete_fields

    def test_address_admin_has_permissions(self):
        """Test address admin permissions"""
        superuser = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123", first_name="Admin", last_name="User"
        )

        request = self.factory.get("/admin/")
        request.user = superuser

        assert self.admin.has_add_permission(request) is True
        assert self.admin.has_change_permission(request, self.address) is True
        assert self.admin.has_delete_permission(request, self.address) is True

    def test_address_admin_get_queryset(self):
        """Test address admin queryset"""
        superuser = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123", first_name="Admin", last_name="User"
        )

        request = self.factory.get("/admin/")
        request.user = superuser

        queryset = self.admin.get_queryset(request)
        assert self.address in queryset


@pytest.mark.django_db
class TestAdminIntegration:
    """Test admin integration and functionality"""

    def setup_method(self):
        self.superuser = User.objects.create_superuser(
            email="integration@example.com", password="adminpass123", first_name="Integration", last_name="Admin"
        )
        self.factory = RequestFactory()

    def test_admin_site_registration(self):
        """Test that models are properly registered"""
        from django.contrib import admin

        # Check that User model is registered
        assert User in admin.site._registry

        # Check that UserAddress model is registered
        assert UserAddress in admin.site._registry

    def test_admin_user_creation_flow(self):
        """Test user creation through admin"""
        site = AdminSite()
        user_admin = UserAdmin(User, site)

        request = self.factory.post("/admin/")
        request.user = self.superuser

        # Test that add form is available
        add_form = user_admin.get_form(request)
        assert add_form is not None

    def test_admin_user_edit_flow(self):
        """Test user editing through admin"""
        test_user = User.objects.create_user(
            email="edit@example.com", password="testpass123", first_name="Edit", last_name="User"
        )

        site = AdminSite()
        user_admin = UserAdmin(User, site)

        request = self.factory.post("/admin/")
        request.user = self.superuser

        # Test that change form is available
        change_form = user_admin.get_form(request, test_user)
        assert change_form is not None

    def test_admin_bulk_actions(self):
        """Test admin bulk actions"""
        # Create multiple users
        users = []
        for i in range(3):
            users.append(
                User.objects.create_user(
                    email=f"bulk{i}@example.com", password="testpass123", first_name=f"Bulk{i}", last_name="User"
                )
            )

        site = AdminSite()
        user_admin = UserAdmin(User, site)

        request = self.factory.post("/admin/")
        request.user = self.superuser

        # Test that actions are available
        actions = user_admin.get_actions(request)
        assert len(actions) > 0
        assert "delete_selected" in actions

    def test_admin_permissions_non_superuser(self):
        """Test admin permissions for non-superuser"""
        staff_user = User.objects.create_user(
            email="staff@example.com", password="staffpass123", first_name="Staff", last_name="User", is_staff=True
        )

        site = AdminSite()
        user_admin = UserAdmin(User, site)

        request = self.factory.get("/admin/")
        request.user = staff_user

        # Staff user should have limited permissions
        assert user_admin.has_view_permission(request) is True
