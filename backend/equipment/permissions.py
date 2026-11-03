"""
Permissions for equipment listings and rental requests.
Each check reads a capability row. active_mode is not consulted.
"""

from rest_framework.permissions import BasePermission

from accounts.models import Capability
from accounts.permissions import HasCapability


class IsEquipmentOwner(HasCapability):
    required_capability = Capability.EQUIPMENT_OWNER
    message = 'Only equipment owner accounts can manage listings.'


class IsEquipmentRenter(HasCapability):
    required_capability = Capability.EQUIPMENT_RENTER
    message = 'Only equipment renter accounts can request a rental.'


class IsCustomer(BasePermission):
    """Any signed-in account may send an equipment inquiry. Customer is not a role gate."""

    message = 'Sign in to send an equipment inquiry.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)
