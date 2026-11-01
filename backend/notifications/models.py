"""In-app notifications. These are not SMS or email."""

from django.conf import settings
from django.db import models


class InAppNotification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='in_app_notifications',
    )
    kind = models.CharField(max_length=64)
    title = models.CharField(max_length=160)
    body = models.CharField(max_length=500)
    payload = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user_id}:{self.kind}'
