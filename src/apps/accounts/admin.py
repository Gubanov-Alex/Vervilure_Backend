from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import BlacklistedToken, User, UserAddress


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced admin interface for User model with deletion tracking."""

    # Display configuration
    list_display = [
        "email",
        "full_name",
        "is_email_verified",
        "is_active",
        "is_anonymized_status",
        "deactivation_status",
        "created_at",
        "last_login",
    ]

    list_filter = [
        "is_active",
        "is_staff",
        "is_superuser",
        "is_email_verified",
        "is_anonymized",
        "deactivated_at",
        "created_at",
        "marketing_consent",
        "newsletter_subscription",
    ]

    search_fields = [
        "email",
        "first_name",
        "last_name",
        "phone_number",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "last_login",
        "email_verification_token",
        "google_id",
        "deactivated_at",
        "anonymized_at",
    ]

    # Fieldsets for detailed view
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone_number",
                    "date_of_birth",
                    "avatar",
                )
            },
        ),
        (
            _("Account Status"),
            {
                "fields": (
                    "is_active",
                    "is_email_verified",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        (
            _("Account Deletion/Anonymization"),
            {
                "fields": (
                    "deactivated_at",
                    "deactivation_reason",
                    "is_anonymized",
                    "anonymized_at",
                ),
                "classes": ("collapse",),
                "description": "Fields related to account deletion and anonymization processes.",
            },
        ),
        (
            _("Email Verification"),
            {
                "fields": (
                    "email_verification_token",
                    "email_verification_sent_at",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Marketing Preferences"),
            {
                "fields": (
                    "marketing_consent",
                    "newsletter_subscription",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Metadata"),
            {
                "fields": (
                    "google_id",
                    "last_login_ip",
                    "created_at",
                    "updated_at",
                    "last_login",
                ),
                "classes": ("collapse",),
            },
        ),
        (_("Permissions"), {"fields": ("groups", "user_permissions"), "classes": ("collapse",)}),
    )

    # Add fieldsets for new user creation
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "is_email_verified",
                ),
            },
        ),
    )

    # Custom ordering
    ordering = ["-created_at"]

    # Custom methods for list display
    def full_name(self, obj):
        """Display full name with anonymization status."""
        if obj.is_anonymized:
            return format_html('<span style="color: #999; font-style: italic;">Anonymized User</span>')
        return obj.get_full_name()

    full_name.short_description = "Full Name"

    def is_anonymized_status(self, obj):
        """Display anonymization status with visual indicator."""
        if obj.is_anonymized:
            return format_html('<span style="color: #d63384; font-weight: bold;">🔒 Anonymized</span>')
        return format_html('<span style="color: #198754;">📝 Active</span>')

    is_anonymized_status.short_description = "Data Status"

    def deactivation_status(self, obj):
        """Display deactivation status with reactivation info."""
        if obj.deactivated_at:
            if obj.can_reactivate():
                deadline = obj.get_reactivation_deadline()
                return format_html(
                    '<span style="color: #fd7e14;">⏸️ Deactivated<br>' "<small>Can reactivate until {}</small></span>",
                    deadline.strftime("%Y-%m-%d") if deadline else "N/A",
                )
            else:
                return format_html(
                    '<span style="color: #dc3545;">❌ Expired<br>' "<small>Cannot reactivate</small></span>"
                )
        elif not obj.is_active:
            return format_html('<span style="color: #6c757d;">⏸️ Inactive</span>')
        else:
            return format_html('<span style="color: #198754;">✅ Active</span>')

    deactivation_status.short_description = "Account Status"

    # Custom actions
    def reactivate_users(self, request, queryset):
        """Admin action to reactivate eligible users."""
        count = 0
        for user in queryset:
            if user.deactivated_at and user.can_reactivate() and not user.is_anonymized:
                user.is_active = True
                user.deactivated_at = None
                user.deactivation_reason = ""
                user.save()
                count += 1

        if count:
            self.message_user(request, f"Successfully reactivated {count} user(s).")
        else:
            self.message_user(request, "No eligible users found for reactivation.", level="warning")

    reactivate_users.short_description = "Reactivate selected deactivated users"

    def anonymize_expired_users(self, request, queryset):
        """Admin action to anonymize users with expired deactivation period."""
        count = 0
        for user in queryset:
            if user.deactivated_at and not user.can_reactivate() and not user.is_anonymized:
                anonymous_id = user.anonymize_user_data()
                count += 1

        if count:
            self.message_user(request, f"Successfully anonymized {count} expired user(s).")
        else:
            self.message_user(request, "No eligible users found for anonymization.", level="warning")

    anonymize_expired_users.short_description = "Anonymize users with expired deactivation"

    actions = ["reactivate_users", "anonymize_expired_users"]

    # Restrict permissions for non-superusers
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if not request.user.is_superuser:
            readonly.extend(
                [
                    "is_staff",
                    "is_superuser",
                    "user_permissions",
                    "groups",
                    "is_anonymized",
                    "deactivation_reason",
                ]
            )
        return readonly

    def has_delete_permission(self, request, obj=None):
        """Restrict deletion to superusers only."""
        return request.user.is_superuser

    # Custom queryset optimization
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related()


class UserAddressInline(admin.TabularInline):
    """Inline admin for user addresses."""

    model = UserAddress
    extra = 0
    fields = ["address_type", "first_name", "last_name", "address_line1", "city", "country", "is_default"]


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    """Admin interface for user addresses."""

    list_display = ["user", "address_type", "full_name", "city", "country", "is_default", "created_at"]

    list_filter = ["address_type", "country", "is_default", "created_at"]
    search_fields = ["user__email", "first_name", "last_name", "city", "address_line1"]

    readonly_fields = ["created_at", "updated_at"]

    def full_name(self, obj):
        """Display full name."""
        return f"{obj.first_name} {obj.last_name}"

    full_name.short_description = "Full Name"


@admin.register(BlacklistedToken)
class BlacklistedTokenAdmin(admin.ModelAdmin):
    """Admin interface for blacklisted tokens."""

    list_display = ["token_jti_short", "user", "blacklisted_at", "expires_at", "is_expired"]

    list_filter = ["blacklisted_at", "expires_at"]
    search_fields = ["user__email", "token_jti"]
    readonly_fields = ["token_jti", "user", "blacklisted_at", "expires_at"]

    def token_jti_short(self, obj):
        """Display shortened JTI for readability."""
        return f"{obj.token_jti[:8]}...{obj.token_jti[-8:]}"

    token_jti_short.short_description = "Token JTI"

    def is_expired(self, obj):
        """Check if token is expired."""
        from django.utils import timezone

        return obj.expires_at < timezone.now()

    is_expired.boolean = True
    is_expired.short_description = "Expired"

    def has_add_permission(self, request):
        """Disable manual token creation."""
        return False
