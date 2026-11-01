"""
IP limits for OTP send and verify.

These sit in front of the phone/email limits. They use Django's cache and the
same DRF Throttled 429 already used for per-phone resend caps.

X-Forwarded-For is ignored unless REMOTE_ADDR is in OTP_TRUSTED_PROXIES.
"""

import ipaddress

from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import Throttled

OTP_IP_WAIT = 'Wait before requesting another code.'


def _parse_ip(value):
    try:
        return str(ipaddress.ip_address(str(value or '').strip()))
    except ValueError:
        return ''


def trusted_proxy_ips():
    configured = getattr(settings, 'OTP_TRUSTED_PROXIES', ()) or ()
    return {parsed for parsed in (_parse_ip(item) for item in configured) if parsed}


def client_ip(meta):
    """Return the connecting IP. Spoofed forwarding headers are ignored by default."""
    remote = _parse_ip((meta or {}).get('REMOTE_ADDR', ''))
    if not remote:
        return '0.0.0.0'
    trusted = trusted_proxy_ips()
    if remote not in trusted:
        return remote
    forwarded = (meta or {}).get('HTTP_X_FORWARDED_FOR') or ''
    parts = [_parse_ip(part) for part in forwarded.split(',')]
    parts = [part for part in parts if part]
    for part in reversed(parts):
        if part not in trusted:
            return part
    return remote


def _limit_for(action):
    if action == 'verify':
        return int(getattr(settings, 'OTP_IP_VERIFY_LIMIT', 25) or 25)
    return int(getattr(settings, 'OTP_IP_SEND_LIMIT', 8) or 8)


def _window_seconds():
    minutes = int(getattr(settings, 'OTP_IP_WINDOW_MINUTES', 15) or 15)
    return max(minutes, 1) * 60


def enforce_otp_ip_limit(request, action):
    """Count this IP for send or verify. Changing phone, purpose, or account does not reset it."""
    limit = max(_limit_for(action), 1)
    timeout = _window_seconds()
    ip_address = client_ip(getattr(request, 'META', {}))
    key = f'kaamdo-otp-ip:{action}:{ip_address}'
    if cache.add(key, 1, timeout):
        count = 1
    else:
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout)
            count = 1
    if count > limit:
        raise Throttled(detail=OTP_IP_WAIT)
