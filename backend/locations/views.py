from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.otp_ip import client_ip
from config.maps import public_map_config

from .catalog import catalog_payload, normalize_district, normalize_state, taluk_names
from .geocode import normalize_geocode_provider, reverse_lookup


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
        state_name = normalize_state(request.query_params.get('state'))
        if state_name:
            chosen = next((row for row in payload.get('states', []) if row['name'] == state_name), None)
            rows = chosen['districts'] if chosen else []
            state = {'code': chosen['code'], 'name': chosen['name']} if chosen else payload['state']
        else:
            rows = payload['districts']
            state = payload['state']
        return Response({
            'state': state,
            'results': [{'name': row['name']} for row in rows],
        })


class LocationTalukListView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        district = normalize_district(request.query_params.get('district'))
        if not district:
            return Response(
                {'detail': 'Choose an official Karnataka or Maharashtra district.'},
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
        payload = public_map_config(
            getattr(settings, 'KAAMDO_MAP_PROVIDER', 'none'),
            getattr(settings, 'KAAMDO_MAP_ATTRIBUTION', ''),
        )
        payload['reverse_geocode'] = normalize_geocode_provider(
            getattr(settings, 'KAAMDO_GEOCODE_PROVIDER', 'none'),
        )
        return Response(payload)


class ReverseGeocodeView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data if hasattr(request, 'data') else {}
        result = reverse_lookup(
            data.get('latitude'),
            data.get('longitude'),
            ip=client_ip(getattr(request, 'META', {})),
        )
        if result['reason'] == 'invalid_coordinates':
            return Response(result, status=400)
        if result['reason'] == 'rate_limited':
            return Response(result, status=429)
        if result['reason'] == 'provider_unavailable':
            return Response(result, status=503)
        return Response(result)
