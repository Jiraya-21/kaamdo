"""
Account permissions.
A request is allowed only when the account has the capability stored in the database.
"""

from rest_framework.permissions import BasePermission


class HasCapability(BasePermission):
    """Allow the request when the signed-in user has required_capability."""

    required_capability = None
    message = 'Your account does not have this capability.'

    def has_permission(self, request, view):
        user = request.user
        code = getattr(view, 'required_capability', None) or self.required_capability
        return bool(
            user
            and user.is_authenticated
            and code
            and user.has_capability(code)
        )
