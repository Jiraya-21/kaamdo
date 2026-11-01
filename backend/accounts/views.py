"""
Accounts views.
Registration, phone login, token logout, capabilities, active mode, and the current user.
"""

from django.contrib.auth.hashers import check_password, make_password
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AccountCapability, User
from .otp import (
    account_otp_phone,
    guest_otp_contact,
    guest_otp_options,
    send_guest_email_otp,
    send_guest_phone_otp,
    send_otp,
    verify_guest_email_otp,
    verify_guest_phone_otp,
    verify_otp,
)
from .otp_ip import enforce_otp_ip_limit
from .serializers import (
    ActiveModeSerializer,
    EnableCapabilitySerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)

INVALID_LOGIN = 'Invalid phone number or password.'
# A fixed hash keeps failed lookups about as slow as a real password check.
_DUMMY_PASSWORD_HASH = make_password('kaamdo-invalid-login')


class OtpIpLimitedMixin:
    """Count this IP before auth so missing tokens cannot skip the cap."""

    otp_ip_action = 'send'

    def initial(self, request, *args, **kwargs):
        enforce_otp_ip_limit(request, self.otp_ip_action)
        super().initial(request, *args, **kwargs)


def _user_payload(user, token):
    return {
        'token': token.key,
        'user': UserSerializer(user).data,
    }


class RegisterView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = Token.objects.create(user=user)
        return Response(_user_payload(user, token), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone_number']
        password = serializer.validated_data['password']

        user = User.objects.filter(phone_number=phone).first()
        password_hash = user.password if user is not None else _DUMMY_PASSWORD_HASH
        password_matches = check_password(password, password_hash)
        if user is None or not user.is_active or not password_matches:
            raise AuthenticationFailed(INVALID_LOGIN)

        token, _created = Token.objects.get_or_create(user=user)
        return Response(_user_payload(user, token))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class CapabilityView(APIView):
    """Enable another activity on the same account. This does not change the open screen."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EnableCapabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountCapability.objects.get_or_create(
            user=request.user,
            code=serializer.validated_data['capability'],
        )
        return Response(UserSerializer(request.user).data)


class OtpSendView(OtpIpLimitedMixin, APIView):
    permission_classes = [IsAuthenticated]
    otp_ip_action = 'send'

    def post(self, request):
        phone = account_otp_phone(request.user)
        purpose = request.data.get('purpose', 'account')
        return Response(send_otp(request.user, phone, purpose))


class OtpVerifyView(OtpIpLimitedMixin, APIView):
    permission_classes = [IsAuthenticated]
    otp_ip_action = 'verify'

    def post(self, request):
        phone = account_otp_phone(request.user)
        return Response(verify_otp(
            request.user,
            phone,
            request.data.get('purpose', 'account'),
            request.data.get('code', ''),
        ))


class GuestOtpOptionsView(APIView):
    """Tell a guest which contact checks can actually run. This does not send a code."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(guest_otp_options())


class GuestOtpSendView(OtpIpLimitedMixin, APIView):
    """Send a guest mobile or email code. This does not create an account."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]
    otp_ip_action = 'send'

    def post(self, request):
        kind, value = guest_otp_contact(request.data)
        purpose = request.data.get('purpose', '')
        if kind == 'phone':
            return Response(send_guest_phone_otp(value, purpose))
        return Response(send_guest_email_otp(value, purpose))


class GuestOtpVerifyView(OtpIpLimitedMixin, APIView):
    """Verify a guest mobile or email code. Success does not create an account or a booking."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]
    otp_ip_action = 'verify'

    def post(self, request):
        kind, value = guest_otp_contact(request.data)
        purpose = request.data.get('purpose', '')
        code = request.data.get('code', '')
        if kind == 'phone':
            return Response(verify_guest_phone_otp(value, purpose, code))
        return Response(verify_guest_email_otp(value, purpose, code))


class ActiveModeView(APIView):
    """Change the open screen. The token and the capability list stay the same."""

    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = ActiveModeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.active_mode = serializer.validated_data['active_mode']
        request.user.save(update_fields=['active_mode'])
        return Response(UserSerializer(request.user).data)
