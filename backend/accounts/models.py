"""
Accounts models.
One person has one User. Capabilities are the activities that account may perform.
The active mode is only the screen they currently have open.
"""

import re

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

PHONE_PATTERN = re.compile(r'^[6-9]\d{9}$')


def normalize_phone(value):
    """Reduce a phone value to digits, dropping a leading India country code."""
    if value is None:
        return ''
    digits = re.sub(r'\D', '', str(value))
    if digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith('0') and len(digits) == 11:
        digits = digits[1:]
    return digits


def validate_indian_mobile(value):
    if value in (None, ''):
        return
    if not PHONE_PATTERN.match(value):
        raise ValidationError('Enter a 10-digit Indian mobile number starting with 6, 7, 8, or 9.')


class Capability(models.TextChoices):
    """Activities one account can be allowed to perform. This is not an admin flag."""

    CUSTOMER = 'customer', 'Customer'
    SERVICE_PROVIDER = 'service_provider', 'Service Provider'
    JOB_SEEKER = 'job_seeker', 'Job Seeker'
    EMPLOYER = 'employer', 'Employer'
    AGRICULTURAL_WORKER = 'agricultural_worker', 'Agricultural Worker'
    AGRICULTURAL_EMPLOYER = 'agricultural_employer', 'Agricultural Job Poster'
    EQUIPMENT_OWNER = 'equipment_owner', 'Equipment Owner'
    EQUIPMENT_RENTER = 'equipment_renter', 'Equipment Renter'


# Older clients send the single role that existed before capabilities.
LEGACY_ROLE_TO_CAPABILITY = {
    'customer': Capability.CUSTOMER,
    'worker': Capability.SERVICE_PROVIDER,
}


class User(AbstractUser):
    """Identity and login. Permissions come from capability rows, not from this screen choice."""

    phone_number = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        validators=[validate_indian_mobile],
        help_text='10-digit Indian mobile number. Used as the public login identifier.',
    )
    active_mode = models.CharField(
        max_length=40,
        choices=Capability.choices,
        default=Capability.CUSTOMER,
        help_text='The interface this person currently has open. It does not grant a capability.',
    )

    def save(self, *args, **kwargs):
        if self.phone_number == '':
            self.phone_number = None
        super().save(*args, **kwargs)

    def capability_codes(self):
        return list(
            self.capability_grants.order_by('enabled_at', 'code').values_list('code', flat=True)
        )

    def has_capability(self, code):
        return self.capability_grants.filter(code=code).exists()


class AccountCapability(models.Model):
    """One enabled activity for one account. A person can have several."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='capability_grants',
    )
    code = models.CharField(max_length=40, choices=Capability.choices)
    enabled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['enabled_at', 'code']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'code'],
                name='accounts_capability_user_code_uniq',
            ),
        ]

    def __str__(self):
        return f'{self.user_id}:{self.code}'


class OtpPurpose(models.TextChoices):
    """Why a phone number is being checked. Login alone does not verify a number."""

    ACCOUNT = 'account', 'Account phone'
    EQUIPMENT_INQUIRY = 'equipment_inquiry', 'Equipment inquiry'
    SERVICE_REQUEST = 'service_request', 'Service request'
    JOB_APPLICATION = 'job_application', 'Job application'
    AGRICULTURAL_APPLICATION = 'agricultural_application', 'Agricultural application'
    EMPLOYER_REVIEW = 'employer_review', 'Employer review'


class PhoneOtpChallenge(models.Model):
    """A short-lived code. Only the hash is stored."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='otp_challenges',
        null=True,
        blank=True,
    )
    phone_number = models.CharField(max_length=10)
    purpose = models.CharField(max_length=40, choices=OtpPurpose.choices)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'purpose', 'created_at'], name='accounts_otp_phone_purpose_idx'),
        ]


class PhoneVerification(models.Model):
    """Proof that this account recently controlled a specific phone number."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='phone_verifications')
    phone_number = models.CharField(max_length=10)
    purpose = models.CharField(max_length=40, choices=OtpPurpose.choices)
    verified_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-verified_at']
        indexes = [
            models.Index(fields=['user', 'phone_number', 'purpose'], name='accounts_phone_verified_idx'),
        ]


class GuestEmailOtpChallenge(models.Model):
    """A short-lived email code for a guest. Only the hash is stored."""

    email = models.EmailField()
    purpose = models.CharField(max_length=40, choices=OtpPurpose.choices)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'purpose', 'created_at'], name='accounts_guest_otp_email_idx'),
        ]

    def __str__(self):
        return f'Guest email check {self.pk or "new"}'


class GuestEmailVerification(models.Model):
    """Proof that a guest recently controlled an email address. This is not a user account."""

    email = models.EmailField()
    purpose = models.CharField(max_length=40, choices=OtpPurpose.choices)
    verified_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-verified_at']
        indexes = [
            models.Index(fields=['email', 'purpose'], name='accounts_guest_verified_idx'),
        ]

    def __str__(self):
        return f'Guest email verification {self.pk or "new"}'


class GuestPhoneVerification(models.Model):
    """
    Guest mobile number that passed a one-time code for a specific action.
    PhoneOtpChallenge may already exist without a user; this record is the
    used-code receipt. When the table is missing, verify falls back to cache.
    """

    phone_number = models.CharField(max_length=10)
    purpose = models.CharField(max_length=40, choices=OtpPurpose.choices)
    verified_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-verified_at']
        indexes = [
            models.Index(fields=['phone_number', 'purpose'], name='accounts_guest_phone_ver_idx'),
        ]

    def __str__(self):
        return f'Guest phone verification {self.pk or "new"}'


def guest_email_is_verified(email, purpose):
    """True when a recent guest check matches this email and purpose."""
    if not email:
        return False
    return GuestEmailVerification.objects.filter(
        email=email.strip().lower(),
        purpose=purpose,
        expires_at__gt=timezone.now(),
    ).exists()


def consume_guest_email_verification(email, purpose):
    """Use a guest email check once. Later creates need a new code."""
    email = str(email or '').strip().lower()
    if not email:
        return 0
    deleted, _ = GuestEmailVerification.objects.filter(
        email=email,
        purpose=purpose,
        expires_at__gt=timezone.now(),
    ).delete()
    return deleted


_GUEST_PHONE_TABLE_READY = None
GUEST_PHONE_CACHE_PREFIX = 'kaamdo:guest-phone-ok:'


def reset_guest_phone_table_cache():
    global _GUEST_PHONE_TABLE_READY
    _GUEST_PHONE_TABLE_READY = None


def guest_phone_table_ready():
    """True only when GuestPhoneVerification exists on this database."""
    global _GUEST_PHONE_TABLE_READY
    if _GUEST_PHONE_TABLE_READY is not None:
        return _GUEST_PHONE_TABLE_READY
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            tables = connection.introspection.table_names(cursor)
        _GUEST_PHONE_TABLE_READY = 'accounts_guestphoneverification' in tables
    except Exception:
        _GUEST_PHONE_TABLE_READY = False
    return _GUEST_PHONE_TABLE_READY


def guest_phone_is_verified(phone, purpose):
    """True when a recent guest mobile check matches this number and purpose."""
    phone = normalize_phone(phone)
    if not phone:
        return False
    now = timezone.now()
    if guest_phone_table_ready():
        return GuestPhoneVerification.objects.filter(
            phone_number=phone,
            purpose=purpose,
            expires_at__gt=now,
        ).exists()
    from django.core.cache import cache

    cached = cache.get(f'{GUEST_PHONE_CACHE_PREFIX}{purpose}:{phone}')
    if not cached:
        return False
    expires_at = cached.get('expires_at')
    return bool(expires_at and expires_at > now)


def consume_guest_phone_verification(phone, purpose):
    """Use a guest mobile check once. Later creates need a new code."""
    phone = normalize_phone(phone)
    if not phone:
        return 0
    now = timezone.now()
    if guest_phone_table_ready():
        deleted, _ = GuestPhoneVerification.objects.filter(
            phone_number=phone,
            purpose=purpose,
            expires_at__gt=now,
        ).delete()
        return deleted
    from django.core.cache import cache

    key = f'{GUEST_PHONE_CACHE_PREFIX}{purpose}:{phone}'
    if cache.get(key):
        cache.delete(key)
        return 1
    return 0


def phone_is_verified(user, phone, purpose):
    """True when a recent check matches this account, number, and purpose."""
    if user is None or not getattr(user, 'is_authenticated', False) or not phone:
        return False
    return PhoneVerification.objects.filter(
        user=user,
        phone_number=phone,
        purpose=purpose,
        expires_at__gt=timezone.now(),
    ).exists()
