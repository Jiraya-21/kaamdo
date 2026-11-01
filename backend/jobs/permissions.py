"""
Permissions for ordinary jobs and agricultural hiring.
Each check reads a capability row. active_mode is not consulted.
"""

from accounts.models import Capability
from accounts.permissions import HasCapability


class IsEmployer(HasCapability):
    required_capability = Capability.EMPLOYER
    message = 'Only employer accounts can manage ordinary job posts.'


class IsJobSeeker(HasCapability):
    required_capability = Capability.JOB_SEEKER
    message = 'Only job seeker accounts can apply to ordinary jobs.'


class IsAgriculturalEmployer(HasCapability):
    required_capability = Capability.AGRICULTURAL_EMPLOYER
    message = 'Only agricultural job poster accounts can manage farm hiring posts.'


class IsAgriculturalWorker(HasCapability):
    required_capability = Capability.AGRICULTURAL_WORKER
    message = 'Only agricultural worker accounts can apply to farm hiring posts.'
