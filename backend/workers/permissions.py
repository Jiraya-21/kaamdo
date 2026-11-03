"""
Permissions for worker profile management.
"""

from rest_framework.permissions import BasePermission

from accounts.models import Capability
from accounts.permissions import HasCapability


class IsServiceProvider(HasCapability):
    required_capability = Capability.SERVICE_PROVIDER
    message = 'Only service provider accounts can manage a worker profile.'


class IsMarketplaceUser(BasePermission):
    """Any signed-in account may request and track Daily Services. Customer is not a role gate."""

    message = 'Sign in to request or track a daily service.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)


class IsCustomer(IsMarketplaceUser):
    """
    Kept for older imports. Customer is marketplace access, not a professional role.
    Prefer IsMarketplaceUser in new code.
    """

    message = 'Sign in to request or track a daily service.'


# Name kept for older imports. The check is the service-provider capability.
IsWorker = IsServiceProvider
