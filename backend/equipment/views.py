"""
API for equipment listings and rental requests.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Capability
from .models import (
    BookingStatus,
    EquipmentBooking,
    EquipmentInquiry,
    EquipmentListing,
    FeeStatus,
    ListingStatus,
    PricingBasis,
)
from .permissions import IsCustomer, IsEquipmentOwner, IsEquipmentRenter
from .photos import clear_equipment_photo, replace_equipment_photo
from .serializers import (
    EquipmentBookingSerializer,
    EquipmentInquirySerializer,
    EquipmentListingPhotoSerializer,
    EquipmentListingSerializer,
)


def public_listings():
    return EquipmentListing.objects.filter(
        status=ListingStatus.PUBLISHED,
        fee_status__in=(FeeStatus.PAID, FeeStatus.WAIVED),
    )


def public_equipment(params):
    """Published, paid or waived advertisements. Filters run before pagination.

    Drafts stay off this list even when the visitor owns them. An owner id in the
    query is ignored. pricing_basis must be hourly or daily. operator_included
    must be true or false when it is sent.
    """
    rows = public_listings()
    district = str(params.get('district') or '').strip()
    query = str(params.get('q') or '').strip()
    pricing = str(params.get('pricing_basis') or '').strip()
    operator = str(params.get('operator_included') or '').strip().lower()
    if district:
        rows = rows.filter(district__iexact=district)
    if query:
        rows = rows.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(district__icontains=query)
            | Q(locality__icontains=query)
        )
    if pricing:
        allowed = {choice.value for choice in PricingBasis}
        if pricing not in allowed:
            raise DjangoValidationError({'pricing_basis': 'Choose hourly or daily.'})
        rows = rows.filter(pricing_basis=pricing)
    if operator:
        if operator not in ('true', 'false'):
            raise DjangoValidationError({'operator_included': 'Choose true or false.'})
        rows = rows.filter(operator_included=(operator == 'true'))
    return rows


class EquipmentListingListCreateView(generics.ListCreateAPIView):
    serializer_class = EquipmentListingSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsEquipmentOwner()]
        return [AllowAny()]

    def get_queryset(self):
        return public_equipment(self.request.query_params).select_related('owner')

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class MyEquipmentListingListView(generics.ListAPIView):
    """Listings owned by the signed-in user, including drafts. An owner id in the query is ignored."""

    serializer_class = EquipmentListingSerializer
    permission_classes = [IsAuthenticated, IsEquipmentOwner]

    def get_queryset(self):
        return EquipmentListing.objects.filter(owner=self.request.user).select_related('owner')


class EquipmentListingDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EquipmentListingSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsEquipmentOwner()]

    def get_queryset(self):
        published = public_listings()
        user = self.request.user
        if user.is_authenticated:
            own = EquipmentListing.objects.filter(owner=user)
            return (published | own).distinct().select_related('owner')
        return published.select_related('owner')

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and obj.owner_id != request.user.id:
            raise PermissionDenied('You can manage only your own listing.')


class ListingBookingView(APIView):
    """The listing owner lists requests. A renter creates one."""

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsEquipmentRenter()]
        return [IsAuthenticated(), IsEquipmentOwner()]

    def get_listing(self):
        return get_object_or_404(EquipmentListing, pk=self.kwargs['listing_pk'])

    def get(self, request, listing_pk):
        listing = self.get_listing()
        if listing.owner_id != request.user.id:
            raise Http404()
        bookings = listing.bookings.select_related('renter')
        return Response(EquipmentBookingSerializer(bookings, many=True).data)

    def post(self, request, listing_pk):
        listing = self.get_listing()
        serializer = EquipmentBookingSerializer(
            data=request.data,
            context={'request': request, 'listing': listing},
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(EquipmentBookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class MyEquipmentBookingListView(generics.ListAPIView):
    serializer_class = EquipmentBookingSerializer
    permission_classes = [IsAuthenticated, IsEquipmentRenter]

    def get_queryset(self):
        return EquipmentBooking.objects.filter(renter=self.request.user).select_related('listing')


class EquipmentBookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_booking(self, pk):
        return get_object_or_404(
            EquipmentBooking.objects.select_related('listing', 'renter'),
            pk=pk,
        )

    def get(self, request, pk):
        booking = self.get_booking(pk)
        if not self._can_view(request.user, booking):
            raise Http404()
        return Response(EquipmentBookingSerializer(booking).data)

    def patch(self, request, pk):
        booking = self.get_booking(pk)
        user = request.user
        if booking.listing.owner_id == user.id and user.has_capability(Capability.EQUIPMENT_OWNER):
            return self._owner_decision(request, booking)
        if booking.renter_id == user.id and user.has_capability(Capability.EQUIPMENT_RENTER):
            return self._renter_update(request, booking)
        raise Http404()

    def delete(self, request, pk):
        booking = self.get_booking(pk)
        if booking.renter_id != request.user.id or not request.user.has_capability(Capability.EQUIPMENT_RENTER):
            raise Http404()
        if booking.status != BookingStatus.REQUESTED:
            return Response(
                {'detail': 'This booking can no longer be removed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        booking.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _can_view(self, user, booking):
        return booking.renter_id == user.id or booking.listing.owner_id == user.id

    def _owner_decision(self, request, booking):
        if booking.status != BookingStatus.REQUESTED:
            return Response(
                {'detail': 'This request has already been decided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        decision = request.data.get('status')
        if decision not in (BookingStatus.ACCEPTED, BookingStatus.DECLINED):
            return Response(
                {'status': ['Choose accepted or declined.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if decision == BookingStatus.ACCEPTED:
            from .serializers import accepted_booking_overlaps
            if accepted_booking_overlaps(
                booking.listing,
                booking.start_date,
                booking.end_date,
                exclude_pk=booking.pk,
            ):
                return Response(
                    {'start_date': ['Those dates overlap an accepted booking for this listing.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        booking.status = decision
        booking.save(update_fields=['status', 'updated_at'])
        return Response(EquipmentBookingSerializer(booking).data)

    def _renter_update(self, request, booking):
        if booking.status != BookingStatus.REQUESTED:
            return Response(
                {'detail': 'This request can no longer be changed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if 'status' in request.data and request.data.get('status') != BookingStatus.REQUESTED:
            return Response(
                {'status': ['Only the listing owner can accept or decline a request.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = EquipmentBookingSerializer(
            booking,
            data=request.data,
            partial=True,
            context={'request': request, 'listing': booking.listing},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(EquipmentBookingSerializer(serializer.instance).data)


class MyEquipmentInquiryListView(generics.ListAPIView):
    serializer_class = EquipmentInquirySerializer
    permission_classes = [IsAuthenticated, IsCustomer]

    def get_queryset(self):
        return EquipmentInquiry.objects.filter(customer=self.request.user).select_related('listing')


class ListingInquiryView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsCustomer()]
        return [IsAuthenticated(), IsEquipmentOwner()]

    def get_listing(self):
        return get_object_or_404(EquipmentListing, pk=self.kwargs['listing_pk'])

    def get(self, request, listing_pk):
        listing = self.get_listing()
        if listing.owner_id != request.user.id:
            raise Http404()
        inquiries = listing.inquiries.select_related('listing')
        return Response(EquipmentInquirySerializer(
            inquiries,
            many=True,
            context={'request': request, 'listing': listing},
        ).data)

    def post(self, request, listing_pk):
        listing = self.get_listing()
        serializer = EquipmentInquirySerializer(
            data=request.data,
            context={'request': request, 'listing': listing},
        )
        serializer.is_valid(raise_exception=True)
        inquiry = serializer.save()
        return Response(
            EquipmentInquirySerializer(inquiry, context={'request': request, 'listing': listing}).data,
            status=status.HTTP_201_CREATED,
        )


class EquipmentInquiryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        inquiry = get_object_or_404(EquipmentInquiry.objects.select_related('listing'), pk=pk)
        user = request.user
        if inquiry.listing.owner_id != user.id or not user.has_capability(Capability.EQUIPMENT_OWNER):
            raise Http404()
        serializer = EquipmentInquirySerializer(
            inquiry,
            data=request.data,
            partial=True,
            context={'request': request, 'listing': inquiry.listing},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(EquipmentInquirySerializer(
            serializer.instance,
            context={'request': request, 'listing': inquiry.listing},
        ).data)


class EquipmentListingPhotoView(APIView):
    """Owner-only listing photo replace or remove."""

    permission_classes = [IsAuthenticated, IsEquipmentOwner]
    parser_classes = [MultiPartParser, FormParser]

    def get_listing(self, request, pk):
        listing = get_object_or_404(EquipmentListing, pk=pk)
        if listing.owner_id != request.user.id:
            raise Http404()
        return listing

    def serialized(self, listing, request):
        return EquipmentListingSerializer(listing, context={'request': request}).data

    def post(self, request, pk):
        listing = self.get_listing(request, pk)
        serializer = EquipmentListingPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            replace_equipment_photo(listing, serializer.validated_data['photo'])
        except DjangoValidationError as exc:
            detail = exc.messages[0] if getattr(exc, 'messages', None) else 'Could not save the photo.'
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        listing.refresh_from_db()
        return Response(self.serialized(listing, request))

    def delete(self, request, pk):
        listing = self.get_listing(request, pk)
        clear_equipment_photo(listing)
        listing.refresh_from_db()
        return Response(self.serialized(listing, request))
