from typing import Any

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import View


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.

    Assumes the model instance has a `user` attribute.
    """

    def has_object_permission(self, request: Request, view: View, obj: Any) -> bool:
        """Check if the user has permission to access the object."""
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        return obj.user == request.user


class IsOwner(permissions.BasePermission):
    """
    Permission to allow only owners to access their own objects.

    Stricter than IsOwnerOrReadOnly - no read access for non-owners.
    """

    def has_object_permission(self, request: Request, view: View, obj: Any) -> bool:
        """Check if the user is the owner of the object."""
        return hasattr(obj, "user") and obj.user == request.user


class IsAccountOwner(permissions.BasePermission):
    """
    Permission to allow users to access only their own account.

    Used for user profile endpoints where obj is the User instance.
    """

    def has_object_permission(self, request: Request, view: View, obj: Any) -> bool:
        """Check if the user is accessing their own account."""
        return obj == request.user

    def has_permission(self, request: Request, view: View) -> bool:
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated


class IsStaffOrOwner(permissions.BasePermission):
    """
    Permission to allow staff users or owners to access objects.

    Useful for admin endpoints that should be accessible to staff
    or the object owner.
    """

    def has_object_permission(self, request: Request, view: View, obj: Any) -> bool:
        """Check if user is staff or owner."""
        if request.user.is_staff:
            return True

        return hasattr(obj, "user") and obj.user == request.user


class IsEmailVerified(permissions.BasePermission):
    """
    Permission that requires user to have verified email.

    Useful for sensitive operations that require email verification.
    """

    message = "Email verification required."

    def has_permission(self, request: Request, view: View) -> bool:
        """Check if user has verified email."""
        if not (request.user and request.user.is_authenticated):
            return False

        # Check if user has email verification field
        return getattr(request.user, "is_email_verified", True)


class IsActiveUser(permissions.BasePermission):
    """
    Permission that requires user to be active.

    Blocks access for deactivated users.
    """

    message = "User account is deactivated."

    def has_permission(self, request: Request, view: View) -> bool:
        """Check if user is active."""
        return request.user and request.user.is_authenticated and request.user.is_active


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission that allows read-only access to everyone,
    but write access only to admin users.
    """

    def has_permission(self, request: Request, view: View) -> bool:
        """Check permissions based on request method."""
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user and request.user.is_staff


class IsSuperUserOrReadOnly(permissions.BasePermission):
    """
    Permission that allows read-only access to everyone,
    but write access only to superusers.
    """

    def has_permission(self, request: Request, view: View) -> bool:
        """Check permissions based on request method."""
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user and request.user.is_superuser


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission that allows access to owners or admin users.

    Useful for endpoints where both the owner and admins
    should have full access.
    """

    def has_object_permission(self, request: Request, view: View, obj: Any) -> bool:
        """Check if user is owner or admin."""
        # Admin users have full access
        if request.user.is_staff:
            return True

        # Owners have access to their objects
        return hasattr(obj, "user") and obj.user == request.user


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Permission that allows read-only access to everyone,
    but authenticated access for write operations.
    """

    def has_permission(self, request: Request, view: View) -> bool:
        """Check permissions based on authentication and method."""
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user and request.user.is_authenticated
