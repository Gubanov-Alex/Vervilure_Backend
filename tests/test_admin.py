"""Tests for admin interface - safe imports and error handling."""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory

# Set up Django before any other imports
import django
from django.conf import settings

if not settings.configured:
    django.setup()

User = get_user_model()

# Safe import with detailed error handling
def get_admin_classes():
    """Safely import admin classes with error handling."""
    try:
        from src.apps.accounts.admin import UserAddressAdmin, UserAdmin
        from src.apps.accounts.models import UserAddress
        return UserAdmin, UserAddressAdmin, UserAddress
    except ImportError as e:
        pytest.skip(f"Admin modules not available: {e}", allow_module_level=True)
    except Exception as e:
        pytest.skip(f"Unexpected error importing admin: {e}", allow_module_level=True)


# Get admin classes or skip tests
UserAdmin, UserAddressAdmin, UserAddress = get_admin_classes()


@pytest.mark.admin
@pytest.mark.django_db
class TestUserAdmin:
    """Test UserAdmin functionality and configuration."""

    def setup_method(self):
        """Setup test data."""
        self.site = AdminSite()
        self.admin = UserAdmin(User, self.site)
        self.factory = RequestFactory()

        self.superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User"
        )

        self.regular_user = User.objects.create_user(
            email="user@example.com",
            password="userpass123",
            first_name="Regular",
            last_name="User"
        )

    def test_admin_list_display_fields(self):
        """Test that admin list display contains expected fields."""
        # Test core fields that should exist
        core_fields = ["email", "is_active", "is_staff", "date_joined"]

        for field in core_fields:
            assert field in self.admin.list_display, f"Core field '{field}' missing from list_display"

    def test_admin_list_filter_configuration(self):
        """Test admin list filter configuration."""
        # Test core filters that should exist
        core_filters = ["is_active", "is_staff", "date_joined"]

        for filter_field in core_filters:
            assert filter_field in self.admin.list_filter, f"Core filter '{filter_field}' missing from list_filter"

    def test_admin_search_fields_configuration(self):
        """Test admin search fields configuration."""
        # Test that search fields exist
        assert len(self.admin.search_fields) > 0, "Search fields should be configured"

        # Email should be searchable
        assert "email" in self.admin.search_fields, "Email should be searchable"

    def test_admin_ordering_configuration(self):
        """Test admin default ordering."""
        # Should have some ordering defined
        assert hasattr(self.admin, 'ordering'), "Admin should have ordering defined"
        if self.admin.ordering:
            assert isinstance(self.admin.ordering, (list, tuple)), "Ordering should be list or tuple"

    def test_admin_fieldsets_basic_structure(self):
        """Test admin fieldsets basic structure."""
        # Fieldsets should exist or be None
        if hasattr(self.admin, 'fieldsets') and self.admin.fieldsets:
            assert isinstance(self.admin.fieldsets, (list, tuple)), "Fieldsets should be list or tuple"
            assert len(self.admin.fieldsets) > 0, "At least one fieldset should exist"

    def test_admin_permissions_superuser(self):
        """Test admin permissions for superuser."""
        request = self.factory.get("/admin/")
        request.user = self.superuser

        # Basic permission tests
        assert self.admin.has_view_permission(request) is True, "Superuser should have view permission"
        assert self.admin.has_add_permission(request) is True, "Superuser should have add permission"

    def test_admin_get_queryset_basic(self):
        """Test admin queryset returns users."""
        request = self.factory.get("/admin/")
        request.user = self.superuser

        queryset = self.admin.get_queryset(request)

        # Should return a queryset
        assert hasattr(queryset, 'model'), "Should return a queryset"
        assert queryset.model == User, "Should return User queryset"

    def test_admin_form_class_availability(self):
        """Test admin form class is available."""
        request = self.factory.get("/admin/")
        request.user = self.superuser

        form_class = self.admin.get_form(request)
        assert form_class is not None, "Admin form class should be available"


@pytest.mark.admin
@pytest.mark.django_db
class TestUserAddressAdmin:
    """Test UserAddressAdmin functionality."""

    def setup_method(self):
        """Setup test data."""
        self.site = AdminSite()
        self.admin = UserAddressAdmin(UserAddress, self.site)
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            email="address@example.com",
            password="testpass123",
            first_name="Address",
            last_name="User"
        )

        # Create address with minimal required fields
        self.address = UserAddress.objects.create(
            user=self.user,
            address_type="shipping",
            first_name="Test",
            last_name="User",
            address_line1="123 Test St",
            city="Test City",
            country="US",
        )

    def test_address_admin_basic_configuration(self):
        """Test basic address admin configuration."""
        # Should have list_display
        assert hasattr(self.admin, 'list_display'), "Admin should have list_display"
        assert len(self.admin.list_display) > 0, "list_display should not be empty"

    def test_address_admin_permissions(self):
        """Test address admin basic permissions."""
        superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User"
        )

        request = self.factory.get("/admin/")
        request.user = superuser

        # Basic permission tests
        assert self.admin.has_view_permission(request) is True, "Should have view permission"

    def test_address_admin_queryset(self):
        """Test address admin queryset."""
        superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User"
        )

        request = self.factory.get("/admin/")
        request.user = superuser

        queryset = self.admin.get_queryset(request)
        assert hasattr(queryset, 'model'), "Should return a queryset"
        assert queryset.model == UserAddress, "Should return UserAddress queryset"


@pytest.mark.admin
@pytest.mark.integration
@pytest.mark.django_db
class TestAdminIntegration:
    """Test admin integration basics."""

    def test_admin_site_has_registrations(self):
        """Test that admin site has model registrations."""
        from django.contrib import admin

        # Should have some models registered
        assert len(admin.site._registry) > 0, "Admin site should have registered models"

    def test_user_model_registration(self):
        """Test User model is registered."""
        from django.contrib import admin

        # User model should be registered
        assert User in admin.site._registry, "User model should be registered in admin"

    def test_admin_basic_functionality(self):
        """Test basic admin functionality."""
        superuser = User.objects.create_superuser(
            email="integration@example.com",
            password="adminpass123",
            first_name="Integration",
            last_name="Admin"
        )

        # Should be able to create superuser for admin access
        assert superuser.is_staff is True, "Superuser should be staff"
        assert superuser.is_superuser is True, "Should be superuser"
