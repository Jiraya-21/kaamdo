"""
Reliability Views.
API endpoints for:
- GET /api/v1/workers/<id>/reliability/ (Public score summary)
- GET /api/v1/workers/me/reliability-dashboard/ (Private worker score breakdown & coaching)
- POST /api/v1/reliability/disputes/ (File dispute)
- POST /api/v1/reliability/appeals/ (Submit appeal)
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

# Reliability views will be implemented in the feature phase
