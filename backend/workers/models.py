"""
Worker profiles.
A worker account can have one public professional profile. Account secrets stay on the user.
"""

import secrets
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

from .contacts import daily_contact_phone_ready
from .matching_columns import matching_offer_columns_ready, matching_request_columns_ready
from .photos import (
    delete_stored_photo,
    validate_worker_photo,
    worker_photo_column_ready,
    worker_photo_upload_to,
)


WORKER_PROFILE_SAFE_FIELDS = (
    'id',
    'user',
    'experience_years',
    'bio',
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


class WorkerProfileQuerySet(models.QuerySet):
    def defer_unmigrated_photo(self):
        if worker_photo_column_ready():
            return self
        # only() is required. defer() is ignored by DISTINCT count queries, which
        # still SELECT photo and fail on an unmigrated local SQLite file.
        return self.only(*WORKER_PROFILE_SAFE_FIELDS)


class WorkerProfileManager(models.Manager):
    def get_queryset(self):
        return WorkerProfileQuerySet(self.model, using=self._db).defer_unmigrated_photo()


class Skill(models.Model):
    """A reusable service name, such as plumbing or electrical work."""

    name = models.CharField(max_length=80)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(Lower('name'), name='workers_skill_name_ci_unique'),
        ]

    def __str__(self):
        return self.name


class WorkerProfile(models.Model):
    """Professional details for one worker account."""

    class PricingBasis(models.TextChoices):
        HOURLY = 'hourly', 'Hourly'
        DAILY = 'daily', 'Daily'

    class Availability(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        UNAVAILABLE = 'unavailable', 'Unavailable'

    class PublicationStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='worker_profile',
    )
    skills = models.ManyToManyField(Skill, related_name='worker_profiles', blank=True)
    service_categories = models.ManyToManyField(
        'ServiceCategory',
        related_name='worker_profiles',
        blank=True,
        help_text='Bookable daily-service categories. These are chosen directly and are not copied from skills.',
    )
    experience_years = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(60)],
    )
    bio = models.TextField(validators=[MaxLengthValidator(500)])
    service_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    pricing_basis = models.CharField(max_length=10, choices=PricingBasis.choices)
    district = models.CharField(max_length=100)
    locality = models.CharField(max_length=120)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    service_radius_km = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text='Fixed maximum kilometres this worker can travel. This is separate from the customer search radius.',
    )
    availability = models.CharField(
        max_length=20,
        choices=Availability.choices,
        default=Availability.AVAILABLE,
    )
    publication_status = models.CharField(
        max_length=20,
        choices=PublicationStatus.choices,
        default=PublicationStatus.DRAFT,
    )
    photo = models.ImageField(
        upload_to=worker_photo_upload_to,
        blank=True,
        null=True,
        validators=[validate_worker_photo],
        help_text='Optional public profile photo. JPEG, PNG, or WebP. Maximum 2 MB.',
    )
    kaamdo_worker_id = models.CharField(
        max_length=16,
        unique=True,
        null=True,
        blank=True,
        help_text='Permanent public KaamDo Worker ID. Assigned once; never reuse across people.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = WorkerProfileManager()

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['publication_status'], name='workers_profile_status_idx'),
            models.Index(fields=['district'], name='workers_profile_district_idx'),
            models.Index(fields=['kaamdo_worker_id'], name='workers_profile_worker_id_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(experience_years__gte=0) & models.Q(experience_years__lte=60),
                name='workers_profile_experience_range',
            ),
            models.CheckConstraint(
                condition=models.Q(service_rate__gt=0),
                name='workers_profile_rate_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(service_radius_km__gte=1) & models.Q(service_radius_km__lte=100),
                name='workers_profile_radius_range',
            ),
        ]

    def __str__(self):
        return f'{self.display_name} ({self.district})'

    @property
    def display_name(self):
        name = self.user.get_full_name().strip()
        return name or 'Worker'

    def clean(self):
        super().clean()
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError('Latitude and longitude must be provided together.')
        if self.latitude is not None and not (Decimal('-90') <= self.latitude <= Decimal('90')):
            raise ValidationError({'latitude': 'Latitude must be between -90 and 90.'})
        if self.longitude is not None and not (Decimal('-180') <= self.longitude <= Decimal('180')):
            raise ValidationError({'longitude': 'Longitude must be between -180 and 180.'})


class ServiceProviderVerification(models.Model):
    """Staff review of a service provider. A profile or a published page is not verification."""

    class Status(models.TextChoices):
        NOT_SUBMITTED = 'not_submitted', 'Not submitted'
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        NEEDS_INFO = 'needs_info', 'Additional information required'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='service_provider_verification',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_SUBMITTED,
    )
    applicant_note = models.TextField(blank=True)
    review_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_provider_reviews',
    )

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.user_id}:{self.status}'


def service_provider_can_publish(user):
    """Published provider actions require an active account and an approved application."""
    if user is None or not getattr(user, 'is_authenticated', False) or not user.is_active:
        return False
    from accounts.models import Capability

    if not user.has_capability(Capability.SERVICE_PROVIDER):
        return False
    try:
        verification = user.service_provider_verification
    except ServiceProviderVerification.DoesNotExist:
        return False
    return verification.status == ServiceProviderVerification.Status.APPROVED


class ServiceRequest(models.Model):
    """A customer asking one published provider to do a piece of work."""

    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Requested'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'
        CLOSED = 'closed', 'Closed'

    profile = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='service_requests')
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='service_requests',
    )
    description = models.TextField(validators=[MaxLengthValidator(1000)])
    contact_phone = models.CharField(max_length=10)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.customer_id} -> profile {self.profile_id}'


class ServiceCategory(models.Model):
    """A bookable daily service, such as electrician or plumber. This is not a worker skill."""

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'service categories'
        constraints = [
            models.UniqueConstraint(Lower('name'), name='workers_category_name_ci_uniq'),
        ]

    def __str__(self):
        return self.name


DAILY_REQUEST_SAFE_FIELDS = (
    'id',
    'category',
    'customer',
    'guest_name',
    'contact_email',
    'access_key_hash',
    'description',
    'latitude',
    'longitude',
    'radius_km',
    'status',
    'assigned_profile',
    'created_at',
    'updated_at',
)
DAILY_REQUEST_MATCHING_FIELDS = (
    'search_radius_km',
    'consented_radius_km',
    'match_attempts',
    'match_reason',
)
SERVICE_OFFER_SAFE_FIELDS = (
    'id',
    'request',
    'profile',
    'state',
    'offered_at',
    'responded_at',
)


class DailyServiceRequestQuerySet(models.QuerySet):
    def defer_unready_columns(self):
        if daily_contact_phone_ready() and matching_request_columns_ready():
            return self
        fields = list(DAILY_REQUEST_SAFE_FIELDS)
        if daily_contact_phone_ready():
            fields.append('contact_phone')
        return self.only(*fields)


class DailyServiceRequestManager(models.Manager):
    def get_queryset(self):
        return DailyServiceRequestQuerySet(self.model, using=self._db).defer_unready_columns()


class DailyServiceRequest(models.Model):
    """A category request from a guest or a registered customer. It is not tied to one worker at creation."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        AWAITING_PAYMENT = 'awaiting_payment', 'Awaiting payment'
        DISPATCH_PENDING = 'dispatch_pending', 'Ready to offer after a recorded payment'
        NO_WORKERS = 'no_workers', 'No eligible worker in range'
        OFFERING = 'offering', 'Offered to eligible workers'
        ASSIGNED = 'assigned', 'Assigned'
        WORKER_CANCELLED = 'worker_cancelled', 'Worker cancelled before the visit'
        NO_ACCEPTANCE = 'no_acceptance', 'No worker accepted'
        IN_PROGRESS = 'in_progress', 'Service in progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUND_REQUESTED = 'refund_requested', 'Refund requested'

    TRANSITIONS = {
        Status.DRAFT: {Status.AWAITING_PAYMENT, Status.CANCELLED},
        Status.AWAITING_PAYMENT: {Status.DISPATCH_PENDING, Status.NO_WORKERS, Status.CANCELLED},
        Status.DISPATCH_PENDING: {Status.OFFERING, Status.NO_WORKERS, Status.CANCELLED},
        Status.NO_WORKERS: {Status.DISPATCH_PENDING, Status.OFFERING, Status.REFUND_REQUESTED, Status.CANCELLED},
        Status.OFFERING: {Status.ASSIGNED, Status.NO_ACCEPTANCE, Status.NO_WORKERS, Status.CANCELLED},
        Status.ASSIGNED: {Status.WORKER_CANCELLED, Status.IN_PROGRESS, Status.CANCELLED},
        Status.WORKER_CANCELLED: {Status.OFFERING, Status.NO_WORKERS, Status.REFUND_REQUESTED},
        Status.NO_ACCEPTANCE: {Status.OFFERING, Status.NO_WORKERS, Status.REFUND_REQUESTED, Status.CANCELLED},
        Status.IN_PROGRESS: {Status.COMPLETED},
        Status.COMPLETED: {Status.REFUND_REQUESTED},
        Status.CANCELLED: set(),
        Status.REFUND_REQUESTED: set(),
    }
    ASSIGNED_STATUSES = {
        Status.ASSIGNED,
        Status.WORKER_CANCELLED,
        Status.IN_PROGRESS,
        Status.COMPLETED,
    }

    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name='daily_requests',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daily_service_requests',
    )
    guest_name = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(
        max_length=10,
        blank=True,
        help_text='Verified guest mobile number. Blank when the guest used email.',
    )
    access_key_hash = models.CharField(max_length=128, blank=True)
    description = models.TextField(validators=[MaxLengthValidator(1000)])
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius_km = models.PositiveSmallIntegerField(
        default=60,
        validators=[MinValueValidator(5), MaxValueValidator(100)],
        help_text='Kilometres chosen by the customer, from 5 to 100. Matching still expands 8, 15, then 20 km up to this cap.',
    )
    search_radius_km = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text='Current matching radius. Never larger than the consented limit.',
    )
    consented_radius_km = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text='Customer-approved search limit beyond the original radius. Blank until they agree.',
    )
    match_attempts = models.PositiveSmallIntegerField(default=0)
    match_reason = models.CharField(max_length=32, blank=True, default='')
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)
    assigned_profile = models.ForeignKey(
        WorkerProfile,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='assigned_daily_requests',
    )
    arrival_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Set only after the request owner confirms the booking arrival code.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = DailyServiceRequestManager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status'], name='workers_daily_status_idx'),
            models.Index(fields=['category'], name='workers_daily_category_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(radius_km__gte=5) & models.Q(radius_km__lte=100),
                name='workers_daily_radius_chk',
            ),
        ]

    def __str__(self):
        return f'Daily request {self.pk or "new"} ({self.status})'

    def set_access_key(self, raw_key):
        """Store a hash only. The raw key is the guest's proof of ownership."""
        if not isinstance(raw_key, str) or len(raw_key) < 20:
            raise ValidationError({'access_key_hash': 'The access key must be a long random value.'})
        self.access_key_hash = make_password(raw_key)

    def check_access_key(self, raw_key):
        if not self.access_key_hash or not raw_key:
            return False
        return check_password(str(raw_key), self.access_key_hash)

    def _unready_field_names(self):
        names = set()
        if not daily_contact_phone_ready():
            names.add('contact_phone')
        if not matching_request_columns_ready():
            names.update(DAILY_REQUEST_MATCHING_FIELDS)
        return names

    def _do_insert(self, manager, using, fields, returning_fields, raw):
        skip = self._unready_field_names()
        if skip:
            fields = [field for field in fields if field.name not in skip]
            if returning_fields:
                returning_fields = [
                    field for field in returning_fields if field.name not in skip
                ]
        return super()._do_insert(manager, using, fields, returning_fields, raw)

    def _do_update(self, base_qs, using, pk_val, values, update_fields, forced_update, returning_fields):
        skip = self._unready_field_names()
        if skip:
            values = [item for item in values if item[0].name not in skip]
            if returning_fields:
                returning_fields = [
                    field for field in returning_fields if field.name not in skip
                ]
        return super()._do_update(
            base_qs,
            using,
            pk_val,
            values,
            update_fields,
            forced_update,
            returning_fields,
        )

    def clean(self):
        super().clean()
        if self.contact_email:
            self.contact_email = self.contact_email.strip().lower()
        if self.customer_id is None:
            if not (self.guest_name or '').strip():
                raise ValidationError({'guest_name': 'A guest request needs the customer name.'})
            has_email = bool(self.contact_email)
            has_phone = bool((self.contact_phone or '').strip())
            if not has_email and not has_phone and not getattr(self, '_guest_phone_verified', False):
                raise ValidationError({
                    'contact_email': 'A guest request needs a verified mobile number or email address.',
                })
        if self._state.adding and self.category_id and not self.category.is_active:
            raise ValidationError({'category': 'Choose an active service category.'})
        if self.access_key_hash and '$' not in self.access_key_hash:
            raise ValidationError({'access_key_hash': 'Store only a hashed access key, never a raw code.'})
        if not (Decimal('-90') <= self.latitude <= Decimal('90')):
            raise ValidationError({'latitude': 'Latitude must be between -90 and 90.'})
        if not (Decimal('-180') <= self.longitude <= Decimal('180')):
            raise ValidationError({'longitude': 'Longitude must be between -180 and 180.'})
        if self.status in self.ASSIGNED_STATUSES and self.assigned_profile_id is None:
            raise ValidationError({'assigned_profile': 'This status needs an assigned worker.'})
        open_statuses = {
            self.Status.DRAFT,
            self.Status.AWAITING_PAYMENT,
            self.Status.DISPATCH_PENDING,
            self.Status.OFFERING,
            self.Status.NO_WORKERS,
            self.Status.NO_ACCEPTANCE,
        }
        if self.status in open_statuses and self.assigned_profile_id is not None:
            raise ValidationError({'assigned_profile': 'Clear the assigned worker before using this status.'})

    def transition_to(self, new_status, *, assigned_profile=None):
        allowed = self.TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError({'status': f'A {self.status} request cannot move to {new_status}.'})
        previous_profile = self.assigned_profile
        previous_status = self.status
        if new_status == self.Status.ASSIGNED and assigned_profile is not None:
            self.assigned_profile = assigned_profile
            # Replacement or first assignment: previous arrival proof does not carry over.
            self.arrival_verified_at = None
        if new_status == self.Status.OFFERING and self.status == self.Status.WORKER_CANCELLED:
            self.assigned_profile = None
            self.arrival_verified_at = None
        if new_status == self.Status.WORKER_CANCELLED:
            self.arrival_verified_at = None
        self.status = new_status
        self.full_clean()
        self.save()
        self._record_assignment_transition(
            previous_status=previous_status,
            previous_profile=previous_profile,
            new_status=new_status,
        )

    def _record_assignment_transition(self, *, previous_status, previous_profile, new_status):
        """Audit assignment, replacement, and clear open arrival codes when the worker changes."""
        from .arrival import invalidate_open_arrival_challenges, record_assignment_event

        if new_status == self.Status.ASSIGNED and self.assigned_profile_id:
            previous_id = previous_profile.pk if previous_profile is not None else None
            if previous_id and previous_id != self.assigned_profile_id:
                record_assignment_event(
                    self,
                    previous_profile,
                    DailyServiceAssignmentEvent.Event.REPLACED,
                    note='Assigned worker replaced; customer must verify the new worker.',
                )
                invalidate_open_arrival_challenges(self)
            record_assignment_event(
                self,
                self.assigned_profile,
                DailyServiceAssignmentEvent.Event.ASSIGNED,
                note='Worker accepted and was assigned to this request.',
            )
            return
        if new_status == self.Status.WORKER_CANCELLED and previous_profile is not None:
            record_assignment_event(
                self,
                previous_profile,
                DailyServiceAssignmentEvent.Event.WORKER_CANCELLED,
                note='Assigned worker cancelled before the visit.',
            )
            invalidate_open_arrival_challenges(self)
            return
        if (
            new_status == self.Status.OFFERING
            and previous_status == self.Status.WORKER_CANCELLED
        ):
            invalidate_open_arrival_challenges(self)


class DailyServiceAssignmentEvent(models.Model):
    """Auditable history of who was assigned, replaced, verified, or completed a request."""

    class Event(models.TextChoices):
        ASSIGNED = 'assigned', 'Assigned'
        REPLACED = 'replaced', 'Replaced'
        WORKER_CANCELLED = 'worker_cancelled', 'Worker cancelled'
        ARRIVAL_SIGNALLED = 'arrival_signalled', 'Arrival signalled'
        ARRIVAL_VERIFIED = 'arrival_verified', 'Arrival verified'
        COMPLETED = 'completed', 'Completed'

    request = models.ForeignKey(
        DailyServiceRequest,
        on_delete=models.CASCADE,
        related_name='assignment_events',
    )
    profile = models.ForeignKey(
        WorkerProfile,
        on_delete=models.PROTECT,
        related_name='assignment_events',
    )
    event = models.CharField(max_length=32, choices=Event.choices)
    note = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['request', 'created_at'], name='workers_assign_evt_req_idx'),
        ]

    def __str__(self):
        return f'{self.request_id}:{self.event}:{self.profile_id}'


class DailyServiceArrivalChallenge(models.Model):
    """Booking-specific arrival code. Separate from login and guest OTP."""

    request = models.ForeignKey(
        DailyServiceRequest,
        on_delete=models.CASCADE,
        related_name='arrival_challenges',
    )
    assigned_profile = models.ForeignKey(
        WorkerProfile,
        on_delete=models.PROTECT,
        related_name='arrival_challenges',
    )
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempt_count = models.PositiveSmallIntegerField(default=0)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_arrivals',
    )
    superseded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['request', 'created_at'], name='workers_arrival_req_idx'),
        ]

    def __str__(self):
        return f'Arrival challenge {self.pk} for request {self.request_id}'


class ServiceOfferQuerySet(models.QuerySet):
    def defer_unready_expiry(self):
        if matching_offer_columns_ready():
            return self
        return self.only(*SERVICE_OFFER_SAFE_FIELDS)


class ServiceOfferManager(models.Manager):
    def get_queryset(self):
        return ServiceOfferQuerySet(self.model, using=self._db).defer_unready_expiry()


class ServiceOffer(models.Model):
    """One offer of a request to one worker. The same worker cannot be offered the same request twice."""

    class State(models.TextChoices):
        OFFERED = 'offered', 'Offered'
        DECLINED = 'declined', 'Declined'
        ACCEPTED = 'accepted', 'Accepted'
        EXPIRED = 'expired', 'Expired'
        WITHDRAWN = 'withdrawn', 'Withdrawn before the visit'

    request = models.ForeignKey(
        DailyServiceRequest,
        on_delete=models.CASCADE,
        related_name='offers',
    )
    profile = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name='daily_service_offers',
    )
    state = models.CharField(max_length=20, choices=State.choices, default=State.OFFERED)
    offered_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    objects = ServiceOfferManager()

    class Meta:
        ordering = ['-offered_at']
        constraints = [
            models.UniqueConstraint(
                fields=['request', 'profile'],
                name='workers_offer_req_profile_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['state', 'expires_at'], name='workers_offer_exp_idx'),
        ]

    def __str__(self):
        return f'Offer {self.pk or "new"} ({self.state})'

    def _do_insert(self, manager, using, fields, returning_fields, raw):
        if not matching_offer_columns_ready():
            fields = [field for field in fields if field.name != 'expires_at']
            if returning_fields:
                returning_fields = [
                    field for field in returning_fields if field.name != 'expires_at'
                ]
        return super()._do_insert(manager, using, fields, returning_fields, raw)

    def _do_update(self, base_qs, using, pk_val, values, update_fields, forced_update, returning_fields):
        if not matching_offer_columns_ready():
            values = [item for item in values if item[0].name != 'expires_at']
            if returning_fields:
                returning_fields = [
                    field for field in returning_fields if field.name != 'expires_at'
                ]
        return super()._do_update(
            base_qs,
            using,
            pk_val,
            values,
            update_fields,
            forced_update,
            returning_fields,
        )


class VisitFeeConfiguration(models.Model):
    """The administrator-controlled visit fee. Booking code must read this row instead of assuming an amount."""

    amount_inr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    currency = models.CharField(max_length=3, default='INR')
    is_active = models.BooleanField(default=True)
    note = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'visit fee configuration'
        constraints = [
            models.UniqueConstraint(
                fields=['is_active'],
                condition=models.Q(is_active=True),
                name='workers_visit_fee_active_uniq',
            ),
            models.CheckConstraint(
                condition=models.Q(currency='INR') & models.Q(amount_inr__gt=0),
                name='workers_visit_fee_inr_chk',
            ),
        ]

    def __str__(self):
        return f'Visit fee {self.amount_inr} {self.currency}'

    def clean(self):
        super().clean()
        if self.currency != 'INR':
            raise ValidationError({'currency': 'The visit fee must be in Indian rupees.'})


def get_active_visit_fee():
    """Return the active fee row, or None when an administrator has not configured one."""
    return VisitFeeConfiguration.objects.filter(is_active=True).order_by('-updated_at').first()


class VisitPayment(models.Model):
    """One visit charge for one request. A mock record is not proof that money was received."""

    class State(models.TextChoices):
        PENDING = 'pending', 'Pending'
        MOCK_RECORDED = 'mock_recorded', 'Mock demo recorded (not money received)'
        GATEWAY_VERIFIED = 'gateway_verified', 'Verified by a payment gateway'
        FAILED = 'failed', 'Failed'
        REFUND_REQUESTED = 'refund_requested', 'Refund requested'
        REFUND_PENDING = 'refund_pending', 'Refund pending'
        REFUNDED = 'refunded', 'Refunded'

    class Source(models.TextChoices):
        NONE = 'none', 'None'
        MOCK_DEMO = 'mock_demo', 'Mock demo'
        PAYMENT_GATEWAY = 'payment_gateway', 'Payment gateway'

    TRANSITIONS = {
        State.PENDING: {State.MOCK_RECORDED, State.GATEWAY_VERIFIED, State.FAILED},
        State.MOCK_RECORDED: {State.REFUND_REQUESTED, State.FAILED},
        State.GATEWAY_VERIFIED: {State.REFUND_REQUESTED},
        State.FAILED: {State.PENDING},
        State.REFUND_REQUESTED: {State.REFUND_PENDING, State.REFUNDED},
        State.REFUND_PENDING: {State.REFUNDED},
        State.REFUNDED: set(),
    }

    request = models.OneToOneField(
        DailyServiceRequest,
        on_delete=models.CASCADE,
        related_name='visit_payment',
    )
    amount_inr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    currency = models.CharField(max_length=3, default='INR')
    state = models.CharField(max_length=32, choices=State.choices, default=State.PENDING)
    verification_source = models.CharField(max_length=32, choices=Source.choices, default=Source.NONE)
    reference = models.CharField(max_length=64, unique=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(currency='INR') & models.Q(amount_inr__gt=0),
                name='workers_visit_pay_inr_chk',
            ),
            models.CheckConstraint(
                condition=(
                    (~models.Q(state='mock_recorded') | models.Q(verification_source='mock_demo'))
                    & (~models.Q(state='gateway_verified') | models.Q(verification_source='payment_gateway'))
                    & (~models.Q(state='mock_recorded') | models.Q(verified_at__isnull=True))
                ),
                name='workers_visit_pay_source_chk',
            ),
        ]

    def __str__(self):
        return f'Visit payment {self.pk or "new"} ({self.state})'

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = secrets.token_hex(16)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.currency != 'INR':
            raise ValidationError({'currency': 'Visit payments must be in Indian rupees.'})
        if self.state == self.State.MOCK_RECORDED and self.verification_source != self.Source.MOCK_DEMO:
            raise ValidationError({'verification_source': 'A mock record must be marked as a mock demo. It is not money received.'})
        if self.state == self.State.GATEWAY_VERIFIED:
            if self.verification_source != self.Source.PAYMENT_GATEWAY:
                raise ValidationError({'verification_source': 'Only a payment gateway can verify a real payment.'})
            if self.verified_at is None:
                raise ValidationError({'verified_at': 'A gateway verification needs the time it was confirmed.'})
        if self.state == self.State.MOCK_RECORDED and self.verified_at is not None:
            raise ValidationError({'verified_at': 'A mock payment cannot carry a real verification time.'})
        if self.verification_source == self.Source.MOCK_DEMO and self.state == self.State.GATEWAY_VERIFIED:
            raise ValidationError({'state': 'A mock demo cannot be recorded as gateway-verified money.'})

    def transition_to(self, new_state, *, verification_source=None, verified_at=None):
        allowed = self.TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise ValidationError({'state': f'A {self.state} payment cannot move to {new_state}.'})
        if new_state == self.State.GATEWAY_VERIFIED and self.state == self.State.MOCK_RECORDED:
            raise ValidationError({'state': 'A mock demo cannot become a real payment.'})
        if verification_source is not None:
            self.verification_source = verification_source
        if verified_at is not None:
            self.verified_at = verified_at
        self.state = new_state
        self.full_clean()
        self.save()


class ServicePriceMenuItem(models.Model):
    """Company price menu: fixed inspection fee label + extra work items workers may add."""

    class Kind(models.TextChoices):
        INSPECTION = 'inspection', 'Inspection fee'
        EXTRA = 'extra', 'Extra work'

    code = models.SlugField(max_length=64, unique=True)
    title = models.CharField(max_length=120)
    description = models.CharField(max_length=240, blank=True)
    amount_inr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.EXTRA)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ['sort_order', 'title']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_inr__gt=0),
                name='workers_price_menu_amount_chk',
            ),
        ]

    def __str__(self):
        return f'{self.title} ({self.amount_inr} INR)'


class RequestExtraCharge(models.Model):
    """Extra work line proposed after inspection. Mock paid is not money received."""

    class State(models.TextChoices):
        PROPOSED = 'proposed', 'Proposed'
        MOCK_PAID = 'mock_paid', 'Mock paid (not money received)'
        CANCELLED = 'cancelled', 'Cancelled'

    request = models.ForeignKey(
        DailyServiceRequest,
        on_delete=models.CASCADE,
        related_name='extra_charges',
    )
    menu_item = models.ForeignKey(
        ServicePriceMenuItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='extra_charges',
    )
    title = models.CharField(max_length=120)
    amount_inr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    state = models.CharField(max_length=16, choices=State.choices, default=State.PROPOSED)
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proposed_extra_charges',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_inr__gt=0),
                name='workers_extra_charge_amount_chk',
            ),
        ]

    def __str__(self):
        return f'{self.title} ({self.state})'


@receiver(post_delete, sender=WorkerProfile)
def _remove_worker_photo_file(sender, instance, **kwargs):
    delete_stored_photo(instance)
