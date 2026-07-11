import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render

FRONTEND_DIST = Path(settings.BASE_DIR) / 'frontend' / 'dist'


def _safe_dist_path(relative: str) -> Path:
    target = (FRONTEND_DIST / relative).resolve()
    root = FRONTEND_DIST.resolve()
    if not str(target).startswith(str(root)):
        raise Http404('Invalid path')
    return target


def serve_frontend_index(request):
    """Sert index.html du build Vite (SPA Vue)."""
    index = FRONTEND_DIST / 'index.html'
    if not index.is_file():
        return render(request, 'home.html')
    return FileResponse(index.open('rb'), content_type='text/html; charset=utf-8')


def serve_frontend_asset(request, path: str):
    """Sert JS/CSS/images du build Vite (/assets/...)."""
    file_path = _safe_dist_path(path)
    if not file_path.is_file():
        raise Http404
    content_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(
        file_path.open('rb'),
        content_type=content_type or 'application/octet-stream',
    )


def serve_favicon(request):
    return serve_frontend_asset(request, 'favicon.svg')
