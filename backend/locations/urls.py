from django.urls import path

from .views import (
    LocationCatalogView,
    LocationDistrictListView,
    LocationTalukListView,
    MapConfigView,
    ReverseGeocodeView,
)

app_name = 'locations'

urlpatterns = [
    path('catalog/', LocationCatalogView.as_view(), name='catalog'),
    path('districts/', LocationDistrictListView.as_view(), name='districts'),
    path('taluks/', LocationTalukListView.as_view(), name='taluks'),
    path('map-config/', MapConfigView.as_view(), name='map-config'),
    path('reverse/', ReverseGeocodeView.as_view(), name='reverse'),
]
