"""Serve the static frontend/ tree from the same host as the API."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.views import View


def frontend_root() -> Path:
    configured = getattr(settings, 'FRONTEND_ROOT', None)
    if configured:
        return Path(configured).resolve()
    return (Path(settings.BASE_DIR).parent / 'frontend').resolve()


class FrontendView(View):
    """Serve HTML/CSS/JS/images from FRONTEND_ROOT. API routes stay first in urls.py."""

    def get(self, request, rest=''):
        root = frontend_root()
        if not root.is_dir():
            raise Http404('Frontend is not packaged on this host.')

        relative = str(rest or '').lstrip('/')
        if not relative or relative.endswith('/'):
            relative = f'{relative}index.html'

        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise Http404() from exc

        if candidate.is_dir():
            candidate = (candidate / 'index.html').resolve()
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise Http404() from exc

        if not candidate.is_file():
            raise Http404()

        content_type, _encoding = mimetypes.guess_type(str(candidate))
        return FileResponse(
            candidate.open('rb'),
            content_type=content_type or 'application/octet-stream',
        )
