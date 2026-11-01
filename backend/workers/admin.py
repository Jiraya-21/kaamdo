"""
Admin registration for worker profiles, skills, and provider verification.
"""

from django.contrib import admin
from django.utils import timezone

from .models import (
    DailyServiceRequest,
    ServiceCategory,
    ServiceOffer,
    ServiceProviderVerification,
    Skill,
    VisitFeeConfiguration,
    VisitPayment,
    WorkerProfile,
)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'district',
        'locality',
        'availability',
        'publication_status',
        'service_rate',
        'pricing_basis',
    )
    list_filter = ('publication_status', 'availability', 'pricing_basis', 'district')
    search_fields = ('user__first_name', 'user__last_name', 'district', 'locality', 'bio')
    filter_horizontal = ('skills', 'service_categories')
    readonly_fields = ('created_at', 'updated_at')
    fields = (
        'user',
        'photo',
        'bio',
        'skills',
        'service_categories',
        'experience_years',
        'service_rate',
        'pricing_basis',
        'district',
        'locality',
        'latitude',
        'longitude',
        'service_radius_km',
        'availability',
        'publication_status',
        'created_at',
        'updated_at',
    )


@admin.action(description='Approve selected provider applications')
def approve_verifications(modeladmin, request, queryset):
    queryset.update(
        status=ServiceProviderVerification.Status.APPROVED,
        reviewed_at=timezone.now(),
        reviewed_by=request.user,
    )


@admin.action(description='Reject selected provider applications')
def reject_verifications(modeladmin, request, queryset):
    queryset.update(
        status=ServiceProviderVerification.Status.REJECTED,
        reviewed_at=timezone.now(),
        reviewed_by=request.user,
    )


@admin.action(description='Ask selected providers for more information')
def request_verification_info(modeladmin, request, queryset):
    queryset.update(
        status=ServiceProviderVerification.Status.NEEDS_INFO,
        reviewed_at=timezone.now(),
        reviewed_by=request.user,
    )


@admin.register(ServiceProviderVerification)
class ServiceProviderVerificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'submitted_at', 'reviewed_at')
    list_filter = ('status',)
    search_fields = ('user__first_name', 'user__last_name', 'user__phone_number', 'applicant_note')
    readonly_fields = ('submitted_at', 'reviewed_at', 'reviewed_by')
    actions = [approve_verifications, reject_verifications, request_verification_info]

    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(DailyServiceRequest)
class DailyServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'category', 'status', 'radius_km', 'created_at')
    list_filter = ('status', 'category')
    readonly_fields = ('created_at', 'updated_at')
    exclude = ('access_key_hash',)


@admin.register(ServiceOffer)
class ServiceOfferAdmin(admin.ModelAdmin):
    list_display = ('id', 'request', 'profile', 'state', 'offered_at')
    list_filter = ('state',)
    readonly_fields = ('offered_at', 'responded_at')


@admin.register(VisitFeeConfiguration)
class VisitFeeConfigurationAdmin(admin.ModelAdmin):
    list_display = ('amount_inr', 'currency', 'is_active', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(VisitPayment)
class VisitPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'request', 'amount_inr', 'currency', 'state', 'verification_source')
    list_filter = ('state', 'verification_source')
    readonly_fields = ('reference', 'recorded_at', 'verified_at')
