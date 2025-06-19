import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def _create_user(self, email, password=None, **extra_fields):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)
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


class User(AbstractUser):
    """Extended user model with additional fields for e-commerce platform."""

    username = None  # Remove the username field
    email = models.EmailField(_("email address"), unique=True)
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)

    # Additional profile fields
    phone_number = models.CharField(
        _("phone number"),
        max_length=17,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message=_('Phone number must be entered in format: "+999999999". Up to 15 digits allowed.'),
            )
        ],
        blank=True,
        null=True,
    )

    date_of_birth = models.DateField(_("date of birth"), null=True, blank=True)
    avatar = models.ImageField(_("avatar"), upload_to="avatars/%Y/%m/%d/", null=True, blank=True)

    # Account management
    is_email_verified = models.BooleanField(_("email verified"), default=False)
    email_verification_token = models.UUIDField(default=uuid.uuid4, editable=False)

    # Marketing preferences
    marketing_consent = models.BooleanField(_("marketing consent"), default=False)
    newsletter_subscription = models.BooleanField(_("newsletter subscription"), default=False)

    # Account metadata
    last_login_ip = models.GenericIPAddressField(_("last login IP"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    # Google OAuth integration
    google_id = models.CharField(_("Google ID"), max_length=255, unique=True, null=True, blank=True)

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
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.get_full_name()})"

    @property
    def full_name(self) -> str:
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_full_name(self) -> str:
        """Return user's full name for Django compatibility."""
        return self.full_name

    def clean(self):
        """Custom validation for the model."""
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)


class UserAddress(models.Model):
    """
    User shipping and billing addresses.

    Supports multiple addresses per user with type classification.
    """

    ADDRESS_TYPES = [
        ("shipping", _("Shipping")),
        ("billing", _("Billing")),
        ("both", _("Both")),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses", verbose_name=_("user"))

    address_type = models.CharField(_("address type"), max_length=10, choices=ADDRESS_TYPES, default="both")

    # Address fields
    first_name = models.CharField(_("first name"), max_length=100)
    last_name = models.CharField(_("last name"), max_length=100)
    company = models.CharField(_("company"), max_length=100, blank=True)
    address_line1 = models.CharField(_("address line 1"), max_length=255)
    address_line2 = models.CharField(_("address line 2"), max_length=255, blank=True)
    city = models.CharField(_("city"), max_length=100)
    state = models.CharField(_("state/province"), max_length=100)
    postal_code = models.CharField(_("postal code"), max_length=20)
    country = models.CharField(_("country"), max_length=2)  # ISO country code

    is_default = models.BooleanField(_("is default"), default=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "user_addresses"
        verbose_name = _("User Address")
        verbose_name_plural = _("User Addresses")
        indexes = [
            models.Index(fields=["user", "is_default"]),
            models.Index(fields=["user", "address_type"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "address_type"],
                condition=models.Q(is_default=True),
                name="unique_default_address_per_type",
            )
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} - {self.city}, {self.country}"


class BlacklistedToken(models.Model):
    """
    Store blacklisted JWT tokens for security.

    Used for logout functionality and token invalidation.
    """

    token_jti = models.CharField(_("token JTI"), max_length=255, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blacklisted_tokens", verbose_name=_("user"))
    blacklisted_at = models.DateTimeField(_("blacklisted at"), auto_now_add=True)
    expires_at = models.DateTimeField(_("expires at"))

    class Meta:
        db_table = "blacklisted_tokens"
        verbose_name = _("Blacklisted Token")
        verbose_name_plural = _("Blacklisted Tokens")
        indexes = [
            models.Index(fields=["token_jti"]),
            models.Index(fields=["user"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"Blacklisted token for {self.user.email}"
