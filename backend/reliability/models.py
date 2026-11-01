"""
Reliability Models.
Defines:
- WorkerReliabilityScore: Weighted score (0-100) based on Punctuality, Completion, Feedback, Cancellations, Communication, and Disputes.
- ScoreAuditLog: Transparent audit trail of score recalculations and reasons.
- ReliabilityDispute: Formal dispute tracking for bookings.
- WorkerAppeal: Formal appeal records against disputes or score deductions.
"""

from django.db import models
from django.conf import settings

# Reliability models will be implemented in the feature phase
