"""
Daily Services offer batches, expiry, and reassignment.

Distance is a straight-line geographic estimate. It is not road distance or travel time.
This module does not send SMS and does not claim a worker was notified.
"""

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from .matching_columns import matching_offer_columns_ready, matching_request_columns_ready
from .models import DailyServiceRequest, ServiceOffer
from .services import (
    MatchResult,
    eligible_worker_profiles,
    geographic_distance_km,
)

MATCHABLE_STATUSES = frozenset({
    DailyServiceRequest.Status.DISPATCH_PENDING,
    DailyServiceRequest.Status.OFFERING,
    DailyServiceRequest.Status.NO_WORKERS,
    DailyServiceRequest.Status.NO_ACCEPTANCE,
    DailyServiceRequest.Status.WORKER_CANCELLED,
})
CLOSED_STATUSES = frozenset({
    DailyServiceRequest.Status.ASSIGNED,
    DailyServiceRequest.Status.IN_PROGRESS,
    DailyServiceRequest.Status.COMPLETED,
    DailyServiceRequest.Status.CANCELLED,
    DailyServiceRequest.Status.REFUND_REQUESTED,
})
BUSY_REQUEST_STATUSES = frozenset({
    DailyServiceRequest.Status.OFFERING,
    DailyServiceRequest.Status.ASSIGNED,
    DailyServiceRequest.Status.IN_PROGRESS,
})
REASON_ASSIGNED = 'assigned'
REASON_NO_ELIGIBLE = 'no_eligible'
REASON_NEEDS_CONSENT = 'needs_radius_consent'
REASON_NO_RESPONSE = 'no_response'
REASON_ALL_DECLINED = 'all_declined'
REASON_POOL_EXHAUSTED = 'pool_exhausted'
REASON_ROUNDS_EXHAUSTED = 'rounds_exhausted'
REASON_CANCELLED = 'cancelled'
REASON_OFFERING = 'offering'
REASON_UNUSABLE_LOCATION = 'unusable_location'


def match_batch_size():
    return int(getattr(settings, 'KAAMDO_MATCH_BATCH_SIZE', 3))


def match_offer_window():
    return timedelta(seconds=int(getattr(settings, 'KAAMDO_MATCH_OFFER_WINDOW_SECONDS', 180)))


def match_max_rounds():
    return int(getattr(settings, 'KAAMDO_MATCH_MAX_ROUNDS', 6))


def match_max_radius():
    return int(getattr(settings, 'KAAMDO_MATCH_MAX_RADIUS_KM', 100))


def radius_stages():
    stages = getattr(settings, 'KAAMDO_MATCH_RADIUS_STAGES', (8, 15, 20))
    cleaned = []
    for item in stages:
        try:
            value = int(item)
        except (TypeError, ValueError):
            continue
        if 5 <= value <= match_max_radius() and value not in cleaned:
            cleaned.append(value)
    return tuple(cleaned or (8, 15, 20))


def offer_deadline(offer, now=None):
    """Persisted expires_at when present; otherwise offered_at plus the configured window."""
    stored = getattr(offer, 'expires_at', None)
    if stored is not None:
        return stored
    offered = offer.offered_at or now or timezone.now()
    return offered + match_offer_window()


def offer_has_expired(offer, now=None):
    moment = now or timezone.now()
    deadline = offer_deadline(offer, now=moment)
    return deadline is not None and deadline <= moment


def agreed_radius(request):
    return int(request.radius_km)


def consented_radius(request):
    if not matching_request_columns_ready():
        return agreed_radius(request)
    extra = getattr(request, 'consented_radius_km', None)
    if extra is None:
        return agreed_radius(request)
    return max(agreed_radius(request), int(extra))


def permitted_radius(request):
    return min(consented_radius(request), match_max_radius())


def current_search_radius(request):
    permitted = permitted_radius(request)
    if matching_request_columns_ready():
        stored = getattr(request, 'search_radius_km', None)
        if stored:
            return min(int(stored), permitted)
    first = radius_stages()[0]
    return min(first, permitted)


def next_search_radius(request):
    current = current_search_radius(request)
    permitted = permitted_radius(request)
    for stage in radius_stages():
        if stage > current and stage <= permitted:
            return stage
    if current < permitted:
        return permitted
    return None


def next_radius_beyond_agreement(request):
    """Next configured stage above the original radius, if one exists at or below the hard max."""
    current = max(current_search_radius(request), agreed_radius(request))
    for stage in radius_stages():
        if stage > current and stage <= match_max_radius():
            return stage
    if current < match_max_radius():
        return match_max_radius()
    return None


def expand_target(request):
    inside = next_search_radius(request)
    if inside is not None:
        return inside
    return next_radius_beyond_agreement(request)


def can_expand(request):
    if request.status in CLOSED_STATUSES:
        return False
    if request.status not in {
        DailyServiceRequest.Status.NO_WORKERS,
        DailyServiceRequest.Status.NO_ACCEPTANCE,
        DailyServiceRequest.Status.OFFERING,
        DailyServiceRequest.Status.DISPATCH_PENDING,
    }:
        return False
    target = expand_target(request)
    return target is not None and target > permitted_radius(request)


def matching_public_fields(request):
    """Customer-visible matching fields. No worker identities."""
    reason = ''
    search = agreed_radius(request)
    if matching_request_columns_ready():
        reason = getattr(request, 'match_reason', '') or ''
        search = current_search_radius(request)
    target = expand_target(request) if can_expand(request) else None
    return {
        'search_radius_km': search,
        'match_reason': reason,
        'can_expand': bool(target),
        'expand_to_km': target,
    }


def ranked_candidates(request, radius_km, exclude_profile_ids):
    """Eligible workers inside this radius, nearest first. Straight-line kilometres only."""
    blocked = set(exclude_profile_ids)
    ranked = []
    for profile in eligible_worker_profiles(request):
        if profile.pk in blocked:
            continue
        distance = geographic_distance_km(
            request.latitude,
            request.longitude,
            profile.latitude,
            profile.longitude,
        )
        if distance is None or distance > float(radius_km) + 0.001:
            continue
        ranked.append((distance, profile.pk, profile))
    ranked.sort()
    return [item[2] for item in ranked]


def busy_profile_ids(request):
    """Providers already holding an open offer or an active assignment on another request."""
    return set(
        ServiceOffer.objects.filter(
            Q(state=ServiceOffer.State.OFFERED, request__status=DailyServiceRequest.Status.OFFERING)
            | Q(
                state=ServiceOffer.State.ACCEPTED,
                request__status__in=(
                    DailyServiceRequest.Status.ASSIGNED,
                    DailyServiceRequest.Status.IN_PROGRESS,
                ),
            )
        ).exclude(request=request).values_list('profile_id', flat=True)
    )


def used_profile_ids(request):
    return set(ServiceOffer.objects.filter(request=request).values_list('profile_id', flat=True))


def expire_open_offers(request=None, now=None):
    """Mark due offered rows expired. Idempotent. Does not assign anyone."""
    moment = now or timezone.now()
    queryset = ServiceOffer.objects.filter(state=ServiceOffer.State.OFFERED)
    if request is not None:
        queryset = queryset.filter(request=request)
    expired_ids = []
    for offer in queryset.select_related('request'):
        if not offer_has_expired(offer, now=moment):
            continue
        offer.state = ServiceOffer.State.EXPIRED
        offer.responded_at = moment
        fields = ['state', 'responded_at']
        offer.save(update_fields=fields)
        expired_ids.append(offer.pk)
    return tuple(expired_ids)


def _set_state(request, status, reason, search_radius=None, increment=False):
    if matching_request_columns_ready():
        request.match_reason = reason
        if search_radius is not None:
            request.search_radius_km = search_radius
        if increment:
            request.match_attempts = int(request.match_attempts or 0) + 1
    if request.status != status:
        request.transition_to(status)
    elif matching_request_columns_ready():
        request.save(update_fields=[
            'match_reason',
            'search_radius_km',
            'match_attempts',
            'updated_at',
        ])


def _past_offer_reason(request):
    states = list(ServiceOffer.objects.filter(request=request).values_list('state', flat=True))
    if not states:
        return REASON_NO_ELIGIBLE
    if all(state == ServiceOffer.State.DECLINED for state in states):
        return REASON_ALL_DECLINED
    if any(state == ServiceOffer.State.EXPIRED for state in states) and not any(
        state == ServiceOffer.State.DECLINED for state in states
    ):
        return REASON_NO_RESPONSE
    if all(state in {ServiceOffer.State.DECLINED, ServiceOffer.State.EXPIRED, ServiceOffer.State.WITHDRAWN} for state in states):
        if any(state == ServiceOffer.State.DECLINED for state in states):
            return REASON_ALL_DECLINED if not any(state == ServiceOffer.State.EXPIRED for state in states) else REASON_POOL_EXHAUSTED
        return REASON_NO_RESPONSE
    return REASON_POOL_EXHAUSTED


def _close_without_assignment(request, radius):
    reason = _past_offer_reason(request)
    if reason == REASON_NO_ELIGIBLE and can_expand(request):
        reason = REASON_NEEDS_CONSENT
    if reason in {REASON_NO_ELIGIBLE, REASON_NEEDS_CONSENT, REASON_UNUSABLE_LOCATION}:
        status = DailyServiceRequest.Status.NO_WORKERS
    else:
        status = DailyServiceRequest.Status.NO_ACCEPTANCE
    _set_state(request, status, reason, search_radius=radius)
    return MatchResult(
        eligible_profile_ids=(),
        created_offer_ids=(),
        existing_offer_ids=(),
        expired_offer_ids=(),
        reason=reason,
        search_radius_km=radius,
    )


def advance_matching(daily_request, *, now=None):
    """Create the next offer batch or close the request honestly.

    A draft or awaiting-payment request is refused. Silence is never acceptance.
    """
    moment = now or timezone.now()
    with transaction.atomic():
        locked = DailyServiceRequest.objects.select_for_update().get(pk=daily_request.pk)
        expired_ids = expire_open_offers(locked, now=moment)
        if locked.status in CLOSED_STATUSES:
            daily_request.status = locked.status
            return MatchResult(
                eligible_profile_ids=(),
                created_offer_ids=(),
                existing_offer_ids=(),
                expired_offer_ids=expired_ids,
                reason=REASON_CANCELLED if locked.status == DailyServiceRequest.Status.CANCELLED else REASON_ASSIGNED,
                search_radius_km=current_search_radius(locked),
            )
        if locked.status not in MATCHABLE_STATUSES:
            raise ValidationError({
                'status': 'Offers can be created only when the request is ready to send to workers.',
            })
        open_offers = list(
            ServiceOffer.objects.select_for_update().filter(
                request=locked,
                state=ServiceOffer.State.OFFERED,
            )
        )
        still_open = [offer for offer in open_offers if not offer_has_expired(offer, now=moment)]
        if still_open:
            daily_request.status = locked.status
            return MatchResult(
                eligible_profile_ids=(),
                created_offer_ids=(),
                existing_offer_ids=tuple(offer.pk for offer in still_open),
                expired_offer_ids=expired_ids,
                reason=REASON_OFFERING,
                search_radius_km=current_search_radius(locked),
            )
        attempts = int(getattr(locked, 'match_attempts', 0) or 0) if matching_request_columns_ready() else 0
        if attempts >= match_max_rounds():
            result = _close_without_assignment(locked, current_search_radius(locked))
            if matching_request_columns_ready():
                locked.match_reason = REASON_ROUNDS_EXHAUSTED
                locked.save(update_fields=['match_reason', 'updated_at'])
            daily_request.status = locked.status
            return MatchResult(
                eligible_profile_ids=(),
                created_offer_ids=(),
                existing_offer_ids=(),
                expired_offer_ids=expired_ids,
                reason=REASON_ROUNDS_EXHAUSTED,
                search_radius_km=current_search_radius(locked),
            )
        if not locked.latitude or not locked.longitude:
            _set_state(locked, DailyServiceRequest.Status.NO_WORKERS, REASON_UNUSABLE_LOCATION)
            daily_request.status = locked.status
            return MatchResult(
                eligible_profile_ids=(),
                created_offer_ids=(),
                existing_offer_ids=(),
                expired_offer_ids=expired_ids,
                reason=REASON_UNUSABLE_LOCATION,
                search_radius_km=current_search_radius(locked),
            )
        used = used_profile_ids(locked)
        busy = busy_profile_ids(locked)
        radius = current_search_radius(locked)
        created_ids = []
        existing_ids = []
        eligible_ids = []
        while True:
            candidates = ranked_candidates(locked, radius, used | busy)
            eligible_ids = [profile.pk for profile in candidates]
            if candidates:
                break
            nxt = next_search_radius(locked)
            if nxt is None:
                result = _close_without_assignment(locked, radius)
                daily_request.status = locked.status
                return MatchResult(
                    eligible_profile_ids=(),
                    created_offer_ids=(),
                    existing_offer_ids=(),
                    expired_offer_ids=expired_ids,
                    reason=result.reason,
                    search_radius_km=radius,
                )
            radius = nxt
            if matching_request_columns_ready():
                locked.search_radius_km = radius
        batch = candidates[:match_batch_size()]
        deadline = moment + match_offer_window()
        if locked.status == DailyServiceRequest.Status.DISPATCH_PENDING:
            locked.transition_to(DailyServiceRequest.Status.OFFERING)
        elif locked.status == DailyServiceRequest.Status.WORKER_CANCELLED:
            locked.transition_to(DailyServiceRequest.Status.OFFERING)
        elif locked.status != DailyServiceRequest.Status.OFFERING:
            locked.transition_to(DailyServiceRequest.Status.OFFERING)
        for profile in batch:
            offer, created = _create_offer(locked, profile, deadline)
            if created:
                created_ids.append(offer.pk)
            else:
                existing_ids.append(offer.pk)
        if matching_request_columns_ready():
            locked.match_reason = REASON_OFFERING
            locked.search_radius_km = radius
            locked.match_attempts = attempts + 1
            locked.save(update_fields=['match_reason', 'search_radius_km', 'match_attempts', 'updated_at'])
        daily_request.status = locked.status
        return MatchResult(
            eligible_profile_ids=tuple(eligible_ids),
            created_offer_ids=tuple(created_ids),
            existing_offer_ids=tuple(existing_ids),
            expired_offer_ids=expired_ids,
            reason=REASON_OFFERING,
            search_radius_km=radius,
        )


def _create_offer(daily_request, profile, deadline):
    defaults = {}
    if matching_offer_columns_ready():
        defaults['expires_at'] = deadline
    try:
        with transaction.atomic():
            return ServiceOffer.objects.get_or_create(
                request=daily_request,
                profile=profile,
                defaults=defaults,
            )
    except IntegrityError:
        offer = ServiceOffer.objects.get(request=daily_request, profile=profile)
        return offer, False


def process_due_matching(*, now=None, limit=50):
    """Expire due offers, then advance every request that can take another batch.

    Safe to run repeatedly. Does not depend on a browser refresh.
    """
    moment = now or timezone.now()
    expired = expire_open_offers(now=moment)
    processed = []
    queryset = DailyServiceRequest.objects.filter(status__in=MATCHABLE_STATUSES).order_by('updated_at', 'pk')
    for request in queryset[:limit]:
        open_count = ServiceOffer.objects.filter(
            request=request,
            state=ServiceOffer.State.OFFERED,
        ).count()
        if open_count:
            continue
        result = advance_matching(request, now=moment)
        processed.append((request.pk, result.reason, len(result.created_offer_ids)))
    return {
        'expired_offers': len(expired),
        'requests': len(processed),
    }


def cancel_daily_request(request):
    """Customer or guest cancellation. Outstanding offers are withdrawn."""
    with transaction.atomic():
        locked = DailyServiceRequest.objects.select_for_update().get(pk=request.pk)
        if locked.status in {
            DailyServiceRequest.Status.COMPLETED,
            DailyServiceRequest.Status.CANCELLED,
            DailyServiceRequest.Status.REFUND_REQUESTED,
        }:
            raise ValidationError({'status': 'This request can no longer be cancelled.'})
        if locked.status == DailyServiceRequest.Status.IN_PROGRESS:
            raise ValidationError({'status': 'Work already in progress cannot be cancelled here.'})
        now = timezone.now()
        ServiceOffer.objects.filter(request=locked, state=ServiceOffer.State.OFFERED).update(
            state=ServiceOffer.State.WITHDRAWN,
            responded_at=now,
        )
        if matching_request_columns_ready():
            locked.match_reason = REASON_CANCELLED
        if locked.status != DailyServiceRequest.Status.CANCELLED:
            if locked.status in DailyServiceRequest.ASSIGNED_STATUSES:
                locked.transition_to(DailyServiceRequest.Status.CANCELLED)
            else:
                locked.transition_to(DailyServiceRequest.Status.CANCELLED)
        request.status = locked.status
        return locked


def consent_to_expand(request, radius_km):
    """Record an explicit wider search. Does not invent a fee or an arrival time."""
    try:
        radius = int(radius_km)
    except (TypeError, ValueError):
        raise ValidationError({'radius_km': 'Choose a whole number of kilometres.'})
    if radius < 5 or radius > match_max_radius():
        raise ValidationError({'radius_km': f'Choose a radius from 5 to {match_max_radius()} kilometres.'})
    if radius <= agreed_radius(request):
        raise ValidationError({
            'radius_km': 'The wider search must be larger than the original radius you already chose.',
        })
    if not matching_request_columns_ready():
        raise ValidationError({
            'detail': 'Wider search is not available on this database yet.',
        })
    with transaction.atomic():
        locked = DailyServiceRequest.objects.select_for_update().get(pk=request.pk)
        if locked.status in CLOSED_STATUSES:
            raise ValidationError({'status': 'This request can no longer change its search radius.'})
        locked.consented_radius_km = max(int(locked.consented_radius_km or 0), radius)
        locked.search_radius_km = min(radius, locked.consented_radius_km)
        locked.save(update_fields=['consented_radius_km', 'search_radius_km', 'updated_at'])
        result = advance_matching(locked)
        request.status = locked.status
        return locked, result


def create_service_offers(daily_request):
    return advance_matching(daily_request)
