"""
Equipment rental models.

Listings and bookings are separate from jobs and from agricultural hiring.
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinValueValidator
from django.db import models

from .photos import equipment_photo_upload_to, validate_equipment_photo


class ListingStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'
    CLOSED = 'closed', 'Closed'


class PricingBasis(models.TextChoices):
    HOURLY = 'hourly', 'Hourly'
    DAILY = 'daily', 'Daily'


class BookingStatus(models.TextChoices):
    REQUESTED = 'requested', 'Requested'
    ACCEPTED = 'accepted', 'Accepted'
    DECLINED = 'declined', 'Declined'


class FeeStatus(models.TextChoices):
    UNPAID = 'unpaid', 'Unpaid'
    PAID = 'paid', 'Paid'
    WAIVED = 'waived', 'Waived'


class InquiryStatus(models.TextChoices):
    NEW = 'new', 'New'
    SEEN = 'seen', 'Seen'
    CLOSED = 'closed', 'Closed'


class EquipmentListing(models.Model):
    """Machinery offered for rent by one account."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='equipment_listings',
    )
    title = models.CharField(max_length=120)
    description = models.TextField(validators=[MaxLengthValidator(2000)])
    district = models.CharField(max_length=100)
    locality = models.CharField(max_length=120)
    pricing_basis = models.CharField(max_length=10, choices=PricingBasis.choices)
    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    operator_included = models.BooleanField(default=False)
    availability_note = models.CharField(max_length=200, blank=True)
    photo = models.ImageField(
        upload_to=equipment_photo_upload_to,
        blank=True,
        null=True,
        validators=[validate_equipment_photo],
        help_text='Optional public listing photo. JPEG, PNG, or WebP. Maximum 2 MB.',
    )
    fee_status = models.CharField(max_length=20, choices=FeeStatus.choices, default=FeeStatus.UNPAID)
    fee_note = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ListingStatus.choices,
        default=ListingStatus.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status'], name='equipment_listing_status_idx'),
            models.Index(fields=['district'], name='equipment_listing_district_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rate__gt=0),
                name='equipment_listing_rate_positive',
            ),
        ]

    def __str__(self):
        return self.title


class EquipmentBooking(models.Model):
    """A renter's request for one equipment listing."""

    listing = models.ForeignKey(
        EquipmentListing,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    renter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='equipment_bookings',
    )
    start_date = models.DateField()
    end_date = models.DateField()
    note = models.TextField(blank=True, validators=[MaxLengthValidator(1000)])
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.REQUESTED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['listing', 'renter'],
                condition=models.Q(status=BookingStatus.REQUESTED),
                name='equipment_one_open_request_per_renter',
            ),
        ]

    def __str__(self):
        return f'{self.renter_id} -> listing {self.listing_id}'

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'The end date cannot be before the start date.'})


class EquipmentInquiry(models.Model):
    """A customer asking the owner to make contact. This does not reserve the equipment."""

    listing = models.ForeignKey(
        EquipmentListing,
        on_delete=models.CASCADE,
        related_name='inquiries',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='equipment_inquiries',
    )
    contact_phone = models.CharField(max_length=10)
    requirement = models.TextField(validators=[MaxLengthValidator(1000)])
    preferred_timing = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=InquiryStatus.choices, default=InquiryStatus.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.customer_id} -> listing {self.listing_id}'
