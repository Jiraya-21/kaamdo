"""
Permissions for worker profile management.
"""

from accounts.models import Capability
from accounts.permissions import HasCapability


class IsServiceProvider(HasCapability):
    required_capability = Capability.SERVICE_PROVIDER
    message = 'Only service provider accounts can manage a worker profile.'


class IsCustomer(HasCapability):
    required_capability = Capability.CUSTOMER
    message = 'Only customer accounts can use daily service requests.'


# Name kept for older imports. The check is the service-provider capability.
IsWorker = IsServiceProvider
