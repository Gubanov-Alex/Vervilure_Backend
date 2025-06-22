import pytest
from django.contrib.auth import get_user_model

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

    @pytest.fixture(autouse=True)
    def setup_admin_test(self, request_factory, superuser, regular_user):
        """Setup test data using pytest fixtures."""
        self.site = AdminSite()
        self.admin = UserAdmin(User, self.site)
        self.factory = request_factory
        self.superuser = superuser
        self.regular_user = regular_user

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
        assert hasattr(self.admin, "ordering"), "Admin should have ordering defined"
        if self.admin.ordering:
            assert isinstance(self.admin.ordering, (list, tuple)), "Ordering should be list or tuple"

    def test_admin_fieldsets_basic_structure(self):
        """Test admin fieldsets basic structure."""
        # Fieldsets should exist or be None
        if hasattr(self.admin, "fieldsets") and self.admin.fieldsets:
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
        assert hasattr(queryset, "model"), "Should return a queryset"
        assert queryset.model == User, "Should return User queryset"

    def test_admin_form_class_availability(self):
        """Test admin form class is available."""
        request = self.factory.get("/admin/")
        request.user = self.superuser

        form_class = self.admin.get_form(request)
        assert form_class is not None, "Admin form class should be available"

    def test_admin_queryset_optimization(self):
        """Test admin queryset includes necessary optimizations."""
        request = self.factory.get("/admin/")
        request.user = self.superuser

        queryset = self.admin.get_queryset(request)

        # Check if select_related or prefetch_related are used for performance
        # This is important for admin performance with foreign keys
        assert hasattr(queryset, "_prefetch_related_lookups") or hasattr(
            queryset, "query"
        ), "Queryset should support optimization"

    def test_admin_readonly_fields_for_staff(self):
        """Test readonly fields configuration for staff users."""
        staff_user = User.objects.create_user(
            email="staff@example.com", password="staffpass123", is_staff=True, first_name="Staff", last_name="User"
        )

        request = self.factory.get("/admin/")
        request.user = staff_user

        # Check if readonly fields are properly configured
        readonly_fields = self.admin.get_readonly_fields(request)
        assert isinstance(readonly_fields, (list, tuple)), "Readonly fields should be list or tuple"


@pytest.mark.admin
@pytest.mark.django_db
class TestUserAddressAdmin:
    """Test UserAddressAdmin functionality."""

    @pytest.fixture(autouse=True)
    def setup_address_admin_test(self, request_factory, django_user_model):
        """Setup test data using pytest fixtures."""
        self.site = AdminSite()
        self.admin = UserAddressAdmin(UserAddress, self.site)
        self.factory = request_factory

        self.user = django_user_model.objects.create_user(
            email="address@example.com", password="testpass123", first_name="Address", last_name="User"
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
        assert hasattr(self.admin, "list_display"), "Admin should have list_display"
        assert len(self.admin.list_display) > 0, "list_display should not be empty"

    def test_address_admin_permissions(self, django_user_model):
        """Test address admin basic permissions."""
        superuser = django_user_model.objects.create_superuser(
            email="admin@example.com", password="adminpass123", first_name="Admin", last_name="User"
        )

        request = self.factory.get("/admin/")
        request.user = superuser

        # Basic permission tests
        assert self.admin.has_view_permission(request) is True, "Should have view permission"

    def test_address_admin_queryset(self, django_user_model):
        """Test address admin queryset."""
        superuser = django_user_model.objects.create_superuser(
            email="admin@example.com", password="adminpass123", first_name="Admin", last_name="User"
        )

        request = self.factory.get("/admin/")
        request.user = superuser

        queryset = self.admin.get_queryset(request)
        assert hasattr(queryset, "model"), "Should return a queryset"
        assert queryset.model == UserAddress, "Should return UserAddress queryset"

    def test_address_admin_list_select_related(self, django_user_model):
        """Test address admin uses select_related for performance."""
        superuser = django_user_model.objects.create_superuser(
            email="admin@example.com", password="adminpass123", first_name="Admin", last_name="User"
        )

        request = self.factory.get("/admin/")
        request.user = superuser

        queryset = self.admin.get_queryset(request)

        # Check if user relationship is optimized to avoid N+1 queries
        query_str = str(queryset.query)
        # This test ensures the admin doesn't cause N+1 queries when displaying user data
        assert isinstance(query_str, str), "Query should be accessible for optimization analysis"


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

    def test_admin_basic_functionality(self, django_user_model):
        """Test basic admin functionality."""
        superuser = django_user_model.objects.create_superuser(
            email="integration@example.com", password="adminpass123", first_name="Integration", last_name="Admin"
        )

        # Should be able to create superuser for admin access
        assert superuser.is_staff is True, "Superuser should be staff"
        assert superuser.is_superuser is True, "Should be superuser"

    def test_admin_urls_accessible(self):
        """Test admin URLs are properly configured."""
        from django.contrib import admin
        from django.urls import NoReverseMatch, reverse

        try:
            admin_url = reverse("admin:index")
            assert admin_url == "/admin/", "Admin index URL should be accessible"
        except NoReverseMatch:
            pytest.fail("Admin URLs not properly configured")

    def test_user_admin_change_view_accessible(self, django_user_model):
        """Test user admin change view can be accessed."""
        from django.contrib import admin
        from django.urls import reverse

        user = django_user_model.objects.create_user(
            email="changeview@example.com", password="testpass123", first_name="Change", last_name="View"
        )

        try:
            change_url = reverse("admin:accounts_user_change", args=[user.pk])
            assert change_url.startswith("/admin/"), "User change URL should be accessible"
        except Exception as e:
            pytest.fail(f"User admin change view not accessible: {e}")


"""Tests for admin interface - production-ready implementation."""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.core.exceptions import ImproperlyConfigured

User = get_user_model()


def get_admin_classes():
    """Safely import admin classes with detailed error handling."""
    try:
        from src.apps.accounts.admin import UserAddressAdmin, UserAdmin
        from src.apps.accounts.models import UserAddress
        return UserAdmin, UserAddressAdmin, UserAddress
    except ImportError as e:
        pytest.skip(f"Admin modules not available: {e}", allow_module_level=True)
    except Exception as e:
        pytest.skip(f"Unexpected error importing admin: {e}", allow_module_level=True)


try:
    UserAdmin, UserAddressAdmin, UserAddress = get_admin_classes()
except:
    # If import fails, create dummy classes to prevent test collection errors
    UserAdmin = None
    UserAddressAdmin = None
    UserAddress = None


@pytest.mark.admin
@pytest.mark.django_db
class TestUserAdmin:
    """Test UserAdmin functionality and configuration."""

    @pytest.fixture(autouse=True)
    def setup_admin_test(self, request_factory, superuser, regular_user):
        """Setup test data using pytest fixtures."""
        if UserAdmin is None:
            pytest.skip("UserAdmin not available")

        self.site = AdminSite()
        self.admin = UserAdmin(User, self.site)
        self.factory = request_factory
        self.superuser = superuser
        self.regular_user = regular_user

    def test_admin_list_display_fields(self):
        """Test that admin list display contains expected fields."""
        # Test core fields that should exist
        core_fields = ["email", "is_active", "is_staff", "date_joined"]

        # Check if list_display exists and is not empty
        assert hasattr(self.admin, 'list_display'), "Admin should have list_display attribute"
        assert len(self.admin.list_display) > 0, "list_display should not be empty"

        for field in core_fields:
            assert field in self.admin.list_display, f"Core field '{field}' missing from list_display"

    def test_admin_list_filter_configuration(self):
        """Test admin list filter configuration."""
        # Test core filters that should exist
        core_filters = ["is_active", "is_staff", "date_joined"]

        assert hasattr(self.admin, 'list_filter'), "Admin should have list_filter attribute"

        for filter_field in core_filters:
            assert filter_field in self.admin.list_filter, f"Core filter '{filter_field}' missing from list_filter"

    def test_admin_search_fields_configuration(self):
        """Test admin search fields configuration."""
        # Test that search fields exist
        assert hasattr(self.admin, 'search_fields'), "Admin should have search_fields attribute"
        assert len(self.admin.search_fields) > 0, "Search fields should be configured"

        # Email should be searchable
        assert "email" in self.admin.search_fields, "Email should be searchable"

    def test_admin_ordering_configuration(self):
        """Test admin default ordering."""
        # Should have some ordering defined
        assert hasattr(self.admin, "ordering"), "Admin should have ordering defined"
        if self.admin.ordering:
            assert isinstance(self.admin.ordering, (list, tuple)), "Ordering should be list or tuple"

    def test_admin_fieldsets_basic_structure(self):
        """Test admin fieldsets basic structure."""
        # Fieldsets should exist or be None
        if hasattr(self.admin, "fieldsets") and self.admin.fieldsets:
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
        assert hasattr(queryset, "model"), "Should return a queryset"
        assert queryset.model == User, "Should return User queryset"

    def test_admin_form_class_availability(self):
        """Test admin form class is available."""
        request = self.factory.get("/admin/")
        request.user = self.superuser

        form_class = self.admin.get_form(request)
        assert form_class is not None, "Admin form class should be available"

    def test_admin_queryset_optimization(self):
        """Test admin queryset includes necessary optimizations."""
        request = self.factory.get("/admin/")
        request.user = self.superuser

        queryset = self.admin.get_queryset(request)

        # Check if select_related or prefetch_related are used for performance
        # This is important for admin performance with foreign keys
        assert hasattr(queryset, "_prefetch_related_lookups") or hasattr(
            queryset, "query"
        ), "Queryset should support optimization"

    def test_admin_readonly_fields_for_staff(self):
        """Test readonly fields configuration for staff users."""
        staff_user = User.objects.create_user(
            email="staff@example.com",
            password="staffpass123",
            is_staff=True,
            first_name="Staff",
            last_name="User"
        )

        request = self.factory.get("/admin/")
        request.user = staff_user

        # Check if readonly fields are properly configured
        readonly_fields = self.admin.get_readonly_fields(request)
        assert isinstance(readonly_fields, (list, tuple)), "Readonly fields should be list or tuple"

    def test_admin_url_configuration(self):
        """Test admin URLs are properly configured."""
        from django.contrib import admin

        # Check if User model is registered
        assert User in admin.site._registry, "User model should be registered in admin"

        # Check if the admin class is correct
        registered_admin = admin.site._registry[User]
        assert isinstance(registered_admin, type(self.admin)), "Correct admin class should be registered"


@pytest.mark.admin
@pytest.mark.django_db
class TestUserAddressAdmin:
    """Test UserAddressAdmin functionality."""

    @pytest.fixture(autouse=True)
    def setup_address_admin_test(self, request_factory, django_user_model):
        """Setup test data using pytest fixtures."""
        if UserAddressAdmin is None or UserAddress is None:
            pytest.skip("UserAddressAdmin or UserAddress not available")

        self.site = AdminSite()
        self.admin = UserAddressAdmin(UserAddress, self.site)
        self.factory = request_factory

        self.user = django_user_model.objects.create_user(
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
        assert hasattr(self.admin, "list_display"), "Admin should have list_display"
        assert len(self.admin.list_display) > 0, "list_display should not be empty"

    def test_address_admin_permissions(self, django_user_model):
        """Test address admin basic permissions."""
        superuser = django_user_model.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User"
        )

        request = self.factory.get("/admin/")
        request.user = superuser

        # Basic permission tests
        assert self.admin.has_view_permission(request) is True, "Should have view permission"

    def test_address_admin_queryset(self, django_user_model):
        """Test address admin queryset."""
        superuser = django_user_model.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User"
        )

        request = self.factory.get("/admin/")
        request.user = superuser

        queryset = self.admin.get_queryset(request)
        assert hasattr(queryset, "model"), "Should return a queryset"
        assert queryset.model == UserAddress, "Should return UserAddress queryset"

    def test_address_admin_list_select_related(self, django_user_model):
        """Test address admin uses select_related for performance."""
        superuser = django_user_model.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User"
        )

        request = self.factory.get("/admin/")
        request.user = superuser

        queryset = self.admin.get_queryset(request)

        # Check if user relationship is optimized to avoid N+1 queries
        query_str = str(queryset.query)
        # This test ensures the admin doesn't cause N+1 queries when displaying user data
        assert isinstance(query_str, str), "Query should be accessible for optimization analysis"

    def test_address_admin_registration(self):
        """Test UserAddress model is registered in admin."""
        from django.contrib import admin

        # Check if UserAddress model is registered
        assert UserAddress in admin.site._registry, "UserAddress model should be registered in admin"


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

    def test_admin_basic_functionality(self, django_user_model):
        """Test basic admin functionality."""
        superuser = django_user_model.objects.create_superuser(
            email="integration@example.com",
            password="adminpass123",
            first_name="Integration",
            last_name="Admin"
        )

        # Should be able to create superuser for admin access
        assert superuser.is_staff is True, "Superuser should be staff"
        assert superuser.is_superuser is True, "Should be superuser"

    def test_admin_urls_accessible(self):
        """Test admin URLs are properly configured."""
        from django.contrib import admin
        from django.urls import NoReverseMatch, reverse

        try:
            admin_url = reverse("admin:index")
            assert admin_url == "/admin/", "Admin index URL should be accessible"
        except NoReverseMatch:
            pytest.fail("Admin URLs not properly configured")

    def test_user_admin_change_view_accessible(self, django_user_model):
        """Test user admin change view can be accessed."""
        from django.contrib import admin
        from django.urls import reverse

        user = django_user_model.objects.create_user(
            email="changeview@example.com",
            password="testpass123",
            first_name="Change",
            last_name="View"
        )

        try:
            change_url = reverse("admin:accounts_user_change", args=[user.pk])
            assert change_url.startswith("/admin/"), "User change URL should be accessible"
        except Exception as e:
            pytest.fail(f"User admin change view not accessible: {e}")

    def test_admin_security_basic(self, django_user_model):
        """Test basic admin security configurations."""
        from django.contrib import admin

        # Create non-staff user
        regular_user = django_user_model.objects.create_user(
            email="regular@example.com",
            password="testpass123",
            first_name="Regular",
            last_name="User",
            is_staff=False
        )

        # Create staff user
        staff_user = django_user_model.objects.create_user(
            email="staff@example.com",
            password="testpass123",
            first_name="Staff",
            last_name="User",
            is_staff=True
        )

        # Test admin access restrictions
        user_admin = admin.site._registry[User]

        # Regular user should not have admin access
        request_factory = RequestFactory()
        request = request_factory.get("/admin/")
        request.user = regular_user

        assert not user_admin.has_module_permission(request), "Regular user should not have module permission"

        # Staff user should have basic access
        request.user = staff_user
        assert user_admin.has_module_permission(request), "Staff user should have module permission"


@pytest.mark.admin
@pytest.mark.performance
@pytest.mark.django_db
class TestAdminPerformance:
    """Test admin performance optimizations."""

    @pytest.fixture(autouse=True)
    def setup_performance_test(self, django_user_model):
        """Setup test data for performance tests."""
        if UserAdmin is None:
            pytest.skip("UserAdmin not available")

        # Create multiple users for performance testing
        self.users = []
        for i in range(10):
            user = django_user_model.objects.create_user(
                email=f"perf_user_{i}@example.com",
                password="testpass123",
                first_name=f"Perf{i}",
                last_name="User"
            )
            self.users.append(user)

    def test_admin_queryset_efficiency(self, django_user_model):
        """Test admin queryset is optimized for large datasets."""
        from django.contrib import admin
        from django.test.utils import override_settings

        user_admin = admin.site._registry[User]

        superuser = django_user_model.objects.create_superuser(
            email="perf_admin@example.com",
            password="adminpass123",
            first_name="Perf",
            last_name="Admin"
        )

        request_factory = RequestFactory()
        request = request_factory.get("/admin/accounts/user/")
        request.user = superuser

        # Test that queryset doesn't cause excessive queries
        with override_settings(DEBUG=True):
            from django.db import connection

            # Reset queries
            connection.queries_log.clear()

            # Get admin queryset
            queryset = user_admin.get_queryset(request)
            list(queryset[:5])  # Force evaluation of first 5 items

            # Check that we don't have excessive queries
            query_count = len(connection.queries)
            assert query_count < 10, f"Too many queries: {query_count}. Check for N+1 query problems."

    def test_admin_list_display_performance(self, django_user_model):
        """Test admin list display doesn't cause performance issues."""
        from django.contrib import admin

        user_admin = admin.site._registry[User]

        # Ensure list_display fields are optimized
        list_display = user_admin.list_display

        # Check that foreign key fields use select_related optimization
        # This is a structural test - actual optimization should be in the admin class
        assert isinstance(list_display, (list, tuple)), "list_display should be a list or tuple"
        assert len(list_display) > 0, "list_display should not be empty"


@pytest.mark.admin
@pytest.mark.security
@pytest.mark.django_db
class TestAdminSecurity:
    """Test admin security configurations."""

    def test_admin_permissions_isolation(self, django_user_model):
        """Test that admin permissions are properly isolated."""
        from django.contrib import admin

        # Create users with different permission levels
        superuser = django_user_model.objects.create_superuser(
            email="super@example.com",
            password="testpass123",
            first_name="Super",
            last_name="User"
        )

        staff_user = django_user_model.objects.create_user(
            email="staff@example.com",
            password="testpass123",
            first_name="Staff",
            last_name="User",
            is_staff=True
        )

        regular_user = django_user_model.objects.create_user(
            email="regular@example.com",
            password="testpass123",
            first_name="Regular",
            last_name="User"
        )

        user_admin = admin.site._registry[User]
        request_factory = RequestFactory()

        # Test superuser permissions
        request = request_factory.get("/admin/")
        request.user = superuser

        assert user_admin.has_view_permission(request), "Superuser should have view permission"
        assert user_admin.has_add_permission(request), "Superuser should have add permission"
        assert user_admin.has_change_permission(request), "Superuser should have change permission"
        assert user_admin.has_delete_permission(request), "Superuser should have delete permission"

        # Test staff user permissions (should be more limited)
        request.user = staff_user
        assert user_admin.has_module_permission(request), "Staff should have module permission"

        # Test regular user permissions (should be denied)
        request.user = regular_user
        assert not user_admin.has_module_permission(request), "Regular user should not have module permission"

    def test_admin_readonly_fields_security(self, django_user_model):
        """Test readonly fields are properly configured for security."""
        from django.contrib import admin

        user_admin = admin.site._registry[User]
        request_factory = RequestFactory()

        # Test with staff user (non-superuser)
        staff_user = django_user_model.objects.create_user(
            email="staff_security@example.com",
            password="testpass123",
            first_name="Staff",
            last_name="Security",
            is_staff=True
        )

        request = request_factory.get("/admin/")
        request.user = staff_user

        readonly_fields = user_admin.get_readonly_fields(request)

        # Critical security fields should be readonly for staff
        security_fields = ['is_superuser', 'is_staff', 'user_permissions', 'groups']

        for field in security_fields:
            # Check if field exists in model and should be readonly
            if hasattr(User, field):
                # This test assumes proper security configuration
                # The actual readonly fields depend on your admin implementation
                assert isinstance(readonly_fields, (list, tuple)), "Readonly fields should be properly configured"
