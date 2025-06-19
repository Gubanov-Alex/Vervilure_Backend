from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import BlacklistedToken, User, UserAddress


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Enhanced admin interface for a User model.

    Provides comprehensive user management with custom fields and actions.
    """

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal info"),
            {"fields": ("first_name", "last_name", "phone_number", "date_of_birth", "avatar_preview", "avatar")},
        ),
        (_("Account Settings"), {"fields": ("is_email_verified", "marketing_consent", "newsletter_subscription")}),
        (
            _("Permissions"),
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Important dates"),
            {"fields": ("last_login", "date_joined", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
        (_("Security"), {"fields": ("last_login_ip", "email_verification_token"), "classes": ("collapse",)}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2", "is_email_verified"),
            },
        ),
    )

    list_display = [
        "email",
        "full_name",
        "is_active",
        "is_email_verified",
        "is_staff",
        "date_joined",
        "last_login",
        # "orders_count",
    ]

    list_filter = [
        "is_active",
        "is_staff",
        "is_superuser",
        "is_email_verified",
        "marketing_consent",
        "newsletter_subscription",
        "date_joined",
    ]

    search_fields = ["email", "first_name", "last_name", "phone_number"]
    ordering = ["-date_joined"]
    readonly_fields = [
        "date_joined",
        "last_login",
        "created_at",
        "updated_at",
        "email_verification_token",
        "avatar_preview",
        # "orders_count",
    ]

    actions = ["verify_email", "send_verification_email", "deactivate_users"]

    def avatar_preview(self, obj):
        """Display avatar preview in admin."""
        if obj.avatar:
            return mark_safe(f'<img src="{obj.avatar.url}" width="50" height="50" ' f'style="border-radius: 50%;" />')
        return "No avatar"

    avatar_preview.short_description = "Avatar Preview"

    # def orders_count(self, obj):
    #     """Display count of user orders with link."""
    #     count = obj.orders.count()
    #     if count > 0:
    #         url = reverse("admin:orders_order_changelist") + f"?user__id__exact={obj.id}"
    #         return format_html('<a href="{}">{} orders</a>', url, count)
    #     return "0 orders"
    #
    # orders_count.short_description = "Orders"

    def verify_email(self, request, queryset):
        """Admin action to verify user emails."""
        updated = queryset.update(is_email_verified=True)
        self.message_user(request, f"Successfully verified {updated} user(s).")

    verify_email.short_description = "Verify selected users' emails"

    def send_verification_email(self, request, queryset):
        """Admin action to send verification emails."""
        from .tasks import send_verification_email

        count = 0
        for user in queryset.filter(is_email_verified=False):
            send_verification_email.delay(user.id)
            count += 1

        self.message_user(request, f"Verification emails queued for {count} user(s).")

    send_verification_email.short_description = "Send verification emails"

    def deactivate_users(self, request, queryset):
        """Admin action to deactivate users."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Successfully deactivated {updated} user(s).")

    deactivate_users.short_description = "Deactivate selected users"


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
