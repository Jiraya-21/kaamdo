"""
Worker profile API.
Workers manage their own profile. Anyone can read published profiles.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Capability
from .models import (
    DailyServiceRequest,
    ServiceCategory,
    ServiceOffer,
    ServiceProviderVerification,
    ServiceRequest,
    WorkerProfile,
)
from .matching import cancel_daily_request, consent_to_expand
from .services import (
    create_service_offers,
    customer_daily_request_payload,
    customer_daily_requests,
    describe_guest_request,
    guest_track_payload,
    list_requests_for_verified_phone,
    resolve_guest_owned_request,
    TEST_PAYMENT_LABEL,
    mock_visit_payment_enabled,
    payment_snapshot,
    price_menu_payload,
    propose_request_extras,
    provider_daily_offers,
    provider_offer_payload,
    public_worker_directory,
    published_worker_profiles,
    offer_workers_after_inspection_fee,
    record_mock_extra_payment,
    record_mock_visit_progress,
    respond_to_service_offer,
    user_may_mock_pay_request,
)
from .arrival import (
    customer_confirms_completion,
    customer_verifies_arrival,
    provider_signals_arrival,
)
from .permissions import IsMarketplaceUser, IsServiceProvider
from .photos import (
    PHOTO_MIGRATION_REQUIRED,
    clear_worker_photo,
    replace_worker_photo,
    worker_photo_column_ready,
)
from .serializers import (
    CustomerDailyServiceRequestSerializer,
    GuestDailyServiceRequestSerializer,
    PublicWorkerProfileSerializer,
    ServiceCategorySerializer,
    ServiceRequestSerializer,
    WorkerProfilePhotoSerializer,
    WorkerProfileSerializer,
)


def published_profiles():
    return published_worker_profiles()


def owned_guest_request(reference, access_key='', phone=''):
    return resolve_guest_owned_request(reference, access_key=access_key or '', phone=phone or '')


class ServiceCategoryListView(generics.ListAPIView):
    """Active daily-service categories. Login is not required."""

    permission_classes = [AllowAny]
    serializer_class = ServiceCategorySerializer
    queryset = ServiceCategory.objects.filter(is_active=True)


class GuestDailyServiceRequestCreateView(generics.CreateAPIView):
    """Create a guest request after the same mobile number or email has passed the service-request check."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]
    serializer_class = GuestDailyServiceRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        from .services import payment_snapshot
        return Response(
            {
                'detail': (
                    'Mobile verified. Pay the inspection fee next. '
                    'Workers are offered only after that fee is recorded.'
                ),
                'reference': record.pk,
                'status': record.status,
                'radius_km': record.radius_km,
                'access_key': serializer.access_key,
                'payment': payment_snapshot(record),
                'next_step': 'pay_inspection_fee',
            },
            status=status.HTTP_201_CREATED,
        )


class GuestDailyServiceRequestStatusView(APIView):
    """Read one request by access key (legacy) or by verified mobile + reference."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        access_key = request.data.get('access_key') or ''
        phone = request.data.get('phone_number') or ''
        try:
            if access_key:
                payload = describe_guest_request(
                    request.data.get('reference'),
                    access_key,
                    request=request,
                )
            else:
                record = resolve_guest_owned_request(
                    request.data.get('reference'),
                    phone=phone,
                )
                payload = guest_track_payload(record, request=request)
        except DailyServiceRequest.DoesNotExist:
            return Response(
                {'detail': 'Daily service request not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(payload)


class GuestDailyServiceRequestByPhoneView(APIView):
    """List every request tied to a mobile number after that number was OTP-verified."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            rows = list_requests_for_verified_phone(
                request.data.get('phone_number'),
                request=request,
            )
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'detail': 'Requests for this mobile number.',
            'phone_number': str(request.data.get('phone_number') or '').strip(),
            'count': len(rows),
            'requests': rows,
        })


class DailyServiceMatchView(APIView):
    """Staff create offers for one existing daily-service request. A request number is not enough."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, pk):
        record = DailyServiceRequest.objects.filter(pk=pk).first()
        if record is None:
            return Response({'detail': 'Daily service request not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            result = create_service_offers(record)
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        record.refresh_from_db()
        if result.eligible_count == 0:
            detail = 'No eligible workers were found.'
        else:
            detail = 'Offers are ready for the eligible workers.'
        return Response(
            {
                'detail': detail,
                'reference': record.pk,
                'status': record.status,
                'eligible_count': result.eligible_count,
                'offers_created': len(result.created_offer_ids),
                'offers_already_present': len(result.existing_offer_ids),
                'match_reason': result.reason,
                'search_radius_km': result.search_radius_km,
            }
        )


class DailyServiceExpandView(APIView):
    """Customer or guest agrees to a wider search. No fee or arrival time is invented."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, pk=None):
        record = self._record(request, pk)
        if record is None:
            return Response({'detail': 'Daily service request not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            record, result = consent_to_expand(record, request.data.get('radius_km'))
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        payload = {
            'detail': (
                'A wider search was agreed. A farther worker may take longer. '
                'This does not add a travel fee and does not promise an arrival time.'
            ),
            'reference': record.pk,
            'status': record.status,
            'radius_km': record.radius_km,
            'match_reason': result.reason,
            'search_radius_km': result.search_radius_km,
            'offers_created': len(result.created_offer_ids),
        }
        return Response(payload)

    def _record(self, request, pk):
        if pk is not None:
            if not request.user or not request.user.is_authenticated:
                return None
            return DailyServiceRequest.objects.filter(pk=pk, customer=request.user).first()
        try:
            return owned_guest_request(
                request.data.get('reference'),
                access_key=request.data.get('access_key') or '',
                phone=request.data.get('phone_number') or '',
            )
        except DailyServiceRequest.DoesNotExist:
            return None


class DailyServiceCancelView(APIView):
    """Customer or guest cancels an unassigned or assigned-but-not-started request."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, pk=None):
        record = DailyServiceExpandView()._record(request, pk)
        if record is None:
            return Response({'detail': 'Daily service request not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            record = cancel_daily_request(record)
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'detail': 'Request cancelled. No worker is assigned.',
            'reference': record.pk,
            'status': record.status,
        })


class PriceMenuView(APIView):
    """Public company price menu: inspection fee + extras."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(price_menu_payload())


class MockVisitPaymentView(APIView):
    """Mock Razorpay-style inspection payment. Does not receive money."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        record = DailyServiceRequest.objects.filter(pk=pk).first()
        if record is None:
            return Response({'detail': 'Daily service request not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user_may_mock_pay_request(request.user, record):
            return Response(
                {'detail': 'Only the request owner or staff can record this mock payment.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not mock_visit_payment_enabled():
            return Response(
                {'detail': 'Mock visit payment is not enabled. No payment was recorded.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            record, payment = record_mock_visit_progress(record)
            record = offer_workers_after_inspection_fee(record)
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'detail': TEST_PAYMENT_LABEL,
                'test_mode': True,
                'provider': 'razorpay_mock',
                'money_received': False,
                'reference': record.pk,
                'status': record.status,
                'payment_state': payment.state,
                'verification_source': payment.verification_source,
                'amount_inr': format(payment.amount_inr, 'f'),
                'payment': payment_snapshot(record),
                'next_step': 'workers_offered',
            }
        )


class GuestMockVisitPaymentView(APIView):
    """Guest mock inspection payment with access key or verified mobile + reference."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not mock_visit_payment_enabled():
            return Response(
                {'detail': 'Mock visit payment is not enabled. No payment was recorded.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            record = resolve_guest_owned_request(
                request.data.get('reference'),
                access_key=request.data.get('access_key') or '',
                phone=request.data.get('phone_number') or '',
            )
        except DailyServiceRequest.DoesNotExist:
            return Response(
                {'detail': 'Request not found for that mobile number or key.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            record, payment = record_mock_visit_progress(record)
            record = offer_workers_after_inspection_fee(record)
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'detail': TEST_PAYMENT_LABEL,
                'test_mode': True,
                'provider': 'razorpay_mock',
                'money_received': False,
                'reference': record.pk,
                'status': record.status,
                'payment_state': payment.state,
                'amount_inr': format(payment.amount_inr, 'f'),
                'payment': payment_snapshot(record),
                'next_step': 'workers_offered',
            }
        )


class ProposeRequestExtrasView(APIView):
    """Assigned worker adds company-menu extras after inspection."""

    permission_classes = [IsAuthenticated, IsServiceProvider]

    def post(self, request, pk):
        record = DailyServiceRequest.objects.filter(pk=pk).first()
        if record is None:
            return Response({'detail': 'Daily service request not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            created = propose_request_extras(record, request.user, request.data.get('items') or [])
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'detail': 'Extras added from the company menu. Waiting for mock payment.',
            'reference': record.pk,
            'payment': payment_snapshot(record),
            'added': [
                {'id': row.pk, 'title': row.title, 'amount_inr': format(row.amount_inr, 'f')}
                for row in created
            ],
        })


class MockExtraPaymentView(APIView):
    """Customer/staff mock-pay proposed extras. Does not receive money."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        record = DailyServiceRequest.objects.filter(pk=pk).first()
        if record is None:
            return Response({'detail': 'Daily service request not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not user_may_mock_pay_request(request.user, record):
            return Response(
                {'detail': 'Only the request owner or staff can record this mock payment.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not mock_visit_payment_enabled():
            return Response(
                {'detail': 'Mock visit payment is not enabled. No payment was recorded.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            rows = record_mock_extra_payment(record)
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        from decimal import Decimal
        total = sum((row.amount_inr for row in rows), Decimal('0.00'))
        return Response({
            'detail': TEST_PAYMENT_LABEL,
            'test_mode': True,
            'provider': 'razorpay_mock',
            'money_received': False,
            'reference': record.pk,
            'amount_inr': format(total, 'f'),
            'payment': payment_snapshot(record),
        })


class GuestMockExtraPaymentView(APIView):
    """Guest mock-pay extras with access key or verified mobile + reference."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not mock_visit_payment_enabled():
            return Response(
                {'detail': 'Mock visit payment is not enabled. No payment was recorded.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            record = resolve_guest_owned_request(
                request.data.get('reference'),
                access_key=request.data.get('access_key') or '',
                phone=request.data.get('phone_number') or '',
            )
        except DailyServiceRequest.DoesNotExist:
            return Response(
                {'detail': 'Request not found for that mobile number or key.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            rows = record_mock_extra_payment(record)
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        from decimal import Decimal
        total = sum((row.amount_inr for row in rows), Decimal('0.00'))
        return Response({
            'detail': TEST_PAYMENT_LABEL,
            'test_mode': True,
            'provider': 'razorpay_mock',
            'money_received': False,
            'reference': record.pk,
            'amount_inr': format(total, 'f'),
            'payment': payment_snapshot(record),
        })


class ServiceOfferResponseView(APIView):
    """The worker who received an offer accepts or declines it."""

    permission_classes = [IsAuthenticated, IsServiceProvider]

    def post(self, request, offer_id):
        try:
            offer = respond_to_service_offer(
                request.user,
                offer_id,
                request.data.get('decision'),
            )
        except ServiceOffer.DoesNotExist:
            return Response({'detail': 'Offer not found.'}, status=status.HTTP_404_NOT_FOUND)
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        if offer.state == ServiceOffer.State.ACCEPTED:
            detail = 'You accepted this request.'
        else:
            detail = 'You declined this request.'
        return Response(
            {
                'detail': detail,
                'state': offer.state,
                'request_status': offer.request.status,
            }
        )


class MyDailyServiceRequestListView(APIView):
    """Signed-in account's own daily requests. No professional role required. Guest keys stay off this list."""

    permission_classes = [IsAuthenticated, IsMarketplaceUser]

    def get(self, request):
        records = customer_daily_requests(request.user)
        return Response([
            customer_daily_request_payload(record, request=request) for record in records
        ])

    def post(self, request):
        serializer = CustomerDailyServiceRequestSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        payload = customer_daily_request_payload(record, request=request)
        payload['detail'] = (
            'Mobile on account checked. Pay the inspection fee next. '
            'Workers are offered only after that fee.'
        )
        payload['next_step'] = 'pay_inspection_fee'
        return Response(payload, status=status.HTTP_201_CREATED)


class MyServiceOfferListView(APIView):
    """Offers belonging to the signed-in worker. Another worker's offers are omitted."""

    permission_classes = [IsAuthenticated, IsServiceProvider]

    def get(self, request):
        offers = provider_daily_offers(request.user)
        return Response([provider_offer_payload(offer) for offer in offers])


class PublishedWorkerListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicWorkerProfileSerializer

    def get_queryset(self):
        return published_profiles()

    def list(self, request, *args, **kwargs):
        try:
            profiles = public_worker_directory(request.query_params)
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        page = self.paginate_queryset(profiles)
        serializer = self.get_serializer(page if page is not None else profiles, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class PublishedWorkerDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicWorkerProfileSerializer
    queryset = published_profiles()


class OwnWorkerProfileView(APIView):
    permission_classes = [IsAuthenticated, IsServiceProvider]

    def get_profile(self, user):
        return (
            WorkerProfile.objects.select_related('user')
            .prefetch_related('skills', 'service_categories')
            .filter(user=user)
            .first()
        )

    def serialized(self, profile, request):
        return WorkerProfileSerializer(profile, context={'request': request}).data

    def get(self, request):
        profile = self.get_profile(request.user)
        if profile is None:
            return Response({'detail': 'Worker profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.serialized(profile, request))

    def post(self, request):
        if self.get_profile(request.user) is not None:
            return Response(
                {'detail': 'A worker profile already exists.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = WorkerProfileSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(user=request.user)
        return Response(self.serialized(profile, request), status=status.HTTP_201_CREATED)

    def put(self, request):
        return self._update(request, partial=False)

    def patch(self, request):
        return self._update(request, partial=True)

    def _update(self, request, partial):
        profile = self.get_profile(request.user)
        if profile is None:
            return Response({'detail': 'Worker profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = WorkerProfileSerializer(
            profile,
            data=request.data,
            partial=partial,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(self.serialized(profile, request))


class OwnWorkerProfilePhotoView(APIView):
    """Owner-only photo replace or remove. Customers and other providers cannot use this."""

    permission_classes = [IsAuthenticated, IsServiceProvider]
    parser_classes = [MultiPartParser, FormParser]

    def get_profile(self, user):
        return (
            WorkerProfile.objects.select_related('user')
            .prefetch_related('skills', 'service_categories')
            .filter(user=user)
            .first()
        )

    def serialized(self, profile, request):
        return WorkerProfileSerializer(profile, context={'request': request}).data

    def unavailable(self):
        return Response(
            {'detail': PHOTO_MIGRATION_REQUIRED},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    def post(self, request):
        if not worker_photo_column_ready():
            return self.unavailable()
        profile = self.get_profile(request.user)
        if profile is None:
            return Response({'detail': 'Worker profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = WorkerProfilePhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            replace_worker_photo(profile, serializer.validated_data['photo'])
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages[0] if exc.messages else PHOTO_MIGRATION_REQUIRED}, status=status.HTTP_400_BAD_REQUEST)
        profile = self.get_profile(request.user)
        return Response(self.serialized(profile, request))

    def delete(self, request):
        if not worker_photo_column_ready():
            return self.unavailable()
        profile = self.get_profile(request.user)
        if profile is None:
            return Response({'detail': 'Worker profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            clear_worker_photo(profile)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages[0] if exc.messages else PHOTO_MIGRATION_REQUIRED}, status=status.HTTP_400_BAD_REQUEST)
        profile = self.get_profile(request.user)
        return Response(self.serialized(profile, request))


class ServiceProviderVerificationView(APIView):
    """Submit the provider application. The applicant cannot approve it."""

    permission_classes = [IsAuthenticated, IsServiceProvider]

    def get_record(self, user):
        record, _created = ServiceProviderVerification.objects.get_or_create(user=user)
        return record

    def get(self, request):
        record = ServiceProviderVerification.objects.filter(user=request.user).first()
        if record is None:
            return Response({
                'status': ServiceProviderVerification.Status.NOT_SUBMITTED,
                'applicant_note': '',
                'review_note': '',
                'submitted_at': None,
                'reviewed_at': None,
            })
        return Response(self._payload(record))

    def post(self, request):
        if not WorkerProfile.objects.filter(user=request.user).exists():
            return Response(
                {'detail': 'Complete your service provider profile before submitting verification.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        note = request.data.get('applicant_note', '')
        if not isinstance(note, str):
            return Response(
                {'applicant_note': ['Enter a short note or leave it blank.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(note) > 1000:
            return Response(
                {'applicant_note': ['Keep the note to 1000 characters or fewer.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        record = self.get_record(request.user)
        if record.status == ServiceProviderVerification.Status.PENDING:
            return Response(
                {'detail': 'Verification is already pending review.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if record.status == ServiceProviderVerification.Status.APPROVED:
            return Response(
                {'detail': 'Verification is already approved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        record.applicant_note = note.strip()
        record.status = ServiceProviderVerification.Status.PENDING
        record.submitted_at = timezone.now()
        record.reviewed_at = None
        record.reviewed_by = None
        record.save()
        return Response(self._payload(record))

    def _payload(self, record):
        return {
            'status': record.status,
            'applicant_note': record.applicant_note,
            'review_note': record.review_note,
            'submitted_at': record.submitted_at,
            'reviewed_at': record.reviewed_at,
        }


class ServiceRequestListCreateView(generics.ListCreateAPIView):
    """Signed-in accounts create and list their own direct provider requests. No Customer role required."""

    serializer_class = ServiceRequestSerializer
    permission_classes = [IsAuthenticated, IsMarketplaceUser]

    def get_queryset(self):
        return ServiceRequest.objects.filter(customer=self.request.user).select_related('profile', 'profile__user')

    def perform_create(self, serializer):
        serializer.save()


class IncomingServiceRequestListView(generics.ListAPIView):
    serializer_class = ServiceRequestSerializer
    permission_classes = [IsAuthenticated, IsServiceProvider]

    def get_queryset(self):
        return ServiceRequest.objects.filter(profile__user=self.request.user).select_related('profile', 'profile__user')


class ServiceRequestDetailView(APIView):
    permission_classes = [IsAuthenticated, IsServiceProvider]

    def patch(self, request, pk):
        service_request = ServiceRequest.objects.filter(pk=pk, profile__user=request.user).first()
        if service_request is None:
            return Response({'detail': 'Service request not found.'}, status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get('status')
        allowed = {
            ServiceRequest.Status.REQUESTED: {
                ServiceRequest.Status.ACCEPTED,
                ServiceRequest.Status.DECLINED,
            },
            ServiceRequest.Status.ACCEPTED: {ServiceRequest.Status.CLOSED},
        }
        if new_status not in allowed.get(service_request.status, set()):
            return Response({'status': ['That status change is not allowed.']}, status=status.HTTP_400_BAD_REQUEST)
        service_request.status = new_status
        service_request.save(update_fields=['status', 'updated_at'])
        return Response(ServiceRequestSerializer(service_request, context={'request': request}).data)


def _owned_daily_request(request, pk=None):
    """Resolve a daily request by signed-in owner, access key, or verified mobile number."""
    if pk is None:
        raw = request.data.get('reference')
        try:
            pk = int(raw)
        except (TypeError, ValueError):
            return None
    record = (
        DailyServiceRequest.objects.filter(pk=pk)
        .select_related('assigned_profile', 'assigned_profile__user', 'category', 'customer')
        .prefetch_related('assigned_profile__skills', 'assigned_profile__service_categories')
        .first()
    )
    if record is None:
        return None
    user = request.user
    if user and user.is_authenticated and record.customer_id == user.id:
        return record
    access_key = request.data.get('access_key') or ''
    if access_key and record.check_access_key(access_key):
        return record
    phone = request.data.get('phone_number') or ''
    from .services import phone_controls_daily_request
    if phone and phone_controls_daily_request(record, phone):
        return record
    return None


class DailyServiceArrivalSignalView(APIView):
    """Assigned provider signals arrival and receives a booking-specific code. Does not verify arrival."""

    permission_classes = [IsAuthenticated, IsServiceProvider]

    def post(self, request, pk):
        record = DailyServiceRequest.objects.filter(pk=pk).select_related('assigned_profile').first()
        if record is None:
            return Response({'detail': 'Daily service request not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            payload = provider_signals_arrival(record, provider_user=request.user)
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload)


class DailyServiceArrivalVerifyView(APIView):
    """Request owner confirms the arriving person with the booking code. Login OTPs are not accepted."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, pk=None):
        record = _owned_daily_request(request, pk)
        if record is None:
            return Response({'detail': 'Daily service request not found.'}, status=status.HTTP_404_NOT_FOUND)
        user = request.user if request.user and request.user.is_authenticated else None
        try:
            updated = customer_verifies_arrival(
                record,
                code=request.data.get('code'),
                user=user,
                access_key=request.data.get('access_key') or '',
            )
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        payload = customer_daily_request_payload(updated, request=request)
        payload['detail'] = 'Arrival verified. The visit may proceed.'
        return Response(payload)


class DailyServiceCompleteView(APIView):
    """Request owner confirms completion after verified arrival. Keeps the assigned worker link."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, pk=None):
        record = _owned_daily_request(request, pk)
        if record is None:
            return Response({'detail': 'Daily service request not found.'}, status=status.HTTP_404_NOT_FOUND)
        user = request.user if request.user and request.user.is_authenticated else None
        try:
            updated = customer_confirms_completion(
                record,
                user=user,
                access_key=request.data.get('access_key') or '',
            )
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        payload = customer_daily_request_payload(updated, request=request)
        payload['detail'] = 'Service marked completed for the assigned worker.'
        return Response(payload)
