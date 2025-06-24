import csv
import logging

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from .models import BlacklistedToken, User, UserAddress
from .tasks import send_verification_email

logger = logging.getLogger(__name__)


class CreatedAtRangeFilter(admin.SimpleListFilter):
    """Custom filter for created_at field with predefined ranges."""

    title = _("Registration Period")
    parameter_name = "created_period"

    def lookups(self, request, model_admin):
        return (
            ("today", _("Today")),
            ("week", _("This Week")),
            ("month", _("This Month")),
            ("3months", _("Last 3 Months")),
            ("year", _("This Year")),
        )

    def queryset(self, request, queryset):
        if self.value() == "today":
            return queryset.filter(created_at__date=timezone.now().date())
        elif self.value() == "week":
            start_date = timezone.now() - timezone.timedelta(days=7)
            return queryset.filter(created_at__gte=start_date)
        elif self.value() == "month":
            start_date = timezone.now() - timezone.timedelta(days=30)
            return queryset.filter(created_at__gte=start_date)
        elif self.value() == "3months":
            start_date = timezone.now() - timezone.timedelta(days=90)
            return queryset.filter(created_at__gte=start_date)
        elif self.value() == "year":
            start_date = timezone.now() - timezone.timedelta(days=365)
            return queryset.filter(created_at__gte=start_date)
        return queryset


class LastLoginRangeFilter(admin.SimpleListFilter):
    """Custom filter for last_login field."""

    title = _("Last Activity")
    parameter_name = "last_activity"

    def lookups(self, request, model_admin):
        return (
            ("today", _("Active Today")),
            ("week", _("Active This Week")),
            ("month", _("Active This Month")),
            ("inactive_30", _("Inactive 30+ days")),
            ("never", _("Never Logged In")),
        )

    def queryset(self, request, queryset):
        if self.value() == "today":
            return queryset.filter(last_login__date=timezone.now().date())
        elif self.value() == "week":
            start_date = timezone.now() - timezone.timedelta(days=7)
            return queryset.filter(last_login__gte=start_date)
        elif self.value() == "month":
            start_date = timezone.now() - timezone.timedelta(days=30)
            return queryset.filter(last_login__gte=start_date)
        elif self.value() == "inactive_30":
            end_date = timezone.now() - timezone.timedelta(days=30)
            return queryset.filter(last_login__lt=end_date)
        elif self.value() == "never":
            return queryset.filter(last_login__isnull=True)
        return queryset


class CountryGroupFilter(admin.SimpleListFilter):
    """Custom filter for grouping addresses by country regions."""

    title = _("Country Region")
    parameter_name = "country_region"

    def lookups(self, request, model_admin):
        return (
            ("eu", _("European Union")),
            ("na", _("North America")),
            ("asia", _("Asia")),
            ("other", _("Other Regions")),
        )

    def queryset(self, request, queryset):
        eu_countries = ["Germany", "France", "Italy", "Spain", "Netherlands", "Poland", "Belgium"]
        na_countries = ["United States", "Canada", "Mexico"]
        asia_countries = ["China", "Japan", "South Korea", "India", "Singapore"]

        if self.value() == "eu":
            return queryset.filter(country__in=eu_countries)
        elif self.value() == "na":
            return queryset.filter(country__in=na_countries)
        elif self.value() == "asia":
            return queryset.filter(country__in=asia_countries)
        elif self.value() == "other":
            all_major = eu_countries + na_countries + asia_countries
            return queryset.exclude(country__in=all_major)
        return queryset


class ExpiredTokenFilter(admin.SimpleListFilter):
    """Custom filter for expired tokens."""

    title = _("Token Status")
    parameter_name = "token_status"

    def lookups(self, request, model_admin):
        return (
            ("active", _("Active")),
            ("expired", _("Expired")),
            ("expires_soon", _("Expires in 7 days")),
        )

    def queryset(self, request, queryset):
        now = timezone.now()

        if self.value() == "active":
            return queryset.filter(expires_at__gte=now)
        elif self.value() == "expired":
            return queryset.filter(expires_at__lt=now)
        elif self.value() == "expires_soon":
            soon = now + timezone.timedelta(days=7)
            return queryset.filter(expires_at__gte=now, expires_at__lte=soon)
        return queryset


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced admin interface for User model with deletion tracking."""

    # Display configuration
    list_display = [
        "email",
        "full_name",
        "is_email_verified_colored",
        "is_active",
        "is_anonymized_status",
        "deactivation_status",
        "user_activity_indicator",
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
        CreatedAtRangeFilter,
        LastLoginRangeFilter,
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
        "user_stats_display",
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
            _("User Statistics"),
            {
                "fields": ("user_stats_display",),
                "classes": ("collapse",),
                "description": "User activity and engagement statistics.",
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

    def is_email_verified_colored(self, obj):
        """Display email verification status with color indicators."""
        if obj.is_email_verified:
            return format_html('<span style="color: #198754; font-weight: bold;">✅ Verified</span>')
        else:
            return format_html('<span style="color: #dc3545; font-weight: bold;">❌ Unverified</span>')

    is_email_verified_colored.short_description = "Email Status"
    is_email_verified_colored.admin_order_field = "is_email_verified"

    def user_activity_indicator(self, obj):
        """Display user activity level indicator."""
        if not obj.last_login:
            return format_html('<span style="color: #6c757d;">👤 Never</span>')

        days_since_login = (timezone.now() - obj.last_login).days

        if days_since_login == 0:
            return format_html('<span style="color: #198754;">🟢 Today</span>')
        elif days_since_login <= 7:
            return format_html('<span style="color: #28a745;">🟡 This Week</span>')
        elif days_since_login <= 30:
            return format_html('<span style="color: #fd7e14;">🟠 This Month</span>')
        else:
            return format_html('<span style="color: #dc3545;">🔴 Inactive</span>')

    user_activity_indicator.short_description = "Activity"
    user_activity_indicator.admin_order_field = "last_login"

    def user_stats_display(self, obj):
        """Display user statistics in readonly field."""
        if obj.pk:
            addresses_count = obj.addresses.count()
            blacklisted_tokens = obj.blacklisted_tokens.count()

            stats_html = f"""
            <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
                <h4 style="margin: 0 0 10px 0;">User Statistics</h4>
                <ul style="margin: 0; padding-left: 20px;">
                    <li><strong>Addresses:</strong> {addresses_count}</li>
                    <li><strong>Blacklisted Tokens:</strong> {blacklisted_tokens}</li>
                    <li><strong>Account Age:</strong> {(timezone.now() - obj.created_at).days} days</li>
                </ul>
            </div>
            """
            return format_html(stats_html)
        return "Save user to view statistics"

    user_stats_display.short_description = "Statistics"

    # Existing custom methods (unchanged)
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

    def export_users_csv(self, request, queryset):
        """Export selected users to CSV."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="users_export.csv"'

        writer = csv.writer(response)
        writer.writerow(["Email", "First Name", "Last Name", "Is Active", "Email Verified", "Created At", "Last Login"])

        for user in queryset:
            writer.writerow(
                [
                    user.email,
                    user.first_name,
                    user.last_name,
                    user.is_active,
                    user.is_email_verified,
                    user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    user.last_login.strftime("%Y-%m-%d %H:%M:%S") if user.last_login else "Never",
                ]
            )

        return response

    export_users_csv.short_description = "📊 Export selected users to CSV"

    # Existing actions + new export action
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

    def verify_email_action(self, request, queryset):
        """
        Admin action to mark email as verified for selected users.

        Features:
        - Atomic transaction for data consistency
        - Skip already verified users
        - Activate users upon verification
        - Comprehensive logging
        """
        updated_count = 0
        already_verified_count = 0
        error_count = 0

        try:
            with transaction.atomic():
                for user in queryset.select_for_update():
                    try:
                        if user.is_email_verified:
                            already_verified_count += 1
                            continue

                        # Update verification status and activate user
                        user.is_email_verified = True
                        user.is_active = True
                        user.save(update_fields=["is_email_verified", "is_active"])

                        updated_count += 1

                        logger.info(
                            f"Email manually verified by admin: {user.email}",
                            extra={
                                "user_id": user.id,
                                "admin_user": request.user.email,
                                "action": "manual_verify_email",
                                "ip_address": request.META.get("REMOTE_ADDR", "unknown"),
                            },
                        )

                    except Exception as e:
                        error_count += 1
                        logger.error(
                            f"Failed to verify email for user {user.email}: {e}",
                            extra={"user_id": user.id, "admin_user": request.user.email, "error": str(e)},
                        )

            # Provide user feedback
            if updated_count > 0:
                messages.success(
                    request,
                    ngettext(
                        "Successfully verified email for %d user.",
                        "Successfully verified emails for %d users.",
                        updated_count,
                    )
                    % updated_count,
                )

            if already_verified_count > 0:
                messages.info(
                    request,
                    ngettext("%d user was already verified.", "%d users were already verified.", already_verified_count)
                    % already_verified_count,
                )

            if error_count > 0:
                messages.warning(
                    request,
                    ngettext(
                        "Failed to verify %d user. Check logs for details.",
                        "Failed to verify %d users. Check logs for details.",
                        error_count,
                    )
                    % error_count,
                )

        except Exception as e:
            messages.error(request, f"Critical error during email verification: {e}")
            logger.error(
                f"Admin verify email action failed: {e}", extra={"admin_user": request.user.email, "error": str(e)}
            )

    verify_email_action.short_description = "✅ Verify email for selected users"

    def send_verification_email_action(self, request, queryset):
        """
        Admin action to send verification emails to selected users via Celery.

        Features:
        - Asynchronous email sending via existing Celery task
        - Skip already verified users
        - Skip users without email addresses
        - Comprehensive logging and feedback
        """
        sent_count = 0
        already_verified_count = 0
        skipped_count = 0
        error_count = 0

        try:
            for user in queryset:
                try:
                    # Skip already verified users
                    if user.is_email_verified:
                        already_verified_count += 1
                        continue

                    # Skip users without email
                    if not user.email:
                        skipped_count += 1
                        continue

                    # Queue email sending task using your existing Celery task
                    send_verification_email.delay(user.id)
                    sent_count += 1

                    logger.info(
                        f"Verification email queued by admin: {user.email}",
                        extra={
                            "user_id": user.id,
                            "admin_user": request.user.email,
                            "action": "admin_send_verification",
                            "ip_address": request.META.get("REMOTE_ADDR", "unknown"),
                        },
                    )

                except Exception as e:
                    error_count += 1
                    logger.error(
                        f"Failed to queue verification email for {user.email}: {e}",
                        extra={"user_id": user.id, "admin_user": request.user.email, "error": str(e)},
                    )

            # Provide user feedback
            if sent_count > 0:
                messages.success(
                    request,
                    ngettext(
                        "Verification email queued for %d user.", "Verification emails queued for %d users.", sent_count
                    )
                    % sent_count,
                )

            if already_verified_count > 0:
                messages.info(
                    request,
                    ngettext(
                        "%d user already has verified email.",
                        "%d users already have verified emails.",
                        already_verified_count,
                    )
                    % already_verified_count,
                )

            if skipped_count > 0:
                messages.warning(
                    request,
                    ngettext(
                        "Skipped %d user (missing email or error).",
                        "Skipped %d users (missing emails or errors).",
                        skipped_count,
                    )
                    % skipped_count,
                )

            if error_count > 0:
                messages.error(
                    request,
                    ngettext(
                        "Failed to queue email for %d user. Check logs for details.",
                        "Failed to queue emails for %d users. Check logs for details.",
                        error_count,
                    )
                    % error_count,
                )

        except Exception as e:
            messages.error(request, f"Critical error during email sending: {e}")
            logger.error(
                f"Admin send verification action failed: {e}", extra={"admin_user": request.user.email, "error": str(e)}
            )

    send_verification_email_action.short_description = "📧 Send verification email to selected users"

    actions = [
        "reactivate_users",
        "anonymize_expired_users",
        "verify_email_action",
        "send_verification_email_action",
        "export_users_csv",
    ]

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

    list_display = [
        "user_email_link",
        "address_type_colored",
        "full_name",
        "address_preview",
        "city",
        "country",
        "is_default_icon",
        "created_at",
    ]

    list_filter = ["address_type", CountryGroupFilter, "country", "is_default", "created_at"]

    search_fields = ["user__email", "first_name", "last_name", "city", "address_line1"]

    readonly_fields = ["created_at", "updated_at"]

    def user_email_link(self, obj):
        """Display user email as clickable link to user admin."""
        from django.urls import reverse
        from django.utils.html import format_html

        url = reverse("admin:accounts_user_change", args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)

    user_email_link.short_description = "User"
    user_email_link.admin_order_field = "user__email"

    def address_type_colored(self, obj):
        """Display address type with color coding."""
        if obj.address_type == "shipping":
            return format_html('<span style="color: #0d6efd; font-weight: bold;">📦 Shipping</span>')
        else:
            return format_html('<span style="color: #198754; font-weight: bold;">💳 Billing</span>')

    address_type_colored.short_description = "Type"
    address_type_colored.admin_order_field = "address_type"

    def address_preview(self, obj):
        """Display short address preview."""
        preview = f"{obj.address_line1}"
        if len(preview) > 30:
            preview = preview[:27] + "..."
        return preview

    address_preview.short_description = "Address"

    def is_default_icon(self, obj):
        """Display default status with icons."""
        if obj.is_default:
            return format_html('<span style="color: #ffc107;">⭐ Default</span>')
        else:
            return format_html('<span style="color: #6c757d;">—</span>')

    is_default_icon.short_description = "Default"
    is_default_icon.admin_order_field = "is_default"

    def full_name(self, obj):
        """Display full name."""
        return f"{obj.first_name} {obj.last_name}"

    full_name.short_description = "Full Name"


@admin.register(BlacklistedToken)
class BlacklistedTokenAdmin(admin.ModelAdmin):
    """Admin interface for blacklisted tokens."""

    list_display = [
        "token_jti_short",
        "user_email_link",
        "blacklisted_at",
        "expires_at",
        "token_status",
        "days_until_expiry",
    ]

    list_filter = [
        "blacklisted_at",
        "expires_at",
        ExpiredTokenFilter,
    ]

    search_fields = ["user__email", "token_jti"]
    readonly_fields = ["token_jti", "user", "blacklisted_at", "expires_at"]

    def user_email_link(self, obj):
        """Display user email as clickable link."""
        from django.urls import reverse
        from django.utils.html import format_html

        url = reverse("admin:accounts_user_change", args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)

    user_email_link.short_description = "User"
    user_email_link.admin_order_field = "user__email"

    def token_status(self, obj):
        """Enhanced token status with visual indicators."""
        if obj.expires_at < timezone.now():
            return format_html('<span style="color: #dc3545;">🔴 Expired</span>')
        else:
            return format_html('<span style="color: #ffc107;">🟡 Active</span>')

    token_status.short_description = "Status"
    token_status.admin_order_field = "expires_at"

    def days_until_expiry(self, obj):
        """Show days until token expiry."""
        if obj.expires_at < timezone.now():
            days_past = (timezone.now() - obj.expires_at).days
            return format_html('<span style="color: #6c757d;">-{} days</span>', days_past)
        else:
            days_left = (obj.expires_at - timezone.now()).days
            if days_left <= 7:
                return format_html('<span style="color: #dc3545;">{} days</span>', days_left)
            else:
                return format_html('<span style="color: #198754;">{} days</span>', days_left)

    days_until_expiry.short_description = "Expires In"

    def token_jti_short(self, obj):
        """Display shortened JTI for readability."""
        return f"{obj.token_jti[:8]}...{obj.token_jti[-8:]}"

    token_jti_short.short_description = "Token JTI"

    def has_add_permission(self, request):
        """Disable manual token creation."""
        return False

    def cleanup_expired_tokens(self, request, queryset):
        """Remove expired tokens."""
        expired_count = queryset.filter(expires_at__lt=timezone.now()).count()
        queryset.filter(expires_at__lt=timezone.now()).delete()

        if expired_count:
            self.message_user(request, f"Successfully removed {expired_count} expired token(s).")
        else:
            self.message_user(request, "No expired tokens found to remove.", level="warning")

    cleanup_expired_tokens.short_description = "🗑️ Remove expired tokens"

    actions = ["cleanup_expired_tokens"]
