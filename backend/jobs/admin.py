"""
Admin registration for ordinary jobs and agricultural hiring.
"""

from django.contrib import admin
from django.utils import timezone

from .models import (
    AgriculturalJob,
    AgriculturalJobApplication,
    EmployerProfile,
    Job,
    JobApplication,
    PostingStatus,
    ReviewStatus,
)


def approve_posts(modeladmin, request, queryset):
    queryset.update(
        review_status=ReviewStatus.APPROVED,
        status=PostingStatus.PUBLISHED,
        reviewed_at=timezone.now(),
    )


approve_posts.short_description = 'Approve and publish selected posts'


def hold_posts(modeladmin, request, queryset):
    queryset.update(review_status=ReviewStatus.PENDING, status=PostingStatus.DRAFT, reviewed_at=timezone.now())


hold_posts.short_description = 'Hold selected posts for review'


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'poster', 'district', 'status', 'review_status', 'created_at')
    list_filter = ('status', 'review_status', 'district')
    search_fields = ('title', 'district', 'locality')
    actions = [approve_posts, hold_posts]


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'applicant', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(AgriculturalJob)
class AgriculturalJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'poster', 'district', 'status', 'review_status', 'created_at')
    list_filter = ('status', 'review_status', 'district')
    search_fields = ('title', 'district', 'locality')
    actions = [approve_posts, hold_posts]


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'domain', 'party_type', 'status', 'submitted_at')
    list_filter = ('domain', 'status', 'party_type')
    actions = ['approve_employers', 'reject_employers']

    @admin.action(description='Approve selected employer reviews')
    def approve_employers(self, request, queryset):
        queryset.update(status=EmployerProfile.Status.APPROVED, reviewed_at=timezone.now())

    @admin.action(description='Reject selected employer reviews')
    def reject_employers(self, request, queryset):
        queryset.update(status=EmployerProfile.Status.REJECTED, reviewed_at=timezone.now())


@admin.register(AgriculturalJobApplication)
class AgriculturalJobApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'applicant', 'status', 'created_at')
    list_filter = ('status',)
