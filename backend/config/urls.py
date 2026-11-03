"""
KaamDo Master URL Configuration
All domain API routes are aggregated under /api/v1/.
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

from .frontend import FrontendView
from .health import HealthView

urlpatterns = [
    path('healthz', HealthView.as_view(), name='healthz'),
    # Django Admin Site
    path('admin/', admin.site.urls),

    # KaamDo API Endpoints (Version 1)
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/workers/', include('workers.urls')),
    path('api/v1/jobs/', include('jobs.urls')),
    path('api/v1/equipment/', include('equipment.urls')),
    path('api/v1/reviews/', include('reviews.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    path('api/v1/reliability/', include('reliability.urls')),
    path('api/v1/locations/', include('locations.urls')),
]

# Serve media files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Public site HTML/assets (same Render URL as the API). Keep last.
urlpatterns += [
    path('', FrontendView.as_view(), name='frontend-home'),
    re_path(r'^(?P<rest>.+)$', FrontendView.as_view(), name='frontend-path'),
]
