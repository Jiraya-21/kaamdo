"""
Accounts URL configuration.
Routes for authentication and user accounts under /api/v1/auth/.
"""

from django.urls import path

from .views import (
    ActiveModeView,
    CapabilityView,
    LoginView,
    LogoutView,
    MeView,
    GuestOtpOptionsView,
    GuestOtpSendView,
    GuestOtpVerifyView,
    OtpSendView,
    OtpVerifyView,
    RegisterView,
)

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', MeView.as_view(), name='me'),
    path('capabilities/', CapabilityView.as_view(), name='capabilities'),
    path('mode/', ActiveModeView.as_view(), name='active-mode'),
    path('otp/send/', OtpSendView.as_view(), name='otp-send'),
    path('otp/verify/', OtpVerifyView.as_view(), name='otp-verify'),
    path('otp/guest/options/', GuestOtpOptionsView.as_view(), name='guest-otp-options'),
    path('otp/guest/send/', GuestOtpSendView.as_view(), name='guest-otp-send'),
    path('otp/guest/verify/', GuestOtpVerifyView.as_view(), name='guest-otp-verify'),
]
