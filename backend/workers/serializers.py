"""
Worker profile serialization.
Public responses omit account secrets such as phone number, email, and password.
"""

import secrets
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from accounts.models import (
    OtpPurpose,
    PHONE_PATTERN,
    GuestEmailVerification,
    GuestPhoneVerification,
    consume_guest_email_verification,
    consume_guest_phone_verification,
    guest_email_is_verified,
    guest_phone_is_verified,
    guest_phone_table_ready,
    normalize_phone,
    phone_is_verified,
)

from .models import (
    DailyServiceRequest,
    ServiceCategory,
    ServiceRequest,
    Skill,
    WorkerProfile,
    service_provider_can_publish,
)
from locations.places import place_taluk, save_place
from locations.validate import official_district, official_locality, official_taluk

from .photos import public_photo_url, validate_worker_photo


class CoordinateField(serializers.DecimalField):
    """Store map coordinates at 6 decimal places.

    Phone GPS often has more digits than the database field allows. Round first
    so auto-fetched locations are not rejected for precision.
    """

    QUANTUM = Decimal('0.000001')

    def __init__(self, **kwargs):
        kwargs.setdefault('max_digits', 9)
        kwargs.setdefault('decimal_places', 6)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if data in (None, ''):
            return super().to_internal_value(data)
        try:
            value = Decimal(str(data).strip())
        except (InvalidOperation, TypeError, ValueError, ArithmeticError):
            self.fail('invalid')
        if not value.is_finite():
            self.fail('invalid')
        rounded = value.quantize(self.QUANTUM, rounding=ROUND_HALF_EVEN)
        return super().to_internal_value(format(rounded, 'f'))


PUBLIC_FIELDS = [
    'id',
    'display_name',
    'skills',
    'experience_years',
    'bio',
    'service_rate',
    'pricing_basis',
    'district',
    'taluk',
    'locality',
    'service_radius_km',
    'availability',
    'service_categories',
    'photo_url',
    'updated_at',
]


def clean_skill_name(value):
    return ' '.join(str(value).split())


def resolve_skills(names):
    skills = []
    seen = set()
    for name in names:
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        existing = Skill.objects.filter(name__iexact=name).first()
        skills.append(existing or Skill.objects.create(name=name))
    return skills


def save_clean(profile):
    try:
        profile.full_clean()
    except DjangoValidationError as exc:
        if getattr(exc, 'message_dict', None):
            raise serializers.ValidationError(exc.message_dict) from exc
        raise serializers.ValidationError(exc.messages) from exc
    profile.save()


class SkillNameListField(serializers.Field):
    def to_representation(self, value):
        return list(value.order_by('name').values_list('name', flat=True))

    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError('Provide skills as a list of names.')
        names = []
        for item in data:
            if not isinstance(item, str):
                raise serializers.ValidationError('Each skill must be text.')
            name = clean_skill_name(item)
            if not name:
                raise serializers.ValidationError('Skill names cannot be blank.')
            if len(name) > 80:
                raise serializers.ValidationError('Skill names must be 80 characters or fewer.')
            names.append(name)
        if not names:
            raise serializers.ValidationError('Add at least one skill.')
        if len({name.casefold() for name in names}) > 20:
            raise serializers.ValidationError('A profile can list at most 20 skills.')
        return names


class ServiceCategorySlugListField(serializers.Field):
    """Active service-category slugs. Skills are not copied into this list."""

    def to_representation(self, value):
        return list(
            value.filter(is_active=True).order_by('name').values_list('slug', flat=True)
        )

    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError('Provide service categories as a list of slugs.')
        categories = []
        seen = set()
        for item in data:
            if not isinstance(item, str):
                raise serializers.ValidationError('Each service category must be a slug.')
            slug = ' '.join(item.split())
            if not slug:
                raise serializers.ValidationError('Service category slugs cannot be blank.')
            key = slug.casefold()
            if key in seen:
                raise serializers.ValidationError('Repeat a service category only once.')
            seen.add(key)
            category = ServiceCategory.objects.filter(is_active=True, slug__iexact=slug).first()
            if category is None:
                raise serializers.ValidationError('Choose an active service category.')
            categories.append(category)
        if len(categories) > 20:
            raise serializers.ValidationError('A profile can list at most 20 service categories.')
        return categories


class PublicWorkerProfileSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    skills = SkillNameListField(read_only=True)
    service_categories = ServiceCategorySlugListField(read_only=True)
    photo_url = serializers.SerializerMethodField()
    taluk = serializers.SerializerMethodField()

    class Meta:
        model = WorkerProfile
        fields = PUBLIC_FIELDS
        read_only_fields = fields

    def get_photo_url(self, obj):
        return public_photo_url(obj, self.context.get('request'))

    def get_taluk(self, obj):
        return place_taluk(obj)


class WorkerProfileSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    skills = SkillNameListField()
    service_categories = ServiceCategorySlugListField(required=False)
    photo_url = serializers.SerializerMethodField()
    taluk = serializers.CharField(required=False, allow_blank=True, max_length=120)
    latitude = CoordinateField(required=False, allow_null=True)
    longitude = CoordinateField(required=False, allow_null=True)

    class Meta:
        model = WorkerProfile
        fields = PUBLIC_FIELDS + ['publication_status', 'created_at', 'latitude', 'longitude']
        read_only_fields = ['id', 'display_name', 'photo_url', 'created_at', 'updated_at']
        extra_kwargs = {
            'experience_years': {'required': False},
            'service_radius_km': {'required': False},
            'availability': {'required': False},
            'publication_status': {'required': False},
        }

    def get_photo_url(self, obj):
        return public_photo_url(obj, self.context.get('request'))

    def validate_bio(self, value):
        bio = ' '.join(value.split())
        if not bio:
            raise serializers.ValidationError('A short description is required.')
        if len(bio) > 500:
            raise serializers.ValidationError('The description must be 500 characters or fewer.')
        return bio

    def validate_district(self, value):
        return official_district(value)

    def validate_locality(self, value):
        return official_locality(value)

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        district = attrs.get('district', getattr(instance, 'district', ''))
        taluk = official_taluk(district, attrs.pop('taluk', None) or '')
        self._taluk = taluk
        latitude = attrs['latitude'] if 'latitude' in attrs else getattr(instance, 'latitude', None)
        longitude = attrs['longitude'] if 'longitude' in attrs else getattr(instance, 'longitude', None)
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError('Latitude and longitude must be provided together.')
        if latitude is not None and not (Decimal('-90') <= latitude <= Decimal('90')):
            raise serializers.ValidationError({'latitude': 'Latitude must be between -90 and 90.'})
        if longitude is not None and not (Decimal('-180') <= longitude <= Decimal('180')):
            raise serializers.ValidationError({'longitude': 'Longitude must be between -180 and 180.'})
        publication_status = attrs.get(
            'publication_status',
            getattr(instance, 'publication_status', WorkerProfile.PublicationStatus.DRAFT),
        )
        if publication_status == WorkerProfile.PublicationStatus.PUBLISHED:
            request = self.context.get('request')
            user = getattr(request, 'user', None)
            if not service_provider_can_publish(user):
                raise serializers.ValidationError({
                    'publication_status': (
                        'Publish a profile only after service-provider verification is approved.'
                    ),
                })
        return attrs

    def create(self, validated_data):
        skill_names = validated_data.pop('skills')
        categories = validated_data.pop('service_categories', [])
        validated_data.pop('taluk', None)
        profile = WorkerProfile(**validated_data)
        save_clean(profile)
        profile.skills.set(resolve_skills(skill_names))
        profile.service_categories.set(categories)
        save_place(profile, profile.district, getattr(self, '_taluk', ''), profile.locality)
        return profile

    def update(self, instance, validated_data):
        skill_names = validated_data.pop('skills', None)
        categories = validated_data.pop('service_categories', None)
        validated_data.pop('taluk', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        save_clean(instance)
        if skill_names is not None:
            instance.skills.set(resolve_skills(skill_names))
        if categories is not None:
            instance.service_categories.set(categories)
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


class WorkerProfilePhotoSerializer(serializers.Serializer):
    """Multipart photo upload. The JSON profile routes do not accept a file."""

    photo = serializers.ImageField(allow_empty_file=False)

    def validate_photo(self, uploaded):
        validate_worker_photo(uploaded)
        return uploaded


class ServiceRequestSerializer(serializers.ModelSerializer):
    provider_name = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = [
            'id',
            'profile',
            'provider_name',
            'description',
            'contact_phone',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'provider_name', 'contact_phone', 'created_at', 'updated_at']

    def get_provider_name(self, obj):
        return obj.profile.display_name

    def validate_description(self, value):
        text = ' '.join(str(value).split())
        if not text:
            raise serializers.ValidationError('Describe the work.')
        if len(text) > 1000:
            raise serializers.ValidationError('Keep the description to 1000 characters or fewer.')
        return text

    def validate(self, attrs):
        request = self.context['request']
        if self.instance is None:
            profile = attrs.get('profile')
            if profile is None or profile.publication_status != WorkerProfile.PublicationStatus.PUBLISHED:
                raise serializers.ValidationError({'profile': 'Choose a published provider.'})
            phone = request.user.phone_number
            if not phone_is_verified(request.user, phone, OtpPurpose.SERVICE_REQUEST):
                raise serializers.ValidationError('Verify your mobile number before sending a request.')
            attrs['contact_phone'] = phone
            if attrs.get('status', ServiceRequest.Status.REQUESTED) != ServiceRequest.Status.REQUESTED:
                raise serializers.ValidationError({'status': 'A new request starts as requested.'})
        return attrs

    def create(self, validated_data):
        validated_data['status'] = ServiceRequest.Status.REQUESTED
        validated_data['customer'] = self.context['request'].user
        return ServiceRequest.objects.create(**validated_data)


class ServiceCategorySerializer(serializers.ModelSerializer):
    """Public category fields. Inactive categories are filtered out before this runs."""

    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'slug', 'description']


class GuestDailyServiceRequestSerializer(serializers.Serializer):
    """Create a guest request. The response is built by the view so private fields stay out."""

    guest_name = serializers.CharField(max_length=120)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(required=False, allow_blank=True, max_length=15)
    category = serializers.PrimaryKeyRelatedField(queryset=ServiceCategory.objects.all())
    description = serializers.CharField()
    latitude = CoordinateField()
    longitude = CoordinateField()
    radius_km = serializers.IntegerField(required=False, min_value=8, max_value=50, default=15)

    def validate_guest_name(self, value):
        name = ' '.join(str(value).split())
        if not name:
            raise serializers.ValidationError('Enter the customer name.')
        return name

    def validate_contact_email(self, value):
        return str(value or '').strip().lower()

    def validate_contact_phone(self, value):
        return str(value or '').strip()

    def validate_category(self, category):
        if not category.is_active:
            raise serializers.ValidationError('Choose an active service category.')
        return category

    def validate_description(self, value):
        text = ' '.join(str(value).split())
        if not text:
            raise serializers.ValidationError('Describe the work.')
        if len(text) > 1000:
            raise serializers.ValidationError('Keep the description to 1000 characters or fewer.')
        return text

    def validate(self, attrs):
        latitude = attrs['latitude'].quantize(Decimal('0.000001'))
        longitude = attrs['longitude'].quantize(Decimal('0.000001'))
        if not (Decimal('-90') <= latitude <= Decimal('90')):
            raise serializers.ValidationError({'latitude': 'Latitude must be between -90 and 90.'})
        if not (Decimal('-180') <= longitude <= Decimal('180')):
            raise serializers.ValidationError({'longitude': 'Longitude must be between -180 and 180.'})
        attrs['latitude'] = latitude
        attrs['longitude'] = longitude
        email = attrs.get('contact_email') or ''
        phone = normalize_phone(attrs.get('contact_phone') or '')
        if email and phone:
            raise serializers.ValidationError({
                'detail': 'Choose a mobile number or an email address, not both.',
            })
        if email:
            if not guest_email_is_verified(email, OtpPurpose.SERVICE_REQUEST):
                raise serializers.ValidationError({
                    'contact_email': 'Verify this email address before creating a request.',
                })
            attrs['contact_phone'] = ''
        elif phone:
            if not PHONE_PATTERN.match(phone):
                raise serializers.ValidationError({
                    'contact_phone': 'Enter a 10-digit Indian mobile number starting with 6, 7, 8, or 9.',
                })
            if not guest_phone_is_verified(phone, OtpPurpose.SERVICE_REQUEST):
                raise serializers.ValidationError({
                    'contact_phone': 'Verify this mobile number before creating a request.',
                })
            attrs['contact_phone'] = phone
            attrs['contact_email'] = ''
        else:
            raise serializers.ValidationError({
                'detail': 'Enter a verified mobile number or email address.',
            })
        return attrs

    def create(self, validated_data):
        raw_key = secrets.token_urlsafe(32)
        phone = validated_data.get('contact_phone') or ''
        email = validated_data.get('contact_email') or ''
        with transaction.atomic():
            if email:
                locked = GuestEmailVerification.objects.select_for_update().filter(
                    email=email,
                    purpose=OtpPurpose.SERVICE_REQUEST,
                    expires_at__gt=timezone.now(),
                )
                if not locked.exists():
                    raise serializers.ValidationError({
                        'contact_email': 'Verify this email address before creating a request.',
                    })
            if phone and guest_phone_table_ready():
                locked_phone = GuestPhoneVerification.objects.select_for_update().filter(
                    phone_number=phone,
                    purpose=OtpPurpose.SERVICE_REQUEST,
                    expires_at__gt=timezone.now(),
                )
                if not locked_phone.exists():
                    raise serializers.ValidationError({
                        'contact_phone': 'Verify this mobile number before creating a request.',
                    })
            elif phone and not guest_phone_is_verified(phone, OtpPurpose.SERVICE_REQUEST):
                raise serializers.ValidationError({
                    'contact_phone': 'Verify this mobile number before creating a request.',
                })
            record = DailyServiceRequest(
                category=validated_data['category'],
                guest_name=validated_data['guest_name'],
                contact_email=email,
                contact_phone=phone,
                description=validated_data['description'],
                latitude=validated_data['latitude'],
                longitude=validated_data['longitude'],
                radius_km=validated_data['radius_km'],
                status=DailyServiceRequest.Status.DRAFT,
            )
            if phone:
                record._guest_phone_verified = True
            record.set_access_key(raw_key)
            try:
                record.full_clean()
            except DjangoValidationError as exc:
                if getattr(exc, 'message_dict', None):
                    raise serializers.ValidationError(exc.message_dict) from exc
                raise serializers.ValidationError(exc.messages) from exc
            record.save()
            if email:
                consume_guest_email_verification(email, OtpPurpose.SERVICE_REQUEST)
            if phone:
                consume_guest_phone_verification(phone, OtpPurpose.SERVICE_REQUEST)
        self.access_key = raw_key
        return record

    def update(self, instance, validated_data):
        raise NotImplementedError


class CustomerDailyServiceRequestSerializer(serializers.Serializer):
    """A signed-in customer starts one category request. It is not an assignment."""

    category = serializers.PrimaryKeyRelatedField(queryset=ServiceCategory.objects.all())
    description = serializers.CharField()
    latitude = CoordinateField()
    longitude = CoordinateField()
    radius_km = serializers.IntegerField(required=False, min_value=8, max_value=50, default=15)

    def validate_category(self, category):
        if not category.is_active:
            raise serializers.ValidationError('Choose an active service category.')
        return category

    def validate_description(self, value):
        text = ' '.join(str(value).split())
        if not text:
            raise serializers.ValidationError('Describe the work.')
        if len(text) > 1000:
            raise serializers.ValidationError('Keep the description to 1000 characters or fewer.')
        return text

    def validate(self, attrs):
        latitude = attrs['latitude'].quantize(Decimal('0.000001'))
        longitude = attrs['longitude'].quantize(Decimal('0.000001'))
        if not (Decimal('-90') <= latitude <= Decimal('90')):
            raise serializers.ValidationError({'latitude': 'Latitude must be between -90 and 90.'})
        if not (Decimal('-180') <= longitude <= Decimal('180')):
            raise serializers.ValidationError({'longitude': 'Longitude must be between -180 and 180.'})
        attrs['latitude'] = latitude
        attrs['longitude'] = longitude
        return attrs

    def create(self, validated_data):
        record = DailyServiceRequest(
            category=validated_data['category'],
            customer=self.context['request'].user,
            description=validated_data['description'],
            latitude=validated_data['latitude'],
            longitude=validated_data['longitude'],
            radius_km=validated_data['radius_km'],
            status=DailyServiceRequest.Status.DRAFT,
        )
        try:
            record.full_clean()
        except DjangoValidationError as exc:
            if getattr(exc, 'message_dict', None):
                raise serializers.ValidationError(exc.message_dict) from exc
            raise serializers.ValidationError(exc.messages) from exc
        record.save()
        return record

    def update(self, instance, validated_data):
        raise NotImplementedError
