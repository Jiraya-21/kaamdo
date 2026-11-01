"""Create in-app notifications. Fail closed if the table has not been migrated."""

from django.db.utils import OperationalError, ProgrammingError


def notify_user(user, kind, title, body, payload=None):
    if user is None or not getattr(user, 'pk', None):
        return None
    from .models import InAppNotification

    try:
        return InAppNotification.objects.create(
            user=user,
            kind=str(kind or '')[:64],
            title=str(title or '')[:160],
            body=str(body or '')[:500],
            payload=payload or {},
        )
    except (OperationalError, ProgrammingError):
        return None
