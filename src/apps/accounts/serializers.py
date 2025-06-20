import logging
import re
import uuid
from typing import Any, Dict

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, UserAddress
from .utils import GoogleOAuthValidator

logger = logging.getLogger(__name__)


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification endpoint."""

    token = serializers.UUIDField(help_text="Email verification token from email link")

    def validate_token(self, value: uuid.UUID) -> uuid.UUID:
        """Validate verification token exists and is not expired."""
        try:
            user = User.objects.get(email_verification_token=value)
            if not user.is_verification_token_valid():
                raise serializers.ValidationError("Verification token has expired")
            if user.is_email_verified:
                raise serializers.ValidationError("Email is already verified")
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid verification token")

        return value


class EmailVerificationResponseSerializer(serializers.Serializer):
    """Response serializer for successful email verification."""

    message = serializers.CharField()
    user_id = serializers.IntegerField()
    verified_at = serializers.DateTimeField()


class PasswordValidationMixin:
    """
    Mixin for password validation with custom strength requirements.
    """

    def validate_password_strength(self, password: str) -> str:
        """
        Validate password meets security requirements.

        Requirements:
        - At least 8 characters
        - Contains uppercase and lowercase letters
        - Contains at least one digit
        - Contains at least one special character
        """
        if len(password) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")

        if not re.search(r"[A-Z]", password):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")

        if not re.search(r"[a-z]", password):
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")

        if not re.search(r"\d", password):
            raise serializers.ValidationError("Password must contain at least one digit.")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise serializers.ValidationError("Password must contain at least one special character.")

        # Use Django's built-in validators
        try:
            validate_password(password)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)

        return password


class UserRegistrationSerializer(serializers.ModelSerializer, PasswordValidationMixin):
    """
    Serializer for user registration with comprehensive validation.
    """

    email = serializers.EmailField(validators=[UniqueValidator(queryset=User.objects.all())])
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "phone_number",
            "date_of_birth",
            "marketing_consent",
            "newsletter_subscription",
        ]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate_password(self, value: str) -> str:
        """Validate password strength."""
        return self.validate_password_strength(value)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate password confirmation and other fields."""
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Password confirmation does not match."})

        attrs.pop("password_confirm")
        return attrs

    def create(self, validated_data: Dict[str, Any]) -> User:
        """Create user with hashed password."""
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user authentication with JWT token generation.
    """

    email = serializers.EmailField()
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate user and return tokens."""
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(request=self.context.get("request"), username=email, password=password)

            if not user:
                raise serializers.ValidationError("Invalid email or password.", code="authorization")

            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.", code="authorization")

            if not user.is_email_verified:
                raise serializers.ValidationError("Email address is not verified.", code="authorization")

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            attrs["user"] = user
            attrs["refresh"] = str(refresh)
            attrs["access"] = str(refresh.access_token)

        return attrs


class GoogleOAuthSerializer(serializers.Serializer):
    """
    Serializer for Google OAuth authentication with comprehensive validation.
    """

    access_token = serializers.CharField(max_length=2048, help_text="Google OAuth access token")

    def validate_access_token(self, value: str) -> str:
        """Validate Google access token format."""
        if not value.strip():
            raise serializers.ValidationError("Access token cannot be empty")
        return value.strip()

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate Google token and prepare user data.
        """
        access_token = attrs.get("access_token")

        # Validate with Google
        validator = GoogleOAuthValidator(settings.GOOGLE_OAUTH_CLIENT_ID)
        is_valid, user_info, error = validator.validate_token(access_token)

        if not is_valid:
            raise serializers.ValidationError({"access_token": error or "Invalid Google token"})

        if not user_info.get("email_verified", False):
            raise serializers.ValidationError({"access_token": "Google email not verified"})

        # Find or create user
        email = user_info["email"]
        google_id = user_info["google_id"]

        try:
            # Try to find an existing user by email or Google ID
            user = User.objects.filter(models.Q(email=email) | models.Q(google_id=google_id)).first()

            if user:
                # Update Google ID if missing
                if not user.google_id:
                    user.google_id = google_id
                    user.save(update_fields=["google_id"])

                # Verify email if from Google
                if not user.is_email_verified:
                    user.is_email_verified = True
                    user.save(update_fields=["is_email_verified"])
            else:
                # Create new user
                user = User.objects.create_user(
                    email=email,
                    google_id=google_id,
                    first_name=user_info.get("first_name", ""),
                    last_name=user_info.get("last_name", ""),
                    is_email_verified=True,  # Google emails are pre-verified
                )

            if not user.is_active:
                raise serializers.ValidationError({"access_token": "User account is disabled"})

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            attrs["user"] = user
            attrs["refresh"] = str(refresh)
            attrs["access"] = str(refresh.access_token)
            attrs["user_info"] = user_info

        except Exception as e:
            logger.error(f"Google OAuth user creation failed: {str(e)}")
            raise serializers.ValidationError({"access_token": "Authentication failed"})

        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile information.
    """

    full_name = serializers.ReadOnlyField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "date_of_birth",
            "avatar",
            "avatar_url",
            "marketing_consent",
            "newsletter_subscription",
            "is_email_verified",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "email", "is_email_verified", "date_joined", "last_login"]

    def get_avatar_url(self, obj: User) -> str:
        """Get full URL for user avatar."""
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return ""


class UserAddressSerializer(serializers.ModelSerializer):
    """
    Serializer for user addresses.
    """

    class Meta:
        model = UserAddress
        fields = [
            "id",
            "address_type",
            "first_name",
            "last_name",
            "company",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "is_default",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate address data."""
        # Add any custom address validation logic here
        return attrs


class PasswordChangeSerializer(serializers.Serializer, PasswordValidationMixin):
    """
    Serializer for password change functionality.
    """

    current_password = serializers.CharField(style={"input_type": "password"})
    new_password = serializers.CharField(style={"input_type": "password"})
    new_password_confirm = serializers.CharField(style={"input_type": "password"})

    def validate_current_password(self, value: str) -> str:
        """Validate current password."""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value: str) -> str:
        """Validate new password strength."""
        return self.validate_password_strength(value)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate password confirmation."""
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Password confirmation does not match."})
        return attrs

    def save(self) -> None:
        """Change user password."""
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
