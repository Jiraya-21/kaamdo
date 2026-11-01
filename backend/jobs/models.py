"""
Jobs models.

Ordinary employment and agricultural hiring use separate tables.
An abstract base only shares field definitions. It does not create a table.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.db import models


class PostingStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'
    CLOSED = 'closed', 'Closed'


class ApplicationStatus(models.TextChoices):
    SUBMITTED = 'submitted', 'Submitted'
    WITHDRAWN = 'withdrawn', 'Withdrawn'
    ACCEPTED = 'accepted', 'Accepted'
    REJECTED = 'rejected', 'Rejected'


class WagePeriod(models.TextChoices):
    HOURLY = 'hourly', 'Hourly'
    DAILY = 'daily', 'Daily'
    WEEKLY = 'weekly', 'Weekly'
    MONTHLY = 'monthly', 'Monthly'


class ReviewStatus(models.TextChoices):
    PENDING = 'pending', 'Pending review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    NEEDS_INFO = 'needs_info', 'More information required'


class WorkType(models.TextChoices):
    FULL_TIME = 'full_time', 'Full time'
    PART_TIME = 'part_time', 'Part time'
    TEMPORARY = 'temporary', 'Temporary'
    CONTRACT = 'contract', 'Contract'


class PostingBase(models.Model):
    """Shared columns for a hiring post. Subclasses each get their own table."""

    title = models.CharField(max_length=120)
    description = models.TextField(validators=[MaxLengthValidator(2000)])
    district = models.CharField(max_length=100)
    locality = models.CharField(max_length=120)
    wage_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    wage_negotiable = models.BooleanField(default=False)
    wage_period = models.CharField(max_length=20, choices=WagePeriod.choices, default=WagePeriod.DAILY)
    headcount = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    review_note = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=PostingStatus.choices,
        default=PostingStatus.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class ApplicationBase(models.Model):
    """Shared columns for an application. Subclasses each get their own table."""

    message = models.TextField(blank=True, validators=[MaxLengthValidator(1000)])
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.SUBMITTED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class Job(PostingBase):
    """An ordinary employment post. Agricultural hiring does not use this table."""

    poster = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posted_jobs',
    )
    work_type = models.CharField(max_length=20, choices=WorkType.choices, default=WorkType.TEMPORARY)

    class Meta(PostingBase.Meta):
        indexes = [
            models.Index(fields=['status'], name='jobs_job_status_idx'),
            models.Index(fields=['district'], name='jobs_job_district_idx'),
        ]

    def __str__(self):
        return self.title


class JobApplication(ApplicationBase):
    """One person's application to one ordinary job."""

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_applications',
    )

    class Meta(ApplicationBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=['job', 'applicant'],
                name='jobs_application_one_per_applicant',
            ),
        ]

    def __str__(self):
        return f'{self.applicant_id} -> job {self.job_id}'


class AgriculturalJob(PostingBase):
    """A farm hiring post. Ordinary jobs and equipment listings do not use this table."""

    poster = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posted_agricultural_jobs',
    )
    work_start = models.DateField(null=True, blank=True)
    work_end = models.DateField(null=True, blank=True)
    working_hours = models.CharField(max_length=80, blank=True)

    class Meta(PostingBase.Meta):
        indexes = [
            models.Index(fields=['status'], name='jobs_agjob_status_idx'),
            models.Index(fields=['district'], name='jobs_agjob_district_idx'),
        ]

    def __str__(self):
        return self.title


class AgriculturalJobApplication(ApplicationBase):
    """One person's application to one agricultural job."""

    job = models.ForeignKey(
        AgriculturalJob,
        on_delete=models.CASCADE,
        related_name='applications',
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='agricultural_job_applications',
    )

    class Meta(ApplicationBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=['job', 'applicant'],
                name='jobs_ag_application_one_per_applicant',
            ),
        ]

    def __str__(self):
        return f'{self.applicant_id} -> agricultural job {self.job_id}'


class EmployerProfile(models.Model):
    """Who is hiring. Phone verification and this review are separate from job approval."""

    class Domain(models.TextChoices):
        ORDINARY = 'ordinary', 'Ordinary jobs'
        AGRICULTURAL = 'agricultural', 'Agricultural jobs'

    class PartyType(models.TextChoices):
        INDIVIDUAL = 'individual', 'Individual'
        BUSINESS = 'business', 'Business'

    class Status(models.TextChoices):
        NOT_SUBMITTED = 'not_submitted', 'Not submitted'
        PENDING = 'pending', 'Pending review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        NEEDS_INFO = 'needs_info', 'More information required'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employer_profiles',
    )
    domain = models.CharField(max_length=20, choices=Domain.choices)
    full_name = models.CharField(max_length=150)
    party_type = models.CharField(max_length=20, choices=PartyType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_SUBMITTED)
    review_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'domain'], name='jobs_employer_profile_user_domain'),
        ]

    def __str__(self):
        return f'{self.user_id}:{self.domain}:{self.status}'
