from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.maps import public_map_config

from .catalog import catalog_payload, normalize_district, taluk_names


class LocationCatalogView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(catalog_payload())


class LocationDistrictListView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        payload = catalog_payload()
        return Response({
            'state': payload['state'],
            'results': [{'name': row['name']} for row in payload['districts']],
        })


class LocationTalukListView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        district = normalize_district(request.query_params.get('district'))
        if not district:
            return Response(
                {'detail': 'Choose an official Karnataka district.'},
                status=400,
            )
        return Response({
            'district': district,
            'results': [{'name': name} for name in taluk_names(district)],
        })


class MapConfigView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(public_map_config(
            getattr(settings, 'KAAMDO_MAP_PROVIDER', 'none'),
            getattr(settings, 'KAAMDO_MAP_ATTRIBUTION', ''),
        ))
