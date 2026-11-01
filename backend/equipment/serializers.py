"""
Serializers for equipment listings and rental requests.
The signed-in user is taken from the request, not from the submitted body.
"""

from decimal import Decimal

from rest_framework import serializers

from accounts.models import OtpPurpose, phone_is_verified
from locations.places import place_taluk, save_place
from locations.validate import official_district, official_locality, official_taluk

from .models import (
    BookingStatus,
    EquipmentBooking,
    EquipmentInquiry,
    EquipmentListing,
    FeeStatus,
    InquiryStatus,
    ListingStatus,
)


def accepted_booking_overlaps(listing, start, end, exclude_pk=None):
    if not listing or not start or not end:
        return False
    qs = EquipmentBooking.objects.filter(
        listing=listing,
        status=BookingStatus.ACCEPTED,
        start_date__lte=end,
        end_date__gte=start,
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def clean_text(value, label, max_length):
    text = ' '.join(str(value).split())
    if not text:
        raise serializers.ValidationError(f'{label} is required.')
    if len(text) > max_length:
        raise serializers.ValidationError(f'{label} must be {max_length} characters or fewer.')
    return text


class EquipmentListingSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    taluk = serializers.CharField(required=False, allow_blank=True, max_length=120)

    class Meta:
        model = EquipmentListing
        fields = [
            'id',
            'title',
            'description',
            'district',
            'taluk',
            'locality',
            'pricing_basis',
            'rate',
            'operator_included',
            'availability_note',
            'fee_status',
            'status',
            'owner_name',
            'is_owner',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'owner_name', 'is_owner', 'fee_status', 'created_at', 'updated_at']

    def get_owner_name(self, obj):
        name = obj.owner.get_full_name().strip()
        return name or 'Equipment owner'

    def get_is_owner(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated and obj.owner_id == user.id)

    def validate_title(self, value):
        return clean_text(value, 'Title', 120)

    def validate_description(self, value):
        return clean_text(value, 'Description', 2000)

    def validate_district(self, value):
        return official_district(value)

    def validate_locality(self, value):
        return official_locality(value)

    def validate_rate(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError('The rate must be greater than zero.')
        return value

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        district = attrs.get('district', getattr(instance, 'district', ''))
        self._taluk = official_taluk(district, attrs.pop('taluk', None) or '')
        status = attrs.get('status', getattr(self.instance, 'status', ListingStatus.DRAFT))
        fee_status = getattr(self.instance, 'fee_status', FeeStatus.UNPAID)
        if status == ListingStatus.PUBLISHED and fee_status not in (FeeStatus.PAID, FeeStatus.WAIVED):
            raise serializers.ValidationError({
                'status': 'This advertisement stays private until KaamDo records the listing fee.',
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('taluk', None)
        instance = super().create(validated_data)
        save_place(instance, instance.district, getattr(self, '_taluk', ''), instance.locality)
        return instance

    def update(self, instance, validated_data):
        validated_data.pop('taluk', None)
        instance = super().update(instance, validated_data)
        save_place(
            instance,
            instance.district,
            getattr(self, '_taluk', place_taluk(instance)),
            instance.locality,
        )
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['taluk'] = place_taluk(instance)
        return data


class EquipmentBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentBooking
        fields = [
            'id',
            'listing',
            'start_date',
            'end_date',
            'note',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'listing', 'created_at', 'updated_at']

    def validate_note(self, value):
        text = ' '.join(str(value).split())
        if len(text) > 1000:
            raise serializers.ValidationError('Note must be 1000 characters or fewer.')
        return text

    def validate(self, attrs):
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end < start:
            raise serializers.ValidationError({'end_date': 'The end date cannot be before the start date.'})
        if self.instance is None:
            listing = self.context['listing']
            renter = self.context['request'].user
            if listing.status != ListingStatus.PUBLISHED:
                raise serializers.ValidationError('You can request only a published listing.')
            if EquipmentBooking.objects.filter(
                listing=listing,
                renter=renter,
                status=BookingStatus.REQUESTED,
            ).exists():
                raise serializers.ValidationError('You already have an open request for this listing.')
            if attrs.get('status', BookingStatus.REQUESTED) != BookingStatus.REQUESTED:
                raise serializers.ValidationError({'status': 'A new request starts as requested.'})
            if accepted_booking_overlaps(listing, start, end):
                raise serializers.ValidationError({
                    'start_date': 'Those dates overlap an accepted booking for this listing.',
                })
        return attrs

    def create(self, validated_data):
        validated_data['status'] = BookingStatus.REQUESTED
        return EquipmentBooking.objects.create(
            listing=self.context['listing'],
            renter=self.context['request'].user,
            **validated_data,
        )


class EquipmentInquirySerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source='listing.title', read_only=True)

    class Meta:
        model = EquipmentInquiry
        fields = [
            'id',
            'listing',
            'listing_title',
            'contact_phone',
            'requirement',
            'preferred_timing',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'listing', 'listing_title', 'contact_phone', 'created_at', 'updated_at']

    def validate_requirement(self, value):
        return clean_text(value, 'Requirement', 1000)

    def validate(self, attrs):
        request = self.context['request']
        listing = self.context.get('listing') or getattr(self.instance, 'listing', None)
        if self.instance is None:
            if listing is None or listing.status != ListingStatus.PUBLISHED:
                raise serializers.ValidationError('You can inquire only about a published advertisement.')
            if listing.fee_status not in (FeeStatus.PAID, FeeStatus.WAIVED):
                raise serializers.ValidationError('You can inquire only about a published advertisement.')
            phone = request.user.phone_number
            if not phone_is_verified(request.user, phone, OtpPurpose.EQUIPMENT_INQUIRY):
                raise serializers.ValidationError('Verify your mobile number before sending an inquiry.')
            attrs['contact_phone'] = phone
            if attrs.get('status', InquiryStatus.NEW) != InquiryStatus.NEW:
                raise serializers.ValidationError({'status': 'A new inquiry starts as new.'})
        elif attrs.get('status') not in (None, InquiryStatus.SEEN, InquiryStatus.CLOSED, self.instance.status):
            raise serializers.ValidationError({'status': 'Choose seen or closed.'})
        return attrs

    def create(self, validated_data):
        validated_data['status'] = InquiryStatus.NEW
        return EquipmentInquiry.objects.create(
            listing=self.context['listing'],
            customer=self.context['request'].user,
            **validated_data,
        )
