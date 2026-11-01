"""
SMSMobileAPI send adapter.

OTP values are created by KaamDo. This module only submits an already-built
message. A provider acceptance is not phone verification.

Network calls happen only when the caller supplies an API key. Tests must mock
them. The key and message body are not logged.
"""

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

SEND_URL = 'https://api.smsmobileapi.com/sendsms/'
DEFAULT_TIMEOUT = 10
REFUSED = 'The SMS provider refused the request. No code was sent.'
UNREACHABLE = 'The SMS provider could not be reached. No code was sent.'
TIMEOUT = 'The SMS provider timed out. No code was sent.'
UNUSABLE = 'The SMS provider returned an unusable response. No code was sent.'
NOT_CONFIGURED = 'SMS delivery is not configured. No code was sent.'


class SmsDeliveryError(Exception):
    """User-facing SMS failure. The message must not include secrets or OTP digits."""

    def __init__(self, user_message):
        super().__init__(user_message)
        self.user_message = user_message


def india_msisdn(phone):
    digits = ''.join(character for character in str(phone or '') if character.isdigit())
    if digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]
    if len(digits) != 10:
        raise SmsDeliveryError('Enter a 10-digit valid number.')
    return f'+91{digits}'


def _urlopen(request, timeout, context):
    return urllib.request.urlopen(request, timeout=timeout, context=context)


def post_sendsms(fields, timeout):
    """POST form fields to the documented HTTPS sendsms endpoint. Do not put the key in the URL."""
    body = urllib.parse.urlencode(fields).encode('utf-8')
    request = urllib.request.Request(SEND_URL, data=body, method='POST')
    request.add_header('Content-Type', 'application/x-www-form-urlencoded')
    request.add_header('Accept', 'application/json')
    try:
        with _urlopen(
            request,
            timeout=float(timeout),
            context=ssl.create_default_context(),
        ) as response:
            return getattr(response, 'status', 200), response.read()
    except TimeoutError as exc:
        raise SmsDeliveryError(TIMEOUT) from exc
    except urllib.error.HTTPError as exc:
        status = exc.code
        try:
            exc.read()
        except Exception:
            pass
        if status in (401, 403):
            raise SmsDeliveryError(REFUSED) from exc
        raise SmsDeliveryError(UNUSABLE) from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, 'reason', None)
        if isinstance(reason, TimeoutError) or 'timed out' in str(reason).lower():
            raise SmsDeliveryError(TIMEOUT) from exc
        raise SmsDeliveryError(UNREACHABLE) from exc


def parse_sendsms_body(raw):
    try:
        payload = json.loads(raw.decode('utf-8') if isinstance(raw, (bytes, bytearray)) else raw)
    except (TypeError, ValueError, UnicodeDecodeError) as exc:
        raise SmsDeliveryError(UNUSABLE) from exc
    if not isinstance(payload, dict):
        raise SmsDeliveryError(UNUSABLE)
    result = payload.get('result')
    if not isinstance(result, dict):
        raise SmsDeliveryError(UNUSABLE)
    error = result.get('error')
    if error not in (0, '0'):
        raise SmsDeliveryError(UNUSABLE)
    return {
        'accepted': True,
        'provider_id': str(result['id']) if result.get('id') not in (None, '') else '',
    }


def send_message(phone, message, *, api_key, timeout=DEFAULT_TIMEOUT, post=None):
    """Submit one SMS. Does not mark a phone verified."""
    key = str(api_key or '').strip()
    if not key:
        raise SmsDeliveryError(NOT_CONFIGURED)
    text = str(message or '')
    if not text.strip():
        raise SmsDeliveryError(NOT_CONFIGURED)
    fields = {
        'apikey': key,
        'recipients': india_msisdn(phone),
        'message': text,
        'sendsms': '1',
    }
    poster = post or post_sendsms
    status, raw = poster(fields, timeout)
    if status != 200:
        raise SmsDeliveryError(UNUSABLE)
    return parse_sendsms_body(raw)
