"""
Accounts serializers.
Registration grants capabilities. It cannot grant staff or superuser access.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .models import (
    PHONE_PATTERN,
    AccountCapability,
    Capability,
    LEGACY_ROLE_TO_CAPABILITY,
    User,
    normalize_phone,
)


class UserSerializer(serializers.ModelSerializer):
    """Fields that are safe to return to the signed-in person."""

    full_name = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()
    service_provider = serializers.SerializerMethodField()
    test_payment = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'phone_number',
            'first_name',
            'last_name',
            'full_name',
            'email',
            'capabilities',
            'active_mode',
            'service_provider',
            'test_payment',
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_capabilities(self, obj):
        return obj.capability_codes()

    def get_service_provider(self, obj):
        if not obj.has_capability(Capability.SERVICE_PROVIDER):
            return None
        from workers.models import ServiceProviderVerification, WorkerProfile

        categories = []
        profile_status = None
        try:
            profile = (
                WorkerProfile.objects.filter(user=obj)
                .prefetch_related('service_categories')
                .first()
            )
            if profile is not None:
                profile_status = profile.publication_status
                categories = [
                    {'id': row.pk, 'name': row.name, 'slug': row.slug}
                    for row in profile.service_categories.all()
                ]
        except Exception:
            profile_status = None
        try:
            verification_status = obj.service_provider_verification.status
        except ServiceProviderVerification.DoesNotExist:
            verification_status = ServiceProviderVerification.Status.NOT_SUBMITTED
        return {
            'profile_status': profile_status,
            'verification_status': verification_status,
            'section': 'Daily services',
            'categories': categories,
        }

    def get_test_payment(self, obj):
        """Staff-only flag. Ordinary accounts get null. A client payload cannot turn this on."""
        if not getattr(obj, 'is_staff', False):
            return None
        from workers.services import test_payment_public_payload, test_visit_payment_enabled
        if not test_visit_payment_enabled():
            return None
        return test_payment_public_payload()


class RegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=16)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    full_name = serializers.CharField(max_length=301)
    capabilities = serializers.ListField(
        child=serializers.ChoiceField(choices=Capability.choices),
        required=False,
        allow_empty=False,
    )
    # Kept so the previous customer/worker registration payload still works.
    role = serializers.CharField(required=False, allow_blank=False)

    def validate_phone_number(self, value):
        phone = normalize_phone(value)
        if not PHONE_PATTERN.match(phone):
            raise serializers.ValidationError('Enter a 10-digit valid number.')
        if User.objects.filter(phone_number=phone).exists():
            raise serializers.ValidationError('A user with this phone number already exists.')
        if User.objects.filter(username=phone).exists():
            raise serializers.ValidationError('An account with this phone number already exists.')
        return phone

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def validate_full_name(self, value):
        name = ' '.join(value.split())
        if not name:
            raise serializers.ValidationError('Full name is required.')
        first_name, _, last_name = name.partition(' ')
        if len(first_name) > 150 or len(last_name) > 150:
            raise serializers.ValidationError('Full name is too long.')
        return name

    def validate(self, attrs):
        selected = attrs.get('capabilities')
        role = attrs.get('role')
        if selected:
            codes = list(dict.fromkeys(selected))
        elif role:
            mapped = LEGACY_ROLE_TO_CAPABILITY.get(role)
            if mapped is None:
                raise serializers.ValidationError({
                    'role': 'Select a valid starting capability. Worker and customer are accepted.',
                })
            codes = [mapped]
        else:
            raise serializers.ValidationError({
                'capabilities': 'Choose at least one capability.',
            })
        if Capability.CUSTOMER not in codes:
            codes.append(Capability.CUSTOMER)
        attrs['capabilities'] = codes
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        first_name, _, last_name = validated_data['full_name'].partition(' ')
        phone = validated_data['phone_number']
        codes = validated_data['capabilities']
        # Public registration cannot grant staff or superuser access.
        user = User.objects.create_user(
            username=phone,
            password=validated_data['password'],
            phone_number=phone,
            first_name=first_name,
            last_name=last_name,
            active_mode=codes[0],
            is_staff=False,
        )
        AccountCapability.objects.bulk_create([
            AccountCapability(user=user, code=code) for code in codes
        ])
        return user


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=16)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_phone_number(self, value):
        phone = normalize_phone(value)
        if not PHONE_PATTERN.match(phone):
            raise serializers.ValidationError('Enter a 10-digit valid number.')
        return phone


class EnableCapabilitySerializer(serializers.Serializer):
    capability = serializers.ChoiceField(choices=Capability.choices)

    def validate_capability(self, value):
        # Customer is marketplace access for every account, not a professional role to add.
        if value == Capability.CUSTOMER:
            raise serializers.ValidationError(
                'Every signed-in account can request services. Choose a professional role instead.'
            )
        return value


class ActiveModeSerializer(serializers.Serializer):
    active_mode = serializers.ChoiceField(choices=Capability.choices)

    def validate_active_mode(self, value):
        user = self.context['request'].user
        if not user.has_capability(value):
            raise serializers.ValidationError(
                'Switch only to a capability already enabled on this account.'
            )
        return value
