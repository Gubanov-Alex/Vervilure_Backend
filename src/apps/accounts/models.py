import uuid
from datetime import timedelta
from typing import Any, Dict, Optional

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def _create_user(self, email, password=None, **extra_fields):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)

        # Auto-generate username from email if not provided
        if "username" not in extra_fields or not extra_fields["username"]:
            base_username = email.split("@")[0]
            username = base_username
            counter = 1
            while self.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            extra_fields["username"] = username

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

    def active_users(self):
        """Return queryset of active users (not deactivated or anonymized)."""
        return self.filter(is_active=True, is_anonymized=False, deactivated_at__isnull=True)

    def deactivated_users(self):
        """Return queryset of deactivated users (including anonymized)."""
        return self.filter(
            models.Q(is_active=False) | models.Q(deactivated_at__isnull=False) | models.Q(is_anonymized=True)
        )

    def anonymized_users(self):
        """Return queryset of anonymized users."""
        return self.filter(is_anonymized=True)

    def users_for_deletion(self, days_threshold: int = 30):
        """Return users eligible for deletion (deactivated more than threshold days ago)."""
        cutoff_date = timezone.now() - timedelta(days=days_threshold)
        return self.filter(is_active=False, deactivated_at__lt=cutoff_date, is_anonymized=False)


class User(AbstractUser):
    """Extended user model with additional fields for e-commerce platform."""

    # Override username to be nullable since we use email authentication
    username = models.CharField(_("username"), max_length=150, unique=True, null=True, blank=True)

    email_verification_token = models.UUIDField(default=uuid.uuid4, unique=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)

    # Personal information - override from AbstractUser to ensure proper settings
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)
    email = models.EmailField(_("email address"), unique=True)

    phone_number = models.CharField(
        _("phone number"),
        max_length=20,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message=_('Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.'),
            )
        ],
        blank=True,
        null=True,
    )

    date_of_birth = models.DateField(_("date of birth"), null=True, blank=True)
    avatar = models.ImageField(_("avatar"), upload_to="avatars/%Y/%m/%d/", null=True, blank=True)

    # Marketing preferences
    marketing_consent = models.BooleanField(_("marketing consent"), default=False)
    newsletter_subscription = models.BooleanField(_("newsletter subscription"), default=False)

    # Account metadata
    last_login_ip = models.GenericIPAddressField(_("last login IP"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    # Google OAuth integration
    google_id = models.CharField(_("Google ID"), max_length=255, unique=True, null=True, blank=True)

    # Account deletion/deactivation fields
    deactivated_at = models.DateTimeField(
        _("deactivated at"), null=True, blank=True, help_text=_("Timestamp when account was deactivated (soft delete)")
    )
    deactivation_reason = models.TextField(
        _("deactivation reason"),
        max_length=500,
        blank=True,
        help_text=_("Reason provided by user for account deactivation"),
    )
    is_anonymized = models.BooleanField(
        _("is anonymized"), default=False, help_text=_("Whether user data has been anonymized")
    )
    anonymized_at = models.DateTimeField(
        _("anonymized at"), null=True, blank=True, help_text=_("Timestamp when account was anonymized")
    )

    # CRITICAL: Assign the custom manager
    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "auth_user"
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_active", "is_email_verified"]),
            models.Index(fields=["google_id"]),
            models.Index(fields=["email_verification_token"]),
            # Indexes for deletion/anonymization fields
            models.Index(
                fields=["deactivated_at"],
                condition=models.Q(deactivated_at__isnull=False),
                name="user_deactivated_at_idx",
            ),
            models.Index(
                fields=["anonymized_at"], condition=models.Q(anonymized_at__isnull=False), name="user_anonymized_at_idx"
            ),
            models.Index(
                fields=["is_anonymized"], condition=models.Q(is_anonymized=True), name="user_is_anonymized_idx"
            ),
            models.Index(fields=["is_active", "deactivated_at"]),
        ]

    def __str__(self) -> str:
        if self.is_anonymized:
            return f"Anonymized User ({self.id})"
        return f"{self.email} ({self.get_full_name()})"

    @property
    def full_name(self) -> str:
        """Return the user's full name."""
        if self.is_anonymized:
            return "Deleted User"
        return f"{self.first_name} {self.last_name}".strip()

    def get_full_name(self) -> str:
        """Return user's full name for Django compatibility."""
        return self.full_name

    def is_verification_token_valid(self) -> bool:
        """Check if the verification token is still valid (24h window)."""
        if not self.email_verification_sent_at:
            return True  # No expiration if never sent

        expiry_time = self.email_verification_sent_at + timedelta(hours=24)
        return timezone.now() <= expiry_time

    def can_reactivate(self) -> bool:
        """Check if account can be reactivated (within 30-day window)."""
        if not self.deactivated_at or self.is_anonymized:
            return False

        reactivation_deadline = self.deactivated_at + timedelta(days=30)
        return timezone.now() <= reactivation_deadline

    def get_reactivation_deadline(self) -> Optional[timezone.datetime]:
        """Get the deadline for account reactivation."""
        if not self.deactivated_at:
            return None
        return self.deactivated_at + timedelta(days=30)

    def soft_delete_user_data(self, reason: str = "") -> None:
        """
        Soft delete user account by deactivating it.

        Args:
            reason: Reason for account deactivation
        """
        self.is_active = False
        self.deactivated_at = timezone.now()
        self.deactivation_reason = reason
        self.save(update_fields=["is_active", "deactivated_at", "deactivation_reason"])

    def anonymize_user_data(self) -> str:
        """
        Anonymize user data while preserving account for statistical purposes.

        Returns:
            Anonymous identifier for the user
        """
        anonymous_id = f"deleted_user_{get_random_string(12)}"

        self.email = f"{anonymous_id}@deleted.local"
        self.first_name = "Deleted"
        self.last_name = "User"
        self.phone_number = None
        self.date_of_birth = None
        self.avatar = None
        self.is_active = False
        self.is_anonymized = True
        self.anonymized_at = timezone.now()

        # Clear marketing preferences
        self.marketing_consent = False
        self.newsletter_subscription = False

        # Clear OAuth data
        self.google_id = None

        self.save()

        # Clear related data that might contain PII
        from .models import UserAddress  # Avoid circular import

        UserAddress.objects.filter(user=self).delete()

        return anonymous_id

    def reactivate_account(self) -> None:
        """
        Reactivate a soft-deleted account if within reactivation window.

        Raises:
            ValueError: If account cannot be reactivated
        """
        if self.is_anonymized:
            raise ValueError("Cannot reactivate anonymized account")

        if self.deactivated_at:
            if not self.can_reactivate():
                raise ValueError("Reactivation deadline has passed")

        self.is_active = True
        self.deactivated_at = None
        self.deactivation_reason = ""
        self.save(update_fields=["is_active", "deactivated_at", "deactivation_reason"])

    def regenerate_verification_token(self) -> uuid.UUID:
        """
        Regenerate email verification token and update timestamp.

        Returns:
            UUID: New verification token
        """
        self.email_verification_token = uuid.uuid4()
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=["email_verification_token", "email_verification_sent_at"])
        return self.email_verification_token

    def export_user_data(self) -> Dict[str, Any]:
        """
        Export user data for GDPR compliance.

        Returns:
            Dictionary containing user's personal data
        """
        # Basic personal information
        personal_info = {
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone_number": self.phone_number,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

        # Account settings
        account_settings = {
            "is_email_verified": self.is_email_verified,
            "marketing_consent": self.marketing_consent,
            "newsletter_subscription": self.newsletter_subscription,
            "is_active": self.is_active,
        }

        # Activity logs (simplified)
        activity_logs = {
            "last_login_ip": self.last_login_ip,
            "deactivated_at": self.deactivated_at.isoformat() if self.deactivated_at else None,
            "deactivation_reason": self.deactivation_reason,
        }

        # Export related data
        exported_data = {
            "personal_information": personal_info,
            "account_settings": account_settings,
            "activity_logs": activity_logs,
        }

        # Add addresses if any
        addresses = []
        for address in self.addresses.all():
            addresses.append(
                {
                    "type": address.address_type,
                    "first_name": address.first_name,
                    "last_name": address.last_name,
                    "address_line1": address.address_line1,
                    "address_line2": address.address_line2,
                    "city": address.city,
                    "state": address.state,
                    "postal_code": address.postal_code,
                    "country": address.country,
                    "is_default": address.is_default,
                }
            )

        if addresses:
            exported_data["addresses"] = addresses

        return exported_data

    def clean(self):
        """Custom validation for the model."""
        super().clean()

        # Validate email uniqueness (case-insensitive)
        if self.email:
            self.email = self.email.lower()

        # Ensure anonymized users have proper data
        if self.is_anonymized:
            if not self.email.endswith("@deleted.local"):
                raise ValidationError("Anonymized users must have @deleted.local email")
            if self.first_name != "Deleted" or self.last_name != "User":
                raise ValidationError("Anonymized users must have 'Deleted User' name")

    def save(self, *args, **kwargs):
        """Override save to normalize email."""
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)


class UserAddress(models.Model):
    """User address model for shipping and billing."""

    ADDRESS_TYPE_CHOICES = [
        ("shipping", _("Shipping Address")),
        ("billing", _("Billing Address")),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    address_type = models.CharField(_("address type"), max_length=20, choices=ADDRESS_TYPE_CHOICES)
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)
    address_line1 = models.CharField(_("address line 1"), max_length=255)
    address_line2 = models.CharField(_("address line 2"), max_length=255, blank=True)
    city = models.CharField(_("city"), max_length=100)
    state = models.CharField(_("state/province"), max_length=100, blank=True)
    postal_code = models.CharField(_("postal code"), max_length=20)
    country = models.CharField(_("country"), max_length=100)
    is_default = models.BooleanField(_("is default"), default=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "accounts_useraddress"
        verbose_name = _("User Address")
        verbose_name_plural = _("User Addresses")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "address_type"],
                condition=models.Q(is_default=True),
                name="unique_default_address_per_type",
            )
        ]
        indexes = [
            models.Index(fields=["user", "address_type"]),
            models.Index(fields=["is_default"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_address_type_display()} for {self.user.email}"


class BlacklistedToken(models.Model):
    """Model to track blacklisted JWT tokens."""

    token_jti = models.CharField(_("token JTI"), max_length=255, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blacklisted_tokens")
    blacklisted_at = models.DateTimeField(_("blacklisted at"), auto_now_add=True)
    expires_at = models.DateTimeField(_("expires at"))

    class Meta:
        db_table = "accounts_blacklistedtoken"
        verbose_name = _("Blacklisted Token")
        verbose_name_plural = _("Blacklisted Tokens")
        indexes = [
            models.Index(fields=["token_jti"]),
            models.Index(fields=["user"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"Blacklisted token for {self.user.email}"

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return timezone.now() > self.expires_at
