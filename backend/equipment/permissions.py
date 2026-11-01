"""
Permissions for equipment listings and rental requests.
Each check reads a capability row. active_mode is not consulted.
"""

from accounts.models import Capability
from accounts.permissions import HasCapability


class IsEquipmentOwner(HasCapability):
    required_capability = Capability.EQUIPMENT_OWNER
    message = 'Only equipment owner accounts can manage listings.'


class IsEquipmentRenter(HasCapability):
    required_capability = Capability.EQUIPMENT_RENTER
    message = 'Only equipment renter accounts can request a rental.'


class IsCustomer(HasCapability):
    required_capability = Capability.CUSTOMER
    message = 'Only customer accounts can send an equipment inquiry.'
