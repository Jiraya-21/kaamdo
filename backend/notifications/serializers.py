from rest_framework import serializers

from .models import InAppNotification


class InAppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = ['id', 'kind', 'title', 'body', 'payload', 'read_at', 'created_at']
        read_only_fields = fields
