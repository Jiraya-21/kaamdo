from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class LocationDistrict(models.Model):
    """Seeded official district. The catalog module remains the source of truth."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LocationTaluk(models.Model):
    """Seeded official taluk. No village rows and no coordinates."""

    district = models.ForeignKey(
        LocationDistrict,
        on_delete=models.CASCADE,
        related_name='taluks',
    )
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['district', 'name'],
                name='locations_taluk_district_name',
            ),
        ]

    def __str__(self):
        return f'{self.name}, {self.district.name}'


class ListingPlace(models.Model):
    """Optional taluk label for an existing listing row. Not a map point."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_pk = models.CharField(max_length=64)
    item = GenericForeignKey('content_type', 'object_pk')
    district = models.CharField(max_length=100)
    taluk = models.CharField(max_length=120, blank=True)
    locality = models.CharField(max_length=120, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_pk'],
                name='locations_listingplace_item_unique',
            ),
        ]

    def __str__(self):
        return f'{self.locality} {self.taluk} {self.district}'.strip()
