"""
Daily-service worker matching.

Distance is a straight-line geographic estimate on the Earth's surface.
It is not the distance by road.
"""

import math
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from accounts.models import AccountCapability, OtpPurpose, guest_phone_is_verified, normalize_phone
from locations.places import place_taluk

from .models import (
    DailyServiceRequest,
    RequestExtraCharge,
    ServiceOffer,
    ServicePriceMenuItem,
    ServiceProviderVerification,
    VisitPayment,
    WorkerProfile,
    get_active_visit_fee,
)

EARTH_RADIUS_KM = 6371.0
# Absorbs tiny rounding in the distance formula. It does not widen the chosen radius.
DISTANCE_TOLERANCE_KM = 0.001


@dataclass(frozen=True)
class MatchResult:
    """Offer counts for one matching run. This does not include guest or worker contact details."""

    eligible_profile_ids: tuple
    created_offer_ids: tuple
    existing_offer_ids: tuple
    expired_offer_ids: tuple = ()
    reason: str = ''
    search_radius_km: int = 0

    @property
    def eligible_count(self):
        return len(self.eligible_profile_ids)


def coordinates_are_valid(latitude, longitude):
    """True when both coordinates exist and fall in the normal latitude and longitude ranges."""
    latitude_value = _finite_float(latitude)
    longitude_value = _finite_float(longitude)
    if latitude_value is None or longitude_value is None:
        return False
    return -90 <= latitude_value <= 90 and -180 <= longitude_value <= 180


def geographic_distance_km(latitude_a, longitude_a, latitude_b, longitude_b):
    """Return the straight-line distance in kilometres, or None when coordinates are unusable."""
    if not coordinates_are_valid(latitude_a, longitude_a) or not coordinates_are_valid(latitude_b, longitude_b):
        return None
    lat1 = math.radians(float(latitude_a))
    lon1 = math.radians(float(longitude_a))
    lat2 = math.radians(float(latitude_b))
    lon2 = math.radians(float(longitude_b))
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    chord = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    chord = min(1.0, max(0.0, chord))
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(chord))


def eligible_worker_profiles(daily_request):
    """Return published, approved, available workers who cover this request's category and both radii."""
    if not coordinates_are_valid(daily_request.latitude, daily_request.longitude):
        return []
    has_provider = AccountCapability.objects.filter(
        user_id=OuterRef('user_id'),
        code='service_provider',
    )
    candidates = (
        WorkerProfile.objects.filter(
            service_categories=daily_request.category,
            publication_status=WorkerProfile.PublicationStatus.PUBLISHED,
            availability=WorkerProfile.Availability.AVAILABLE,
            user__is_active=True,
            user__service_provider_verification__status=ServiceProviderVerification.Status.APPROVED,
            latitude__isnull=False,
            longitude__isnull=False,
        )
        .filter(Exists(has_provider))
        .select_related('user', 'user__service_provider_verification')
        .order_by('id')
    )
    eligible = []
    for profile in candidates:
        if not coordinates_are_valid(profile.latitude, profile.longitude):
            continue
        distance_km = geographic_distance_km(
            daily_request.latitude,
            daily_request.longitude,
            profile.latitude,
            profile.longitude,
        )
        if distance_km is None:
            continue
        if not _within_radius(distance_km, _request_cover_radius(daily_request)):
            continue
        if not _within_radius(distance_km, profile.service_radius_km):
            continue
        eligible.append(profile)
    return eligible


def _request_cover_radius(daily_request):
    """Largest radius this request may currently search, including explicit consent."""
    agreed = float(daily_request.radius_km)
    extra = getattr(daily_request, 'consented_radius_km', None)
    if extra:
        return max(agreed, float(extra))
    return agreed


def create_service_offers(daily_request):
    """Create the next offer batch, or reuse offers already being offered.

    A draft or awaiting-payment request is refused. No payment row is created.
    """
    from .matching import advance_matching

    return advance_matching(daily_request)


TEST_VISIT_PAYMENT_VALUES = frozenset({'mock_demo', 'test_bypass'})
TEST_PAYMENT_LABEL = 'Inspection fee paid. Workers can be offered now.'


def mock_visit_payment_enabled():
    """True only for a local debug process that explicitly asked for a mock visit payment."""
    return test_visit_payment_enabled()


def test_visit_payment_enabled():
    """Mock checkout. Off by default. Refuses when DEBUG is False. Not a real payment."""
    if settings.DEBUG is not True:
        return False
    value = str(getattr(settings, 'KAAMDO_VISIT_PAYMENT', 'unconfigured') or '').strip().lower()
    return value in TEST_VISIT_PAYMENT_VALUES


def test_payment_public_payload():
    return {
        'enabled': True,
        'label': TEST_PAYMENT_LABEL,
        'money_received': False,
        'provider': 'razorpay_mock',
    }


def price_menu_payload():
    """Public company menu: inspection fee + extra work items."""
    fee = get_active_visit_fee()
    inspection = {
        'title': 'Inspection fee',
        'description': 'Worker visits and checks the work. Paid before a worker is offered.',
        'amount_inr': format(fee.amount_inr, 'f') if fee else '99.00',
        'currency': 'INR',
        'kind': 'inspection',
        'code': 'inspection-fee',
    }
    extras = []
    for item in ServicePriceMenuItem.objects.filter(is_active=True, kind=ServicePriceMenuItem.Kind.EXTRA):
        extras.append({
            'id': item.pk,
            'code': item.code,
            'title': item.title,
            'description': item.description,
            'amount_inr': format(item.amount_inr, 'f'),
            'currency': 'INR',
            'kind': item.kind,
        })
    return {
        'inspection_fee': inspection,
        'extras': extras,
        'mock_checkout': mock_visit_payment_enabled(),
        'money_received': False,
        'provider_label': 'Pay inspection fee' if mock_visit_payment_enabled() else '',
        'steps': [
            'Pay the inspection fee to confirm the visit.',
            'Worker checks the work at the place.',
            'If more work is needed, worker adds items from this menu.',
            'Pay any extras. Then the work can finish.',
        ],
    }


def payment_snapshot(record):
    """Inspection + extras payment fields for track / account screens."""
    fee = get_active_visit_fee()
    payment = VisitPayment.objects.filter(request_id=record.pk).first()
    extras = list(
        RequestExtraCharge.objects.filter(request_id=record.pk)
        .exclude(state=RequestExtraCharge.State.CANCELLED)
    )
    proposed = [row for row in extras if row.state == RequestExtraCharge.State.PROPOSED]
    paid_extras = [row for row in extras if row.state == RequestExtraCharge.State.MOCK_PAID]
    can_pay_inspection = mock_visit_payment_enabled() and record.status in (
        DailyServiceRequest.Status.DRAFT,
        DailyServiceRequest.Status.AWAITING_PAYMENT,
    )
    can_pay_extras = mock_visit_payment_enabled() and bool(proposed)
    return {
        'inspection_fee_inr': format(fee.amount_inr, 'f') if fee else None,
        'inspection_label': 'Inspection fee',
        'payment_state': payment.state if payment else None,
        'payment_amount_inr': format(payment.amount_inr, 'f') if payment else None,
        'mock_checkout': mock_visit_payment_enabled(),
        'can_pay_inspection': can_pay_inspection,
        'can_pay_extras': can_pay_extras,
        'money_received': False,
        'provider_label': 'Pay inspection fee' if mock_visit_payment_enabled() else '',
        'extras': [
            {
                'id': row.pk,
                'title': row.title,
                'amount_inr': format(row.amount_inr, 'f'),
                'state': row.state,
            }
            for row in extras
        ],
        'extras_due_inr': format(
            sum((row.amount_inr for row in proposed), Decimal('0.00')),
            'f',
        ),
        'extras_paid_inr': format(
            sum((row.amount_inr for row in paid_extras), Decimal('0.00')),
            'f',
        ),
    }


def user_may_mock_pay_request(user, record):
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_staff', False):
        return True
    return record.customer_id is not None and record.customer_id == user.id


def propose_request_extras(record, user, menu_item_ids):
    """Assigned worker picks company-menu extras after inspection."""
    if record.status not in (
        DailyServiceRequest.Status.ASSIGNED,
        DailyServiceRequest.Status.IN_PROGRESS,
    ):
        raise ValidationError({'status': 'Extras can be added only after a worker is assigned.'})
    profile = getattr(record, 'assigned_profile', None)
    if profile is None or profile.user_id != user.id:
        raise ValidationError({'detail': 'Only the assigned worker can add extras from the menu.'})
    ids = []
    for raw in menu_item_ids or []:
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            raise ValidationError({'items': 'Choose items from the company price menu.'}) from None
    if not ids:
        raise ValidationError({'items': 'Choose at least one menu item.'})
    items = list(
        ServicePriceMenuItem.objects.filter(
            pk__in=ids,
            is_active=True,
            kind=ServicePriceMenuItem.Kind.EXTRA,
        )
    )
    if len(items) != len(set(ids)):
        raise ValidationError({'items': 'One or more menu items are not available.'})
    created = []
    with transaction.atomic():
        locked = DailyServiceRequest.objects.select_for_update().get(pk=record.pk)
        for item in items:
            created.append(
                RequestExtraCharge.objects.create(
                    request=locked,
                    menu_item=item,
                    title=item.title,
                    amount_inr=item.amount_inr,
                    state=RequestExtraCharge.State.PROPOSED,
                    proposed_by=user,
                )
            )
    return created


def record_mock_extra_payment(record):
    """Mark proposed extras as mock paid. Does not receive money."""
    if not mock_visit_payment_enabled():
        raise ValidationError({'detail': 'Mock visit payment is not enabled. No payment was recorded.'})
    with transaction.atomic():
        locked = DailyServiceRequest.objects.select_for_update().get(pk=record.pk)
        rows = list(
            RequestExtraCharge.objects.select_for_update().filter(
                request=locked,
                state=RequestExtraCharge.State.PROPOSED,
            )
        )
        if not rows:
            raise ValidationError({'detail': 'No extra charges are waiting for payment.'})
        now = timezone.now()
        for row in rows:
            row.state = RequestExtraCharge.State.MOCK_PAID
            row.paid_at = now
            row.save(update_fields=['state', 'paid_at'])
        return rows


def prepare_inspection_payment(daily_request):
    """After contact verification + booking: wait for inspection fee before any worker offer.

    Stops empty draft bookings from looking ready. Does not receive money and does not match workers.
    """
    fee = get_active_visit_fee()
    with transaction.atomic():
        locked = DailyServiceRequest.objects.select_for_update().get(pk=daily_request.pk)
        if locked.status not in (
            DailyServiceRequest.Status.DRAFT,
            DailyServiceRequest.Status.AWAITING_PAYMENT,
        ):
            daily_request.status = locked.status
            return locked, VisitPayment.objects.filter(request_id=locked.pk).first()
        if locked.status == DailyServiceRequest.Status.DRAFT:
            locked.transition_to(DailyServiceRequest.Status.AWAITING_PAYMENT)
        payment = VisitPayment.objects.select_for_update().filter(request=locked).first()
        if payment is None:
            if fee is None:
                raise ValidationError({'detail': 'No active inspection fee is configured.'})
            payment = VisitPayment(
                request=locked,
                amount_inr=fee.amount_inr,
                currency='INR',
                state=VisitPayment.State.PENDING,
                verification_source=VisitPayment.Source.NONE,
            )
            payment.full_clean()
            payment.save()
        daily_request.status = locked.status
        return locked, payment


def record_mock_visit_progress(daily_request):
    """Record a mock demo payment and move a draft/awaiting request to ready-to-offer.

    This does not receive money, verify a gateway payment, match workers, or assign anyone.
    Call only after the booking contact was verified and prepare_inspection_payment ran (or draft).
    """
    if not mock_visit_payment_enabled():
        raise ValidationError({'detail': 'Mock visit payment is not enabled. No payment was recorded.'})
    with transaction.atomic():
        locked = DailyServiceRequest.objects.select_for_update().get(pk=daily_request.pk)
        payment = VisitPayment.objects.select_for_update().filter(request=locked).first()
        if _mock_progress_is_complete(locked, payment):
            daily_request.status = locked.status
            return locked, payment
        if not _mock_progress_can_continue(locked, payment):
            raise ValidationError({
                'status': 'This request cannot take a mock payment in its current state. Nothing was changed.',
            })
        fee = get_active_visit_fee()
        if payment is None and fee is None:
            raise ValidationError({'detail': 'No active visit fee is configured. No payment was recorded.'})
        if (
            payment is not None
            and payment.state == VisitPayment.State.PENDING
            and (fee is None or payment.amount_inr != fee.amount_inr)
        ):
            raise ValidationError({
                'status': 'This request cannot take a mock payment in its current state. Nothing was changed.',
            })
        if locked.status == DailyServiceRequest.Status.DRAFT:
            locked.transition_to(DailyServiceRequest.Status.AWAITING_PAYMENT)
        if payment is None:
            payment = VisitPayment(
                request=locked,
                amount_inr=fee.amount_inr,
                currency='INR',
                state=VisitPayment.State.PENDING,
                verification_source=VisitPayment.Source.NONE,
            )
            payment.full_clean()
            payment.save()
        if payment.state == VisitPayment.State.PENDING:
            payment.transition_to(
                VisitPayment.State.MOCK_RECORDED,
                verification_source=VisitPayment.Source.MOCK_DEMO,
            )
        if locked.status == DailyServiceRequest.Status.AWAITING_PAYMENT:
            locked.transition_to(DailyServiceRequest.Status.DISPATCH_PENDING)
        if not _mock_progress_is_complete(locked, payment):
            raise ValidationError({
                'status': 'This request cannot take a mock payment in its current state. Nothing was changed.',
            })
        daily_request.status = locked.status
        return locked, payment


def offer_workers_after_inspection_fee(daily_request):
    """After the inspection fee is recorded, start offering eligible workers.

    Matching used to wait for a separate cron loop, which felt broken after pay.
    Safe to call repeatedly. Does not take money.
    """
    from .matching import advance_matching

    if daily_request.status != DailyServiceRequest.Status.DISPATCH_PENDING:
        return daily_request
    advance_matching(daily_request)
    daily_request.refresh_from_db()
    return daily_request


def _mock_payment_is_demo(payment):
    return (
        payment is not None
        and payment.state == VisitPayment.State.MOCK_RECORDED
        and payment.verification_source == VisitPayment.Source.MOCK_DEMO
        and payment.verified_at is None
    )


def _mock_progress_is_complete(daily_request, payment):
    # Fee already recorded. Matching may have moved the request past dispatch_pending.
    return _mock_payment_is_demo(payment)


def _mock_progress_can_continue(daily_request, payment):
    if daily_request.status == DailyServiceRequest.Status.DRAFT:
        return payment is None
    if daily_request.status != DailyServiceRequest.Status.AWAITING_PAYMENT:
        return False
    if payment is None:
        return True
    if payment.verified_at is not None:
        return False
    if payment.state == VisitPayment.State.PENDING and payment.verification_source == VisitPayment.Source.NONE:
        return True
    return _mock_payment_is_demo(payment)


def _finite_float(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _within_radius(distance_km, radius_km):
    return distance_km <= float(radius_km) + DISTANCE_TOLERANCE_KM


def published_worker_profiles():
    """Published Daily Services providers only.

    A job-seeker account does not have this profile. A published row whose
    account no longer has the service-provider capability stays off the list.
    """
    has_provider = AccountCapability.objects.filter(
        user_id=OuterRef('user_id'),
        code='service_provider',
    )
    return (
        WorkerProfile.objects.filter(
            publication_status=WorkerProfile.PublicationStatus.PUBLISHED,
            user__is_active=True,
        )
        .filter(Exists(has_provider))
        .select_related('user')
        .prefetch_related('skills', 'service_categories')
    )


def _query_text(value):
    if value is None:
        return ''
    return ' '.join(str(value).split())


def _directory_origin(params):
    """Return origin and radius, or None when the caller did not ask for a radius search."""
    latitude = _query_text(params.get('latitude'))
    longitude = _query_text(params.get('longitude'))
    radius = _query_text(params.get('radius_km'))
    if not latitude and not longitude and not radius:
        return None
    if not latitude or not longitude or not radius:
        raise ValidationError({
            'radius_km': 'Provide latitude, longitude, and radius_km together.',
        })
    if not coordinates_are_valid(latitude, longitude):
        raise ValidationError({
            'latitude': 'Latitude and longitude must be usable coordinates.',
        })
    try:
        radius_km = int(radius)
    except (TypeError, ValueError):
        raise ValidationError({'radius_km': 'Enter a whole number of kilometres from 1 to 100.'})
    if radius_km < 1 or radius_km > 100:
        raise ValidationError({'radius_km': 'Enter a whole number of kilometres from 1 to 100.'})
    return float(latitude), float(longitude), radius_km


def public_worker_directory(params):
    """Filter every published profile before pagination.

    Skill, category, district, and text search run in the database.
    A radius search then keeps only workers whose straight-line distance is inside
    that radius. Workers with missing or invalid coordinates are left out of a
    radius search because their distance cannot be calculated.
    """
    profiles = published_worker_profiles()
    skill = _query_text(params.get('skill'))
    category = _query_text(params.get('category'))
    district = _query_text(params.get('district'))
    query = _query_text(params.get('q'))
    if skill:
        profiles = profiles.filter(skills__name__iexact=skill)
    if category:
        profiles = profiles.filter(
            service_categories__slug__iexact=category,
            service_categories__is_active=True,
        )
    if district:
        profiles = profiles.filter(district__iexact=district)
    if query:
        profiles = profiles.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(skills__name__icontains=query)
            | Q(district__icontains=query)
            | Q(locality__icontains=query)
        )
    pks = profiles.values_list('pk', flat=True).distinct()
    profiles = (
        WorkerProfile.objects.filter(pk__in=pks)
        .select_related('user')
        .prefetch_related('skills', 'service_categories')
        .order_by('-updated_at', 'pk')
    )
    origin = _directory_origin(params)
    if origin is None:
        return profiles
    latitude, longitude, radius_km = origin
    matched = []
    for profile in profiles:
        distance_km = geographic_distance_km(
            latitude,
            longitude,
            profile.latitude,
            profile.longitude,
        )
        if distance_km is None or not _within_radius(distance_km, radius_km):
            continue
        matched.append(profile)
    matched.sort(key=lambda profile: (
        geographic_distance_km(latitude, longitude, profile.latitude, profile.longitude),
        profile.pk,
    ))
    return matched


def respond_to_service_offer(user, offer_id, decision):
    """Accept or decline one offer. The signed-in user must own that offer's worker profile."""
    if decision not in ('accept', 'decline'):
        raise ValidationError({'decision': 'Choose accept or decline.'})
    profile = WorkerProfile.objects.filter(user=user).first()
    preview = (
        ServiceOffer.objects.filter(pk=offer_id, profile=profile).only('id', 'request_id').first()
        if profile is not None
        else None
    )
    if preview is None:
        raise ServiceOffer.DoesNotExist
    from .matching import MATCHABLE_STATUSES, advance_matching, expire_open_offers, offer_has_expired

    now = timezone.now()
    daily_request = DailyServiceRequest.objects.get(pk=preview.request_id)
    expire_open_offers(daily_request, now=now)
    current = ServiceOffer.objects.filter(pk=preview.pk, profile=profile).first()
    if current is not None and (current.state != ServiceOffer.State.OFFERED or offer_has_expired(current, now=now)):
        if current.state == ServiceOffer.State.OFFERED:
            current.state = ServiceOffer.State.EXPIRED
            current.responded_at = now
            current.save(update_fields=['state', 'responded_at'])
        if daily_request.status in MATCHABLE_STATUSES:
            advance_matching(daily_request, now=now)
        raise ValidationError({'decision': 'This offer has expired and cannot be accepted.'})
    with transaction.atomic():
        daily_request = DailyServiceRequest.objects.select_for_update().get(pk=preview.request_id)
        offer = ServiceOffer.objects.select_for_update().get(pk=preview.pk, profile=profile)
        if offer.state != ServiceOffer.State.OFFERED:
            raise ValidationError({'decision': 'This offer has already been answered.'})
        if offer_has_expired(offer, now=now):
            offer.state = ServiceOffer.State.EXPIRED
            offer.responded_at = now
            offer.save(update_fields=['state', 'responded_at'])
            if daily_request.status in MATCHABLE_STATUSES:
                advance_matching(daily_request, now=now)
            raise ValidationError({'decision': 'This offer has expired and cannot be accepted.'})
        if decision == 'decline':
            offer.state = ServiceOffer.State.DECLINED
            offer.responded_at = now
            offer.save(update_fields=['state', 'responded_at'])
            if daily_request.status in MATCHABLE_STATUSES:
                advance_matching(daily_request, now=now)
                daily_request.refresh_from_db()
            offer.request = daily_request
            return offer
        if daily_request.status != DailyServiceRequest.Status.OFFERING:
            raise ValidationError({
                'decision': 'This request cannot be accepted until it is being offered to workers.',
            })
        offer.state = ServiceOffer.State.ACCEPTED
        offer.responded_at = timezone.now()
        offer.save(update_fields=['state', 'responded_at'])
        daily_request.transition_to(
            DailyServiceRequest.Status.ASSIGNED,
            assigned_profile=profile,
        )
        from .matching import REASON_ASSIGNED
        from .matching_columns import matching_request_columns_ready

        if matching_request_columns_ready():
            daily_request.match_reason = REASON_ASSIGNED
            daily_request.save(update_fields=['match_reason', 'updated_at'])
        ServiceOffer.objects.filter(
            request=daily_request,
            state=ServiceOffer.State.OFFERED,
        ).exclude(pk=offer.pk).update(
            state=ServiceOffer.State.WITHDRAWN,
            responded_at=timezone.now(),
        )
        offer.request = daily_request
        return offer


def _offer_for_pair(daily_request, profile):
    try:
        with transaction.atomic():
            return ServiceOffer.objects.get_or_create(
                request=daily_request,
                profile=profile,
            )
    except IntegrityError:
        offer = ServiceOffer.objects.get(request=daily_request, profile=profile)
        return offer, False


def assigned_worker_card(record, *, request=None):
    """Digital Worker ID card after assignment. Omits phone, documents, and invented ratings."""
    from .identity import assigned_request_identity_card

    card = assigned_request_identity_card(record, request=request)
    if card is None:
        return None
    # Keep legacy keys used by existing clients and tests.
    card['id'] = card.get('profile_id')
    profile = record.assigned_profile
    if profile is not None:
        card['taluk'] = place_taluk(profile)
    return card


def customer_daily_requests(user):
    """Requests owned by this account. A browser-supplied customer id is not used."""
    return (
        DailyServiceRequest.objects.filter(customer=user)
        .select_related('category', 'assigned_profile', 'assigned_profile__user')
        .prefetch_related('assigned_profile__skills')
    )


def customer_daily_request_payload(record, *, request=None):
    """Fields a request owner may see for their own request. No access key."""
    from .matching import matching_public_fields

    payload = {
        'reference': record.pk,
        'category': record.category.name,
        'description': record.description,
        'status': record.status,
        'radius_km': record.radius_km,
        'created_at': record.created_at,
        'arrival_verified_at': getattr(record, 'arrival_verified_at', None),
    }
    payload.update(matching_public_fields(record))
    payload['payment'] = payment_snapshot(record)
    card = assigned_worker_card(record, request=request)
    if card is not None:
        payload['assigned_profile'] = card
        payload['worker_identity'] = card
    return payload


def provider_daily_offers(user):
    """Offers for the signed-in worker's profile. A browser-supplied profile id is not used."""
    return (
        ServiceOffer.objects.filter(profile__user=user)
        .select_related('request', 'request__category', 'profile')
    )


def provider_offer_payload(offer):
    """Offer state plus the request summary needed to accept or decline. No guest secrets."""
    record = offer.request
    payment = payment_snapshot(record)
    return {
        'id': offer.pk,
        'state': offer.state,
        'offered_at': offer.offered_at,
        'responded_at': offer.responded_at,
        'expires_at': getattr(offer, 'expires_at', None),
        'request': {
            'reference': record.pk,
            'category': record.category.name,
            'description': record.description,
            'status': record.status,
            'radius_km': record.radius_km,
            'payment': payment,
            'can_propose_extras': record.status in (
                DailyServiceRequest.Status.ASSIGNED,
                DailyServiceRequest.Status.IN_PROGRESS,
            ),
        },
    }


def describe_guest_request(reference, access_key, *, request=None):
    """Return a guest's request status after the access key matches. The number alone is not enough."""
    if isinstance(reference, bool) or not isinstance(reference, (int, str)):
        raise DailyServiceRequest.DoesNotExist
    try:
        pk = int(reference)
    except (TypeError, ValueError):
        raise DailyServiceRequest.DoesNotExist
    record = (
        DailyServiceRequest.objects.filter(pk=pk)
        .select_related('assigned_profile', 'assigned_profile__user', 'category')
        .prefetch_related('assigned_profile__skills', 'assigned_profile__service_categories')
        .first()
    )
    if record is None or not record.check_access_key(access_key):
        raise DailyServiceRequest.DoesNotExist
    return guest_track_payload(record, request=request)


def guest_track_payload(record, *, request=None):
    """Public track fields for one request. No access key, no raw contact."""
    from .matching import matching_public_fields

    payload = {
        'reference': record.pk,
        'category': record.category.name if record.category_id else '',
        'description': record.description,
        'status': record.status,
        'radius_km': record.radius_km,
        'created_at': record.created_at,
        'arrival_verified_at': getattr(record, 'arrival_verified_at', None),
    }
    payload.update(matching_public_fields(record))
    payload['payment'] = payment_snapshot(record)
    card = assigned_worker_card(record, request=request)
    if card is not None:
        payload['assigned_profile'] = card
        payload['worker_identity'] = card
    return payload


def phone_controls_daily_request(record, phone):
    """True when a recently verified mobile number owns this request."""
    phone = normalize_phone(phone)
    if not phone or not guest_phone_is_verified(phone, OtpPurpose.SERVICE_REQUEST):
        return False
    contact = normalize_phone(getattr(record, 'contact_phone', '') or '')
    if contact and contact == phone:
        return True
    customer = getattr(record, 'customer', None)
    if customer is not None and normalize_phone(getattr(customer, 'phone_number', '') or '') == phone:
        return True
    return False


def list_requests_for_verified_phone(phone, *, request=None):
    """All requests tied to a mobile number after that number passed the guest OTP check.

    Guests no longer need to remember a request id or secret code.
    """
    phone = normalize_phone(phone)
    if not phone:
        raise ValidationError({'phone_number': 'Enter a 10-digit Indian mobile number.'})
    if not guest_phone_is_verified(phone, OtpPurpose.SERVICE_REQUEST):
        raise ValidationError({
            'phone_number': 'Verify this mobile number with a code before tracking.',
        })
    records = (
        DailyServiceRequest.objects.filter(
            Q(contact_phone=phone) | Q(customer__phone_number=phone)
        )
        .select_related('assigned_profile', 'assigned_profile__user', 'category', 'customer')
        .prefetch_related('assigned_profile__skills', 'assigned_profile__service_categories')
        .order_by('-created_at', '-pk')
    )
    return [guest_track_payload(record, request=request) for record in records]


def resolve_guest_owned_request(reference, *, access_key='', phone=''):
    """Resolve one guest/account request by access key or by a verified mobile number."""
    if isinstance(reference, bool) or not isinstance(reference, (int, str)):
        raise DailyServiceRequest.DoesNotExist
    try:
        pk = int(reference)
    except (TypeError, ValueError):
        raise DailyServiceRequest.DoesNotExist
    record = (
        DailyServiceRequest.objects.filter(pk=pk)
        .select_related('assigned_profile', 'assigned_profile__user', 'category', 'customer')
        .prefetch_related('assigned_profile__skills', 'assigned_profile__service_categories')
        .first()
    )
    if record is None:
        raise DailyServiceRequest.DoesNotExist
    if access_key and record.check_access_key(access_key):
        return record
    if phone and phone_controls_daily_request(record, phone):
        return record
    raise DailyServiceRequest.DoesNotExist
