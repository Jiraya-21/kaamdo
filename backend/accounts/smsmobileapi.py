"""
SMSMobileAPI send adapter.

OTP values are created by KaamDo. This module only submits an already-built
message. A provider acceptance is not phone verification.

Network calls happen only when the caller supplies an API key. Tests must mock
them. The key, Authorization material, OTP digits, and full phone numbers are
never logged.
"""

import json
import logging
import re
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

logger = logging.getLogger('kaamdo.smsmobileapi')

_PLAIN_SUCCESS = re.compile(
    r'^\s*(ok|okay|success|accepted|sent|true|1|0)\s*[.!?]?\s*$',
    re.IGNORECASE,
)
_SECRET_QUERY = re.compile(r'(apikey|api_key|key|token|password)=([^&\s]+)', re.IGNORECASE)
_PHONE_RE = re.compile(r'(\+?91[\s-]*)?[6-9]\d{9}')
_OTP_RE = re.compile(r'\b\d{4,8}\b')


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


def _decode_body(raw):
    if raw is None:
        return ''
    if isinstance(raw, (bytes, bytearray)):
        return raw.decode('utf-8', errors='replace')
    return str(raw)


def sanitize_response_text(text, *, api_key=''):
    """Redact secrets, OTP-like digits, and phone numbers for logs."""
    value = _decode_body(text)
    key = str(api_key or '').strip()
    if key:
        value = value.replace(key, '[REDACTED_KEY]')
    value = _SECRET_QUERY.sub(r'\1=[REDACTED]', value)
    value = _PHONE_RE.sub('[REDACTED_PHONE]', value)
    value = _OTP_RE.sub('[REDACTED_DIGITS]', value)
    value = re.sub(r'\s+', ' ', value).strip()
    return value[:500]


def _log_provider_exchange(*, status, content_type, body, api_key='', outcome='info', detail=''):
    logger.log(
        logging.WARNING if outcome == 'error' else logging.INFO,
        'smsmobileapi sendsms status=%s content_type=%s body=%s detail=%s key_configured=%s',
        status,
        content_type or '',
        sanitize_response_text(body, api_key=api_key),
        detail or '',
        'yes' if str(api_key or '').strip() else 'no',
    )


def post_sendsms(fields, timeout):
    """POST form fields to the documented HTTPS sendsms endpoint. Do not put the key in the URL.

    Returns (http_status, raw_body_bytes, content_type).
    """
    body = urllib.parse.urlencode(fields).encode('utf-8')
    request = urllib.request.Request(SEND_URL, data=body, method='POST')
    request.add_header('Content-Type', 'application/x-www-form-urlencoded')
    request.add_header('Accept', 'application/json, text/plain, */*')
    try:
        with _urlopen(
            request,
            timeout=float(timeout),
            context=ssl.create_default_context(),
        ) as response:
            raw = response.read()
            content_type = ''
            try:
                content_type = response.headers.get('Content-Type', '') if response.headers else ''
            except Exception:
                content_type = ''
            return getattr(response, 'status', 200), raw, content_type
    except TimeoutError as exc:
        raise SmsDeliveryError(TIMEOUT) from exc
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = b''
        content_type = ''
        try:
            raw = exc.read() or b''
        except Exception:
            raw = b''
        try:
            content_type = exc.headers.get('Content-Type', '') if exc.headers else ''
        except Exception:
            content_type = ''
        if status in (401, 403):
            raise SmsDeliveryError(REFUSED) from exc
        # Return the body so send_message can parse provider JSON/text when present.
        return status, raw, content_type
    except urllib.error.URLError as exc:
        reason = getattr(exc, 'reason', None)
        if isinstance(reason, TimeoutError) or 'timed out' in str(reason).lower():
            raise SmsDeliveryError(TIMEOUT) from exc
        raise SmsDeliveryError(UNREACHABLE) from exc


def _provider_id_from(mapping):
    if not isinstance(mapping, dict):
        return ''
    for key in ('id', 'message_id', 'messageId'):
        if mapping.get(key) not in (None, ''):
            return str(mapping.get(key))
    return ''


def _truthy_ok(value):
    return value in (True, 1, '1', 'true', 'True', 'ok', 'OK', 'yes', 'YES')


def _success_from_sms_envelope(sms):
    """Parse the SMSMobileAPI envelope: {\"sms\": {\"ok\": true, \"details\": {...}}}."""
    if not isinstance(sms, dict):
        return None
    details = sms.get('details') if isinstance(sms.get('details'), dict) else {}
    error = details.get('error', sms.get('error'))
    ok = sms.get('ok')

    if ok is not None and not _truthy_ok(ok):
        raise SmsDeliveryError(REFUSED)
    if error not in (None, 0, '0', False) and error != '':
        raise SmsDeliveryError(REFUSED)

    # Accepted when sms.ok is true, and/or details.error is 0 with a successful send flag.
    accepted = _truthy_ok(ok)
    if not accepted and error in (0, '0', False):
        accepted = True
    if not accepted and details.get('sent') in (1, '1', True, 'true', 'True'):
        accepted = True
    if not accepted:
        return None

    # trial_account.sms_sent may be 0 on a successful trial send; do not require it.
    return {
        'accepted': True,
        'provider_id': _provider_id_from(details) or _provider_id_from(sms),
    }


def _success_from_mapping(result):
    if not isinstance(result, dict):
        return None

    if isinstance(result.get('sms'), dict):
        return _success_from_sms_envelope(result.get('sms'))

    if 'error' in result:
        error = result.get('error')
        if error in (0, '0', False):
            return {
                'accepted': True,
                'provider_id': _provider_id_from(result),
            }
        raise SmsDeliveryError(REFUSED)

    status = result.get('status', result.get('State', result.get('state')))
    if isinstance(status, str) and status.strip().lower() in {
        'ok', 'okay', 'success', 'accepted', 'sent', 'queued', '0', '1',
    }:
        return {
            'accepted': True,
            'provider_id': _provider_id_from(result),
        }
    if result.get('success') in (True, 1, '1', 'true', 'True'):
        return {
            'accepted': True,
            'provider_id': _provider_id_from(result),
        }
    if result.get('sent') in (1, '1', True, 'true', 'True'):
        return {
            'accepted': True,
            'provider_id': _provider_id_from(result),
        }
    if _truthy_ok(result.get('ok')):
        details = result.get('details') if isinstance(result.get('details'), dict) else {}
        return {
            'accepted': True,
            'provider_id': _provider_id_from(details) or _provider_id_from(result),
        }
    return None


def parse_sendsms_body(raw, *, content_type='', api_key='', http_status=200):
    text = _decode_body(raw).lstrip('\ufeff').strip()
    status = int(http_status or 0)

    if not text:
        if 200 <= status < 300:
            return {'accepted': True, 'provider_id': ''}
        raise SmsDeliveryError(UNUSABLE)

    payload = None
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        payload = None

    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        payload = payload[0]

    if isinstance(payload, dict):
        # Prefer documented/live envelopes in order: sms → result → top-level.
        candidates = []
        if isinstance(payload.get('sms'), dict):
            candidates.append(payload)
        if isinstance(payload.get('result'), dict):
            candidates.append(payload.get('result'))
        candidates.append(payload)

        last_reject = None
        for candidate in candidates:
            try:
                parsed = _success_from_mapping(candidate)
            except SmsDeliveryError as exc:
                last_reject = exc
                continue
            if parsed:
                return parsed
        if last_reject is not None:
            _log_provider_exchange(
                status=status,
                content_type=content_type,
                body=text,
                api_key=api_key,
                outcome='error',
                detail='provider_rejected',
            )
            raise last_reject
        _log_provider_exchange(
            status=status,
            content_type=content_type,
            body=text,
            api_key=api_key,
            outcome='error',
            detail='json_unrecognized',
        )
        raise SmsDeliveryError(UNUSABLE)

    if 200 <= status < 300 and _PLAIN_SUCCESS.match(text):
        return {'accepted': True, 'provider_id': ''}

    lower = text.lower()
    if 200 <= status < 300 and any(
        token in lower for token in ('"error":0', '"error": 0', 'sent by mobile')
    ):
        return {'accepted': True, 'provider_id': ''}

    _log_provider_exchange(
        status=status,
        content_type=content_type,
        body=text,
        api_key=api_key,
        outcome='error',
        detail='unusable_body',
    )
    raise SmsDeliveryError(UNUSABLE)


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
    posted = poster(fields, timeout)
    if isinstance(posted, tuple) and len(posted) == 3:
        status, raw, content_type = posted
    else:
        status, raw = posted
        content_type = ''

    status = int(status or 0)
    if status in (401, 403):
        _log_provider_exchange(
            status=status,
            content_type=content_type,
            body=raw,
            api_key=key,
            outcome='error',
            detail='auth_refused',
        )
        raise SmsDeliveryError(REFUSED)

    try:
        accepted = parse_sendsms_body(
            raw,
            content_type=content_type,
            api_key=key,
            http_status=status,
        )
    except SmsDeliveryError as exc:
        if status >= 400 and exc.user_message == UNUSABLE:
            _log_provider_exchange(
                status=status,
                content_type=content_type,
                body=raw,
                api_key=key,
                outcome='error',
                detail='http_status',
            )
        raise

    if status >= 400:
        # Parsed body claimed success on an HTTP error — still refuse.
        _log_provider_exchange(
            status=status,
            content_type=content_type,
            body=raw,
            api_key=key,
            outcome='error',
            detail='http_error_with_body',
        )
        raise SmsDeliveryError(UNUSABLE)

    _log_provider_exchange(
        status=status,
        content_type=content_type,
        body=raw,
        api_key=key,
        outcome='info',
        detail='accepted',
    )
    return accepted
