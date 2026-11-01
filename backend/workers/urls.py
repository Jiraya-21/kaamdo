"""
Worker URL configuration.
Routes under /api/v1/workers/.
"""

from django.urls import path

from .views import (
    DailyServiceCancelView,
    DailyServiceExpandView,
    DailyServiceMatchView,
    MockVisitPaymentView,
    MyDailyServiceRequestListView,
    MyServiceOfferListView,
    ServiceOfferResponseView,
    GuestDailyServiceRequestCreateView,
    GuestDailyServiceRequestStatusView,
    IncomingServiceRequestListView,
    OwnWorkerProfilePhotoView,
    OwnWorkerProfileView,
    PublishedWorkerDetailView,
    PublishedWorkerListView,
    ServiceCategoryListView,
    ServiceProviderVerificationView,
    ServiceRequestDetailView,
    ServiceRequestListCreateView,
)

app_name = 'workers'

urlpatterns = [
    path('categories/', ServiceCategoryListView.as_view(), name='service-categories'),
    path('daily-requests/', GuestDailyServiceRequestCreateView.as_view(), name='guest-daily-requests'),
    path('daily-requests/mine/', MyDailyServiceRequestListView.as_view(), name='my-daily-requests'),
    path('daily-requests/status/', GuestDailyServiceRequestStatusView.as_view(), name='daily-request-status'),
    path('daily-offers/mine/', MyServiceOfferListView.as_view(), name='my-daily-offers'),
    path('daily-requests/expand/', DailyServiceExpandView.as_view(), name='guest-daily-request-expand'),
    path('daily-requests/cancel/', DailyServiceCancelView.as_view(), name='guest-daily-request-cancel'),
    path('daily-requests/<int:pk>/match/', DailyServiceMatchView.as_view(), name='daily-request-match'),
    path('daily-requests/<int:pk>/expand/', DailyServiceExpandView.as_view(), name='daily-request-expand'),
    path('daily-requests/<int:pk>/cancel/', DailyServiceCancelView.as_view(), name='daily-request-cancel'),
    path('daily-requests/<int:pk>/mock-payment/', MockVisitPaymentView.as_view(), name='daily-request-mock-payment'),
    path('daily-offers/<int:offer_id>/respond/', ServiceOfferResponseView.as_view(), name='daily-offer-respond'),
    path('', PublishedWorkerListView.as_view(), name='worker-list'),
    path('profile/', OwnWorkerProfileView.as_view(), name='worker-own-profile'),
    path('profile/photo/', OwnWorkerProfilePhotoView.as_view(), name='worker-own-profile-photo'),
    path('requests/', ServiceRequestListCreateView.as_view(), name='service-requests'),
    path('requests/incoming/', IncomingServiceRequestListView.as_view(), name='incoming-service-requests'),
    path('requests/<int:pk>/', ServiceRequestDetailView.as_view(), name='service-request-detail'),
    path('verification/', ServiceProviderVerificationView.as_view(), name='worker-verification'),
    path('<int:pk>/', PublishedWorkerDetailView.as_view(), name='worker-detail'),
]
