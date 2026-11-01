"""
Phone and guest-email OTP checks.
Codes are hashed. The plain code is shown only for an explicit local development setup.
SMSMobileAPI is used only when KAAMDO_OTP_DELIVERY=smsmobileapi and a server key is set.
A provider acceptance is not phone verification.
"""

import secrets
import sys
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

from .models import (
    GUEST_PHONE_CACHE_PREFIX,
    GuestEmailOtpChallenge,
    GuestEmailVerification,
    GuestPhoneVerification,
    OtpPurpose,
    PhoneOtpChallenge,
    PhoneVerification,
    guest_phone_table_ready,
    normalize_phone,
    PHONE_PATTERN,
)
from .smsmobileapi import SmsDeliveryError, send_message as send_smsmobileapi_message

OTP_MINUTES = 10
VERIFIED_HOURS = 24
MAX_SENDS = 3
SEND_WINDOW_MINUTES = 15
MAX_ATTEMPTS = 5
SMS_ACCEPTED_DETAIL = (
    'The SMS provider accepted the request. Enter the code when it arrives.'
)


def normalize_otp_phone(value):
    phone = normalize_phone(value)
    if not PHONE_PATTERN.match(phone):
        raise ValidationError({'phone_number': 'Enter a 10-digit valid number.'})
    return phone


def account_otp_phone(user):
    """Registered OTP always uses the mobile number stored on the account."""
    return normalize_otp_phone(getattr(user, 'phone_number', ''))


def require_account_phone(user, phone):
    if phone != account_otp_phone(user):
        raise ValidationError({'phone_number': 'Use the mobile number on this account.'})


def normalize_guest_email(value):
    email = str(value or '').strip().lower()
    try:
        validate_email(email)
    except DjangoValidationError as exc:
        raise ValidationError({'email': 'Enter a valid email address.'}) from exc
    return email


def guest_otp_contact(data):
    """Return ('phone', number) or ('email', address). Guests choose one, not both."""
    payload = data if hasattr(data, 'get') else {}
    phone_raw = str(payload.get('phone_number') or '').strip()
    email_raw = str(payload.get('email') or '').strip()
    if phone_raw and email_raw:
        raise ValidationError({
            'detail': 'Choose a mobile number or an email address, not both.',
        })
    if phone_raw:
        return 'phone', normalize_otp_phone(phone_raw)
    if email_raw:
        return 'email', normalize_guest_email(email_raw)
    raise ValidationError({'detail': 'Enter a mobile number or an email address.'})


def development_otp_enabled():
    """True only for a local debug process that explicitly asked for development codes."""
    return settings.DEBUG is True and getattr(settings, 'OTP_DELIVERY', 'unconfigured') == 'development'


def sms_otp_enabled():
    """True only when SMSMobileAPI delivery was explicitly selected. Default remains off."""
    return getattr(settings, 'OTP_DELIVERY', 'unconfigured') == 'smsmobileapi'


def sms_otp_configured():
    """True only when SMS delivery is selected and a server key is present. The key is not returned."""
    if not sms_otp_enabled():
        return False
    return bool(str(getattr(settings, 'SMSMOBILEAPI_API_KEY', '') or '').strip())


def guest_otp_options():
    """Public guest verification flags. No secrets, no codes, and no provider names."""
    development = development_otp_enabled()
    sms = sms_otp_configured()
    return {
        'email': {
            'available': development,
            'mode': 'development' if development else 'unavailable',
        },
        'phone': {
            'available': sms,
            'mode': 'sms' if sms else 'unavailable',
        },
    }


def _new_code():
    return f'{secrets.randbelow(1000000):06d}'


def _development_payload(code, label, detail):
    if not development_otp_enabled():
        raise ValidationError({'detail': 'Verification delivery is not configured. No code was sent.'})
    print(f'KaamDo local development OTP ({label}): {code}', file=sys.stderr)
    return {
        'detail': detail,
        'delivery': 'development',
        'expires_in': OTP_MINUTES * 60,
        'dev_code': code,
    }


def send_otp(user, phone, purpose):
    if purpose not in OtpPurpose.values:
        raise ValidationError({'purpose': 'Choose a valid verification purpose.'})
    require_account_phone(user, phone)
    window_start = timezone.now() - timedelta(minutes=SEND_WINDOW_MINUTES)
    recent = PhoneOtpChallenge.objects.filter(
        phone_number=phone,
        purpose=purpose,
        created_at__gte=window_start,
    ).count()
    if recent >= MAX_SENDS:
        raise Throttled(detail='Wait before requesting another code.')
    if development_otp_enabled():
        code = _new_code()
        PhoneOtpChallenge.objects.filter(
            user=user,
            phone_number=phone,
            purpose=purpose,
            consumed=False,
        ).update(consumed=True)
        PhoneOtpChallenge.objects.create(
            user=user,
            phone_number=phone,
            purpose=purpose,
            code_hash=make_password(code),
            expires_at=timezone.now() + timedelta(minutes=OTP_MINUTES),
        )
        return _development_payload(
            code,
            f'phone {purpose}',
            'Local development code only. This was not sent by SMS.',
        )
    if not sms_otp_enabled():
        raise ValidationError({
            'detail': 'SMS delivery is not configured. No code was sent.',
        })
    api_key = getattr(settings, 'SMSMOBILEAPI_API_KEY', '')
    if not str(api_key or '').strip():
        raise ValidationError({
            'detail': 'SMS delivery is not configured. No code was sent.',
        })
    code = _new_code()
    PhoneOtpChallenge.objects.filter(
        user=user,
        phone_number=phone,
        purpose=purpose,
        consumed=False,
    ).update(consumed=True)
    challenge = PhoneOtpChallenge.objects.create(
        user=user,
        phone_number=phone,
        purpose=purpose,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(minutes=OTP_MINUTES),
    )
    try:
        send_smsmobileapi_message(
            phone,
            (
                f'KaamDo code: {code}. It expires in {OTP_MINUTES} minutes. '
                'Do not share it.'
            ),
            api_key=api_key,
            timeout=getattr(settings, 'SMSMOBILEAPI_TIMEOUT_SECONDS', 10),
        )
    except SmsDeliveryError as exc:
        challenge.consumed = True
        challenge.save(update_fields=['consumed'])
        raise ValidationError({'detail': exc.user_message}) from exc
    return {
        'detail': SMS_ACCEPTED_DETAIL,
        'delivery': 'sms',
        'expires_in': OTP_MINUTES * 60,
    }


def _consume_open_phone_challenges(phone, purpose, user=None):
    qs = PhoneOtpChallenge.objects.filter(
        phone_number=phone,
        purpose=purpose,
        consumed=False,
    )
    if user is None:
        qs = qs.filter(user__isnull=True)
    else:
        qs = qs.filter(user=user)
    qs.update(consumed=True)


def _create_phone_challenge(phone, purpose, code, user=None):
    return PhoneOtpChallenge.objects.create(
        user=user,
        phone_number=phone,
        purpose=purpose,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(minutes=OTP_MINUTES),
    )


def send_guest_phone_otp(phone, purpose):
    """Create a guest mobile code. This does not create an account or a booking."""
    if purpose != OtpPurpose.SERVICE_REQUEST:
        raise ValidationError({'purpose': 'Guest mobile verification is only available for a service request.'})
    window_start = timezone.now() - timedelta(minutes=SEND_WINDOW_MINUTES)
    recent = PhoneOtpChallenge.objects.filter(
        phone_number=phone,
        purpose=purpose,
        created_at__gte=window_start,
        user__isnull=True,
    ).count()
    if recent >= MAX_SENDS:
        raise Throttled(detail='Wait before requesting another code.')
    if development_otp_enabled():
        code = _new_code()
        _consume_open_phone_challenges(phone, purpose)
        _create_phone_challenge(phone, purpose, code)
        return _development_payload(
            code,
            f'guest phone {purpose}',
            'Local development code only. This was not sent by SMS.',
        )
    if not sms_otp_enabled():
        raise ValidationError({
            'detail': 'SMS delivery is not configured. No code was sent.',
        })
    api_key = getattr(settings, 'SMSMOBILEAPI_API_KEY', '')
    if not str(api_key or '').strip():
        raise ValidationError({
            'detail': 'SMS delivery is not configured. No code was sent.',
        })
    code = _new_code()
    _consume_open_phone_challenges(phone, purpose)
    challenge = _create_phone_challenge(phone, purpose, code)
    try:
        send_smsmobileapi_message(
            phone,
            (
                f'KaamDo code: {code}. It expires in {OTP_MINUTES} minutes. '
                'Do not share it.'
            ),
            api_key=api_key,
            timeout=getattr(settings, 'SMSMOBILEAPI_TIMEOUT_SECONDS', 10),
        )
    except SmsDeliveryError as exc:
        challenge.consumed = True
        challenge.save(update_fields=['consumed'])
        raise ValidationError({'detail': exc.user_message}) from exc
    return {
        'detail': SMS_ACCEPTED_DETAIL,
        'delivery': 'sms',
        'expires_in': OTP_MINUTES * 60,
    }


def send_guest_email_otp(email, purpose):
    """Create a guest email code. This does not create an account or a booking."""
    if purpose != OtpPurpose.SERVICE_REQUEST:
        raise ValidationError({'purpose': 'Guest email verification is only available for a service request.'})
    window_start = timezone.now() - timedelta(minutes=SEND_WINDOW_MINUTES)
    recent = GuestEmailOtpChallenge.objects.filter(
        email=email,
        purpose=purpose,
        created_at__gte=window_start,
    ).count()
    if recent >= MAX_SENDS:
        raise Throttled(detail='Wait before requesting another code.')
    if not development_otp_enabled():
        raise ValidationError({
            'detail': 'Email delivery is not configured. No code was sent.',
        })
    code = _new_code()
    GuestEmailOtpChallenge.objects.filter(
        email=email,
        purpose=purpose,
        consumed=False,
    ).update(consumed=True)
    GuestEmailOtpChallenge.objects.create(
        email=email,
        purpose=purpose,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(minutes=OTP_MINUTES),
    )
    return _development_payload(
        code,
        f'guest email {purpose}',
        'Local development code only. This was not sent by email.',
    )


def verify_otp(user, phone, purpose, code):
    if purpose not in OtpPurpose.values:
        raise ValidationError({'purpose': 'Choose a valid verification purpose.'})
    require_account_phone(user, phone)
    if not isinstance(code, str) or not code.isdigit() or len(code) != 6:
        raise ValidationError({'code': 'Enter the 6-digit code.'})
    challenge = (
        PhoneOtpChallenge.objects.filter(
            user=user,
            phone_number=phone,
            purpose=purpose,
            consumed=False,
        )
        .order_by('-created_at')
        .first()
    )
    if challenge is None or challenge.expires_at <= timezone.now():
        raise ValidationError({'code': 'That code is expired. Request a new one.'})
    if challenge.attempts >= MAX_ATTEMPTS:
        challenge.consumed = True
        challenge.save(update_fields=['consumed'])
        raise ValidationError({'code': 'Too many attempts. Request a new code.'})
    if not check_password(code, challenge.code_hash):
        challenge.attempts += 1
        if challenge.attempts >= MAX_ATTEMPTS:
            challenge.consumed = True
        challenge.save(update_fields=['attempts', 'consumed'])
        raise ValidationError({'code': 'That code is not correct.'})
    challenge.consumed = True
    challenge.save(update_fields=['consumed'])
    PhoneVerification.objects.create(
        user=user,
        phone_number=phone,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(hours=VERIFIED_HOURS),
    )
    return {'detail': 'Phone number verified.', 'expires_in': VERIFIED_HOURS * 3600}


def _store_guest_phone_verification(phone, purpose):
    expires_at = timezone.now() + timedelta(hours=VERIFIED_HOURS)
    if guest_phone_table_ready():
        GuestPhoneVerification.objects.create(
            phone_number=phone,
            purpose=purpose,
            expires_at=expires_at,
        )
        return
    from django.core.cache import cache

    cache.set(
        f'{GUEST_PHONE_CACHE_PREFIX}{purpose}:{phone}',
        {'expires_at': expires_at},
        timeout=VERIFIED_HOURS * 3600,
    )


def verify_guest_phone_otp(phone, purpose, code):
    """Mark a guest mobile number verified only after the hashed code matches."""
    if purpose != OtpPurpose.SERVICE_REQUEST:
        raise ValidationError({'purpose': 'Guest mobile verification is only available for a service request.'})
    if not isinstance(code, str) or not code.isdigit() or len(code) != 6:
        raise ValidationError({'code': 'Enter the 6-digit code.'})
    challenge = (
        PhoneOtpChallenge.objects.filter(
            user__isnull=True,
            phone_number=phone,
            purpose=purpose,
            consumed=False,
        )
        .order_by('-created_at')
        .first()
    )
    if challenge is None or challenge.expires_at <= timezone.now():
        raise ValidationError({'code': 'That code is expired. Request a new one.'})
    if challenge.attempts >= MAX_ATTEMPTS:
        challenge.consumed = True
        challenge.save(update_fields=['consumed'])
        raise ValidationError({'code': 'Too many attempts. Request a new code.'})
    if not check_password(code, challenge.code_hash):
        challenge.attempts += 1
        if challenge.attempts >= MAX_ATTEMPTS:
            challenge.consumed = True
        challenge.save(update_fields=['attempts', 'consumed'])
        raise ValidationError({'code': 'That code is not correct.'})
    challenge.consumed = True
    challenge.save(update_fields=['consumed'])
    _store_guest_phone_verification(phone, purpose)
    return {'detail': 'Mobile number verified.', 'expires_in': VERIFIED_HOURS * 3600}


def verify_guest_email_otp(email, purpose, code):
    """Mark a guest email verified only after the hashed code matches."""
    if purpose != OtpPurpose.SERVICE_REQUEST:
        raise ValidationError({'purpose': 'Guest email verification is only available for a service request.'})
    if not isinstance(code, str) or not code.isdigit() or len(code) != 6:
        raise ValidationError({'code': 'Enter the 6-digit code.'})
    challenge = (
        GuestEmailOtpChallenge.objects.filter(
            email=email,
            purpose=purpose,
            consumed=False,
        )
        .order_by('-created_at')
        .first()
    )
    if challenge is None or challenge.expires_at <= timezone.now():
        raise ValidationError({'code': 'That code is expired. Request a new one.'})
    if challenge.attempts >= MAX_ATTEMPTS:
        challenge.consumed = True
        challenge.save(update_fields=['consumed'])
        raise ValidationError({'code': 'Too many attempts. Request a new code.'})
    if not check_password(code, challenge.code_hash):
        challenge.attempts += 1
        if challenge.attempts >= MAX_ATTEMPTS:
            challenge.consumed = True
        challenge.save(update_fields=['attempts', 'consumed'])
        raise ValidationError({'code': 'That code is not correct.'})
    challenge.consumed = True
    challenge.save(update_fields=['consumed'])
    GuestEmailVerification.objects.create(
        email=email,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(hours=VERIFIED_HOURS),
    )
    return {'detail': 'Email address verified.', 'expires_in': VERIFIED_HOURS * 3600}
