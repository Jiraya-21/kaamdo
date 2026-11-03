"""
KaamDo Worker ID and public identity card helpers.

Never invent verification, ratings, qualifications, or completed work.
Never include Aadhaar, documents, private addresses, phone numbers, or coordinates.
"""

import secrets
import string

from django.db.models import Count

from .models import DailyServiceRequest, ServiceProviderVerification, WorkerProfile
from .photos import public_photo_url


WORKER_ID_PREFIX = 'KD'
WORKER_ID_LENGTH = 10
_WORKER_ID_ALPHABET = string.ascii_uppercase + string.digits


def generate_kaamdo_worker_id():
    """Return a unique permanent Worker ID string (not yet saved)."""
    for _ in range(32):
        body = ''.join(secrets.choice(_WORKER_ID_ALPHABET) for _ in range(WORKER_ID_LENGTH))
        candidate = f'{WORKER_ID_PREFIX}{body}'
        if not WorkerProfile.objects.filter(kaamdo_worker_id=candidate).exists():
            return candidate
    raise RuntimeError('Could not allocate a unique KaamDo Worker ID.')


def ensure_kaamdo_worker_id(profile):
    """Assign a permanent Worker ID once. Existing values are left unchanged."""
    if profile is None:
        return None
    current = (getattr(profile, 'kaamdo_worker_id', None) or '').strip()
    if current:
        return current
    profile.kaamdo_worker_id = generate_kaamdo_worker_id()
    profile.save(update_fields=['kaamdo_worker_id', 'updated_at'])
    return profile.kaamdo_worker_id


def _identity_verification_status(user):
    try:
        record = user.service_provider_verification
    except ServiceProviderVerification.DoesNotExist:
        return ServiceProviderVerification.Status.NOT_SUBMITTED
    return record.status


def _completed_jobs_count(profile):
    return DailyServiceRequest.objects.filter(
        assigned_profile=profile,
        status=DailyServiceRequest.Status.COMPLETED,
    ).count()


def _main_category_name(profile):
    category = profile.service_categories.order_by('name').first()
    if category is not None:
        return category.name
    skill = profile.skills.order_by('name').first()
    return skill.name if skill is not None else ''


def worker_identity_card(profile, *, request=None):
    """
    Public digital Worker ID card fields for an assigned or published provider.
    Omits secrets and unverified claims. Ratings/reviews omitted until real data exists.
    """
    if profile is None:
        return None
    ensure_kaamdo_worker_id(profile)
    user = profile.user
    identity_status = _identity_verification_status(user)
    skills = list(profile.skills.order_by('name').values_list('name', flat=True))
    return {
        'worker_id': profile.kaamdo_worker_id,
        'profile_id': profile.pk,
        'display_name': profile.display_name,
        'photo_url': public_photo_url(profile, request),
        'main_category': _main_category_name(profile),
        'skills': skills,
        'identity_verification': identity_status,
        'identity_verified': identity_status == ServiceProviderVerification.Status.APPROVED,
        # No separate skill/qualification verification system yet — never claim verified.
        'skill_verified': False,
        'qualification_verified': False,
        'experience_years': profile.experience_years,
        'completed_jobs': _completed_jobs_count(profile),
        # Reviews app is a stub; do not invent ratings.
        'rating_average': None,
        'review_count': None,
        'district': profile.district,
        'locality': profile.locality,
    }


def assigned_request_identity_card(record, *, request=None):
    """Worker ID card only when this request has an assigned provider in an assigned status."""
    profile = record.assigned_profile
    if record.status not in DailyServiceRequest.ASSIGNED_STATUSES or profile is None:
        return None
    return worker_identity_card(profile, request=request)
