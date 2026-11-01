from django.contrib import admin

from .models import ListingPlace, LocationDistrict, LocationTaluk


@admin.register(LocationDistrict)
class LocationDistrictAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name', 'slug')


@admin.register(LocationTaluk)
class LocationTalukAdmin(admin.ModelAdmin):
    search_fields = ('name', 'district__name')
    list_display = ('name', 'district')
    list_filter = ('district',)


@admin.register(ListingPlace)
class ListingPlaceAdmin(admin.ModelAdmin):
    search_fields = ('district', 'taluk', 'locality')
    list_display = ('district', 'taluk', 'locality', 'object_pk')
