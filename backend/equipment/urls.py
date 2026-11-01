"""
Equipment routes under /api/v1/equipment/.
"""

from django.urls import path

from .views import (
    EquipmentBookingDetailView,
    EquipmentInquiryDetailView,
    EquipmentListingDetailView,
    EquipmentListingListCreateView,
    MyEquipmentListingListView,
    ListingBookingView,
    ListingInquiryView,
    MyEquipmentBookingListView,
    MyEquipmentInquiryListView,
)

app_name = 'equipment'

urlpatterns = [
    path('', EquipmentListingListCreateView.as_view(), name='listing-list'),
    path('mine/', MyEquipmentListingListView.as_view(), name='my-listings'),
    path('bookings/', MyEquipmentBookingListView.as_view(), name='my-bookings'),
    path('inquiries/', MyEquipmentInquiryListView.as_view(), name='my-inquiries'),
    path('inquiries/<int:pk>/', EquipmentInquiryDetailView.as_view(), name='inquiry-detail'),
    path('bookings/<int:pk>/', EquipmentBookingDetailView.as_view(), name='booking-detail'),
    path('<int:pk>/', EquipmentListingDetailView.as_view(), name='listing-detail'),
    path('<int:listing_pk>/bookings/', ListingBookingView.as_view(), name='listing-bookings'),
    path('<int:listing_pk>/inquiries/', ListingInquiryView.as_view(), name='listing-inquiries'),
]
