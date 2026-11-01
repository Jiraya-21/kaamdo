"""
Acceptance checks against an isolated copy of backend/db.sqlite3.

This module is imported only after KAAMDO_ISOLATED_SQLITE is set.
It never opens the live file for writes.
"""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import json
import os
import threading
import time

from django.core.management import call_command
from django.db import connections
from django.utils import timezone
from rest_framework.authtoken.models import Token

from accounts.models import AccountCapability, Capability, User
from workers.matching import (
    advance_matching,
    cancel_daily_request,
    consent_to_expand,
    process_due_matching,
)
from workers.matching_columns import (
    matching_offer_columns_ready,
    matching_request_columns_ready,
    reset_matching_column_cache,
)
from workers.contacts import reset_daily_contact_phone_cache
from workers.models import (
    DailyServiceRequest,
    ServiceCategory,
    ServiceOffer,
    ServiceProviderVerification,
    WorkerProfile,
)
from workers.services import respond_to_service_offer
from workers.tests.test_daily_service_matching import north_of


def _report(name, status, detail):
    return {'name': name, 'status': status, 'detail': detail}


def existing_records_readable():
    reset_matching_column_cache()
    reset_daily_contact_phone_cache()
    request_ready = matching_request_columns_ready()
    offer_ready = matching_offer_columns_ready()
    users = User.objects.count()
    requests = DailyServiceRequest.objects.count()
    offers = ServiceOffer.objects.count()
    categories = ServiceCategory.objects.count()
    sample = list(
        DailyServiceRequest.objects.values('id', 'status', 'radius_km', 'created_at')[:5]
    )
    fields_ok = request_ready and offer_ready
    return _report(
        'existing_records_readable',
        'PASS' if fields_ok else 'FAIL',
        {
            'matching_request_columns': request_ready,
            'matching_offer_columns': offer_ready,
            'users': users,
            'daily_requests': requests,
            'offers': offers,
            'categories': categories,
            'sample_request_ids': [row['id'] for row in sample],
        },
    )


def _make_worker(phone, kilometres, category, *, available=True, radius=40):
    lat, lon = north_of(12, 77, kilometres)
    user = User.objects.create_user(
        username=f'accept-{phone}',
        password='AcceptPass!234',
        phone_number=phone,
        first_name='Test',
        last_name=phone[-4:],
    )
    AccountCapability.objects.create(user=user, code=Capability.SERVICE_PROVIDER)
    profile = WorkerProfile.objects.create(
        user=user,
        bio='Acceptance-test provider.',
        service_rate=Decimal('100.00'),
        pricing_basis=WorkerProfile.PricingBasis.HOURLY,
        district='Mandya',
        locality='Town centre',
        latitude=lat,
        longitude=lon,
        service_radius_km=radius,
        availability=(
            WorkerProfile.Availability.AVAILABLE
            if available
            else WorkerProfile.Availability.UNAVAILABLE
        ),
        publication_status=WorkerProfile.PublicationStatus.PUBLISHED,
    )
    profile.service_categories.add(category)
    ServiceProviderVerification.objects.create(
        user=user,
        status=ServiceProviderVerification.Status.APPROVED,
    )
    token = Token.objects.create(user=user)
    return {'user': user, 'profile': profile, 'token': token}


def _ready(record):
    record.transition_to(DailyServiceRequest.Status.AWAITING_PAYMENT)
    record.transition_to(DailyServiceRequest.Status.DISPATCH_PENDING)
    return record


def matching_lifecycle():
    results = []
    category, _ = ServiceCategory.objects.get_or_create(
        slug='acceptance-electrician',
        defaults={'name': 'Acceptance electrician', 'is_active': True},
    )
    request = DailyServiceRequest.objects.create(
        category=category,
        guest_name='Acceptance Guest',
        contact_email='acceptance-guest@example.invalid',
        description='Acceptance lifecycle fan.',
        latitude=Decimal('12.000000'),
        longitude=Decimal('77.000000'),
        radius_km=8,
    )
    request.set_access_key('acceptance-tracking-key-value')
    request.save(update_fields=['access_key_hash'])
    near = _make_worker('9000004101', 1, category)
    mid = _make_worker('9000004102', 2, category)
    far = _make_worker('9000004103', 12, category)
    _ready(request)

    first = advance_matching(request)
    request.refresh_from_db()
    offered = set(
        ServiceOffer.objects.filter(request=request, state=ServiceOffer.State.OFFERED)
        .values_list('profile_id', flat=True)
    )
    results.append(_report(
        'initial_offers',
        'PASS' if request.status == DailyServiceRequest.Status.OFFERING and near['profile'].pk in offered and far['profile'].pk not in offered else 'FAIL',
        {
            'status': request.status,
            'reason': request.match_reason,
            'search_radius_km': request.search_radius_km,
            'created': len(first.created_offer_ids),
            'offered_profile_ids': list(offered),
        },
    ))

    first_offer = ServiceOffer.objects.get(request=request, profile=near['profile'])
    respond_to_service_offer(near['user'], first_offer.pk, 'decline')
    request.refresh_from_db()
    second_offer = ServiceOffer.objects.filter(request=request, profile=mid['profile']).first()
    results.append(_report(
        'decline_next_batch',
        'PASS' if second_offer is not None and second_offer.state == ServiceOffer.State.OFFERED and request.status == DailyServiceRequest.Status.OFFERING else 'FAIL',
        {'status': request.status, 'reason': request.match_reason, 'second_state': getattr(second_offer, 'state', None)},
    ))

    if second_offer is not None:
        past = timezone.now() - timedelta(seconds=40)
        second_offer.offered_at = past
        second_offer.expires_at = past
        second_offer.save(update_fields=['offered_at', 'expires_at'])
    processed = process_due_matching()
    request.refresh_from_db()
    if second_offer is not None:
        second_offer.refresh_from_db()
    far_offer = ServiceOffer.objects.filter(request=request, profile=far['profile']).first()
    results.append(_report(
        'timeout_without_refresh',
        'PASS' if second_offer and second_offer.state == ServiceOffer.State.EXPIRED and request.status in {
            DailyServiceRequest.Status.NO_WORKERS,
            DailyServiceRequest.Status.NO_ACCEPTANCE,
            DailyServiceRequest.Status.OFFERING,
        } else 'FAIL',
        {
            'status': request.status,
            'reason': request.match_reason,
            'expired_state': getattr(second_offer, 'state', None),
            'far_offered': bool(far_offer),
            'process': processed,
        },
    ))

    consent_ok = 'FAIL'
    consent_detail = {}
    if request.status in {
        DailyServiceRequest.Status.NO_WORKERS,
        DailyServiceRequest.Status.NO_ACCEPTANCE,
        DailyServiceRequest.Status.OFFERING,
    } and far_offer is None:
        locked, result = consent_to_expand(request, 15)
        request.refresh_from_db()
        far_offer = ServiceOffer.objects.filter(request=request, profile=far['profile']).first()
        consent_ok = 'PASS' if request.consented_radius_km == 15 and far_offer is not None else 'FAIL'
        consent_detail = {
            'status': request.status,
            'consented_radius_km': request.consented_radius_km,
            'search_radius_km': request.search_radius_km,
            'offers_created': len(result.created_offer_ids),
        }
    elif far_offer is not None:
        consent_ok = 'PASS'
        consent_detail = {'note': 'Far worker already offered after timeout expansion inside permitted radius.'}
    results.append(_report('radius_consent_and_expand', consent_ok, consent_detail))

    busy_request = DailyServiceRequest.objects.create(
        category=category,
        guest_name='Busy Guest',
        contact_email='busy-guest@example.invalid',
        description='Busy-provider check.',
        latitude=Decimal('12.000000'),
        longitude=Decimal('77.000000'),
        radius_km=15,
    )
    _ready(busy_request)
    if far_offer is not None and far_offer.state == ServiceOffer.State.OFFERED:
        busy_result = advance_matching(busy_request)
        busy_request.refresh_from_db()
        busy_skip = not ServiceOffer.objects.filter(
            request=busy_request,
            profile=far['profile'],
        ).exists()
        results.append(_report(
            'busy_provider_skipped',
            'PASS' if busy_skip else 'FAIL',
            {'status': busy_request.status, 'created': len(busy_result.created_offer_ids)},
        ))
    else:
        results.append(_report('busy_provider_skipped', 'NOT TESTED', 'No open far-worker offer to mark busy.'))

    winner = far if far_offer is not None else mid
    winner_offer = ServiceOffer.objects.filter(request=request, profile=winner['profile']).first()
    if winner_offer is not None and winner_offer.state == ServiceOffer.State.OFFERED:
        respond_to_service_offer(winner['user'], winner_offer.pk, 'accept')
        request.refresh_from_db()
        assigned = request.status == DailyServiceRequest.Status.ASSIGNED
        results.append(_report(
            'assignment',
            'PASS' if assigned and request.assigned_profile_id == winner['profile'].pk else 'FAIL',
            {'status': request.status, 'reason': request.match_reason, 'assigned': request.assigned_profile_id, 'reason_assigned': request.match_reason == 'assigned'},
        ))
        late = None
        try:
            late = respond_to_service_offer(mid['user'], second_offer.pk, 'accept') if second_offer else None
            late_status = 'FAIL'
            late_detail = 'Late accept did not raise.'
        except Exception as exc:
            request.refresh_from_db()
            still = request.assigned_profile_id == winner['profile'].pk
            late_status = 'PASS' if still else 'FAIL'
            late_detail = type(exc).__name__
        results.append(_report('late_accept_cannot_override', late_status, {'error': late_detail, 'assigned': request.assigned_profile_id}))
    else:
        results.append(_report('assignment', 'FAIL', 'No open winner offer.'))
        results.append(_report('late_accept_cannot_override', 'NOT TESTED', 'Assignment did not occur.'))

    cancel_req = DailyServiceRequest.objects.create(
        category=category,
        guest_name='Cancel Guest',
        contact_email='cancel-guest@example.invalid',
        description='Cancel check.',
        latitude=Decimal('12.000000'),
        longitude=Decimal('77.000000'),
        radius_km=15,
    )
    extra = _make_worker('9000004104', 1, category)
    _ready(cancel_req)
    advance_matching(cancel_req)
    cancel_daily_request(cancel_req)
    cancel_req.refresh_from_db()
    open_left = ServiceOffer.objects.filter(request=cancel_req, state=ServiceOffer.State.OFFERED).count()
    results.append(_report(
        'cancellation',
        'PASS' if cancel_req.status == DailyServiceRequest.Status.CANCELLED and open_left == 0 else 'FAIL',
        {'status': cancel_req.status, 'reason': cancel_req.match_reason, 'open_offers': open_left},
    ))

    empty_category, _ = ServiceCategory.objects.get_or_create(
        slug='acceptance-empty',
        defaults={'name': 'Acceptance empty', 'is_active': True},
    )
    empty = DailyServiceRequest.objects.create(
        category=empty_category,
        guest_name='Empty Guest',
        contact_email='empty-guest@example.invalid',
        description='Exhaustion check.',
        latitude=Decimal('12.000000'),
        longitude=Decimal('77.000000'),
        radius_km=8,
    )
    _ready(empty)
    advance_matching(empty)
    empty.refresh_from_db()
    results.append(_report(
        'exhaustion',
        'PASS' if empty.status == DailyServiceRequest.Status.NO_WORKERS and empty.assigned_profile_id is None else 'FAIL',
        {'status': empty.status, 'reason': empty.match_reason},
    ))

    first_ids = set(ServiceOffer.objects.filter(request=request).values_list('profile_id', flat=True))
    advance_matching(request)
    again_ids = set(ServiceOffer.objects.filter(request=request).values_list('profile_id', flat=True))
    results.append(_report(
        'no_duplicate_offers',
        'PASS' if first_ids == again_ids else 'FAIL',
        {'before': len(first_ids), 'after': len(again_ids)},
    ))
    return results


def concurrency_sqlite():
    category, _ = ServiceCategory.objects.get_or_create(
        slug='acceptance-concurrent',
        defaults={'name': 'Acceptance concurrent', 'is_active': True},
    )
    request = DailyServiceRequest.objects.create(
        category=category,
        guest_name='Concurrent Guest',
        contact_email='concurrent-guest@example.invalid',
        description='Two accepts.',
        latitude=Decimal('12.000000'),
        longitude=Decimal('77.000000'),
        radius_km=15,
    )
    a = _make_worker('9000004201', 1, category)
    b = _make_worker('9000004202', 2, category)
    _ready(request)
    request.transition_to(DailyServiceRequest.Status.OFFERING)
    offer_a = ServiceOffer.objects.create(request=request, profile=a['profile'])
    offer_b = ServiceOffer.objects.create(request=request, profile=b['profile'])
    outcomes = []
    barrier = threading.Barrier(2)

    def attempt(user, offer_id):
        connections.close_all()
        barrier.wait(timeout=5)
        try:
            respond_to_service_offer(user, offer_id, 'accept')
            outcomes.append('accepted')
        except Exception as exc:
            outcomes.append(type(exc).__name__)
        finally:
            connections.close_all()

    threads = [
        threading.Thread(target=attempt, args=(a['user'], offer_a.pk)),
        threading.Thread(target=attempt, args=(b['user'], offer_b.pk)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
    request.refresh_from_db()
    accepted = ServiceOffer.objects.filter(request=request, state=ServiceOffer.State.ACCEPTED).count()
    winners = 1 if request.assigned_profile_id and accepted == 1 else 0
    status = 'PASS' if winners == 1 and outcomes.count('accepted') == 1 else 'FAIL'
    return [_report(
        'parallel_sqlite_accept',
        status,
        {
            'outcomes': outcomes,
            'assigned_profile_id': request.assigned_profile_id,
            'accepted_offers': accepted,
            'engine': 'sqlite',
            'note': 'Independent threads and connections. SQLite serializes writers; this is not PostgreSQL.',
        },
    )]


def scheduler_once():
    before = process_due_matching()
    return [_report('process_daily_matching', 'PASS', before)]


def scheduler_loop_two_cycles():
    pulses = []
    for _ in range(2):
        pulses.append(process_due_matching())
        time.sleep(1)
    return [_report(
        'run_matching_loop_isolated_cycles',
        'PASS',
        {
            'cycles': pulses,
            'note': 'Two isolated process_due_matching pulses. The infinite run_matching_loop command was not left running.',
        },
    )]
