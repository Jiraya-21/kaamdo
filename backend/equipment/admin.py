"""
Admin registration for equipment listings and rental requests.
"""

from django.contrib import admin

from .models import EquipmentBooking, EquipmentInquiry, EquipmentListing, FeeStatus


@admin.register(EquipmentListing)
class EquipmentListingAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'owner', 'district', 'pricing_basis', 'rate', 'fee_status', 'status')
    list_filter = ('status', 'fee_status', 'pricing_basis', 'operator_included', 'district')
    search_fields = ('title', 'district', 'locality')
    actions = ['mark_fee_paid', 'mark_fee_waived']

    @admin.action(description='Mark the listing fee paid')
    def mark_fee_paid(self, request, queryset):
        queryset.update(fee_status=FeeStatus.PAID)

    @admin.action(description='Waive the listing fee')
    def mark_fee_waived(self, request, queryset):
        queryset.update(fee_status=FeeStatus.WAIVED)


@admin.register(EquipmentInquiry)
class EquipmentInquiryAdmin(admin.ModelAdmin):
    list_display = ('id', 'listing', 'customer', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('requirement',)


@admin.register(EquipmentBooking)
class EquipmentBookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'listing', 'renter', 'start_date', 'end_date', 'status')
    list_filter = ('status',)
