"""
Booking-specific arrival verification for Daily Services.

Login OTPs are never reused. A provider cannot mark arrival verified alone.
Guest owners prove ownership with the request access key.
"""

import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    DailyServiceAssignmentEvent,
    DailyServiceArrivalChallenge,
    DailyServiceRequest,
)


ARRIVAL_CODE_LENGTH = 6
ARRIVAL_CODE_TTL_MINUTES = 15
ARRIVAL_MAX_ATTEMPTS = 5
ARRIVAL_REGEN_LIMIT = 5
ARRIVAL_REGEN_WINDOW_MINUTES = 30


def _random_arrival_code():
    return ''.join(secrets.choice('0123456789') for _ in range(ARRIVAL_CODE_LENGTH))


def _assert_assigned(record):
    if record.status != DailyServiceRequest.Status.ASSIGNED:
        raise ValidationError({
            'detail': 'Arrival verification is only available after a worker is assigned and before work starts.',
        })
    if record.assigned_profile_id is None:
        raise ValidationError({'detail': 'No worker is assigned to this request.'})


def provider_signals_arrival(record, *, provider_user):
    """
    Assigned provider indicates they have arrived. Returns a fresh booking code.
    Does not mark the visit verified.
    """
    _assert_assigned(record)
    profile = record.assigned_profile
    if profile is None or profile.user_id != provider_user.id:
        raise ValidationError({'detail': 'Only the assigned worker can signal arrival.'})

    now = timezone.now()
    recent = DailyServiceArrivalChallenge.objects.filter(
        request=record,
        created_at__gte=now - timedelta(minutes=ARRIVAL_REGEN_WINDOW_MINUTES),
    ).count()
    if recent >= ARRIVAL_REGEN_LIMIT:
        raise ValidationError({'detail': 'Wait before requesting another arrival code.'})

    code = _random_arrival_code()
    with transaction.atomic():
        DailyServiceArrivalChallenge.objects.filter(
            request=record,
            verified_at__isnull=True,
        ).update(superseded_at=now)
        challenge = DailyServiceArrivalChallenge.objects.create(
            request=record,
            assigned_profile=profile,
            code_hash=make_password(code),
            expires_at=now + timedelta(minutes=ARRIVAL_CODE_TTL_MINUTES),
        )
        DailyServiceAssignmentEvent.objects.create(
            request=record,
            profile=profile,
            event=DailyServiceAssignmentEvent.Event.ARRIVAL_SIGNALLED,
            note='Provider signalled arrival; customer verification required.',
        )
    return {
        'detail': 'Show this code to the customer. It does not start the visit by itself.',
        'code': code,
        'expires_in': ARRIVAL_CODE_TTL_MINUTES * 60,
        'challenge_id': challenge.pk,
        'request_status': record.status,
    }


def _owner_may_verify(record, *, user=None, access_key=''):
    if user is not None and user.is_authenticated and record.customer_id == user.id:
        return True
    if access_key and record.check_access_key(access_key):
        return True
    return False


def customer_verifies_arrival(record, *, code, user=None, access_key=''):
    """
    Customer (or guest owner) confirms the person who arrived using the booking code.
    On success: status becomes in_progress and arrival_verified_at is stored.
    """
    _assert_assigned(record)
    if not _owner_may_verify(record, user=user, access_key=access_key):
        raise ValidationError({'detail': 'Only the request owner can confirm arrival.'})

    raw = str(code or '').strip()
    if len(raw) != ARRIVAL_CODE_LENGTH or not raw.isdigit():
        raise ValidationError({'code': 'Enter the 6-digit arrival code from the assigned worker.'})

    now = timezone.now()
    challenge = (
        DailyServiceArrivalChallenge.objects.filter(
            request=record,
            verified_at__isnull=True,
            superseded_at__isnull=True,
        )
        .order_by('-created_at')
        .first()
    )
    if challenge is None:
        raise ValidationError({'detail': 'Ask the assigned worker to signal arrival first.'})
    if challenge.assigned_profile_id != record.assigned_profile_id:
        raise ValidationError({'detail': 'This arrival code is for a previous worker. Ask for a new code.'})
    if challenge.expires_at <= now:
        raise ValidationError({'detail': 'That arrival code has expired. Ask the worker for a new one.'})
    if challenge.attempt_count >= ARRIVAL_MAX_ATTEMPTS:
        raise ValidationError({'detail': 'Too many incorrect attempts. Ask the worker for a new code.'})

    if not check_password(raw, challenge.code_hash):
        challenge.attempt_count += 1
        challenge.save(update_fields=['attempt_count'])
        raise ValidationError({'code': 'That arrival code is incorrect.'})

    with transaction.atomic():
        locked = DailyServiceRequest.objects.select_for_update().get(pk=record.pk)
        _assert_assigned(locked)
        if locked.assigned_profile_id != challenge.assigned_profile_id:
            raise ValidationError({'detail': 'The assigned worker changed. Confirm arrival again with a new code.'})
        challenge.verified_at = now
        challenge.verified_by = user if user is not None and user.is_authenticated else None
        challenge.save(update_fields=['verified_at', 'verified_by'])
        locked.arrival_verified_at = now
        locked.transition_to(DailyServiceRequest.Status.IN_PROGRESS)
        DailyServiceAssignmentEvent.objects.create(
            request=locked,
            profile=locked.assigned_profile,
            event=DailyServiceAssignmentEvent.Event.ARRIVAL_VERIFIED,
            note='Customer verified arrival with booking code.',
        )
        locked.refresh_from_db()
        return locked


def customer_confirms_completion(record, *, user=None, access_key=''):
    """Owner confirms work finished. Only after verified arrival."""
    if record.status != DailyServiceRequest.Status.IN_PROGRESS:
        raise ValidationError({'detail': 'Completion is only available while the service is in progress.'})
    if record.arrival_verified_at is None:
        raise ValidationError({'detail': 'Arrival must be verified before completion.'})
    if not _owner_may_verify(record, user=user, access_key=access_key):
        raise ValidationError({'detail': 'Only the request owner can confirm completion.'})
    with transaction.atomic():
        locked = DailyServiceRequest.objects.select_for_update().get(pk=record.pk)
        if locked.status != DailyServiceRequest.Status.IN_PROGRESS:
            raise ValidationError({'detail': 'Completion is only available while the service is in progress.'})
        locked.transition_to(DailyServiceRequest.Status.COMPLETED)
        DailyServiceAssignmentEvent.objects.create(
            request=locked,
            profile=locked.assigned_profile,
            event=DailyServiceAssignmentEvent.Event.COMPLETED,
            note='Customer confirmed completion.',
        )
        locked.refresh_from_db()
        return locked


def record_assignment_event(record, profile, event, *, note=''):
    DailyServiceAssignmentEvent.objects.create(
        request=record,
        profile=profile,
        event=event,
        note=note or '',
    )


def invalidate_open_arrival_challenges(record, *, note=''):
    now = timezone.now()
    DailyServiceArrivalChallenge.objects.filter(
        request=record,
        verified_at__isnull=True,
        superseded_at__isnull=True,
    ).update(superseded_at=now)
    if record.arrival_verified_at is not None:
        record.arrival_verified_at = None
        record.save(update_fields=['arrival_verified_at', 'updated_at'])
