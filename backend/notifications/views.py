"""List and mark in-app notifications. No SMS or email is sent."""

from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InAppNotification
from .serializers import InAppNotificationSerializer


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            rows = InAppNotification.objects.filter(user=request.user)[:50]
            data = InAppNotificationSerializer(rows, many=True).data
        except (OperationalError, ProgrammingError):
            data = []
        return Response(data)


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = InAppNotification.objects.filter(user=request.user, pk=pk).first()
        except (OperationalError, ProgrammingError):
            return Response({'detail': 'Notifications are not available on this database.'}, status=400)
        if notification is None:
            return Response({'detail': 'Notification not found.'}, status=404)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=['read_at'])
        return Response(InAppNotificationSerializer(notification).data)
