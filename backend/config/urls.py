"""
KaamDo Master URL Configuration
All domain API routes are aggregated under /api/v1/.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

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
