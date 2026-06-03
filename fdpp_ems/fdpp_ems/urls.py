from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404
import os
import mimetypes


def api_404(request, exception=None):
    if request.path.startswith('/api/'):
        return JsonResponse({
            'error': 'Endpoint not found',
            'detail': 'The requested API endpoint or resource was not found. Verify the URL and required parameters.'
        }, status=404)
    from django.shortcuts import render
    return render(request, '404.html', status=404)


def serve_media_files(request, file_path):
    """Serve uploaded media files."""
    full_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, file_path))
    media_root = os.path.normpath(settings.MEDIA_ROOT)
    if not full_path.startswith(media_root):
        raise Http404("Invalid path")
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise Http404("File not found")
    content_type, _ = mimetypes.guess_type(full_path)
    resp = FileResponse(open(full_path, 'rb'), content_type=content_type or 'application/octet-stream')
    resp['Content-Length'] = os.path.getsize(full_path)
    return resp


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include('management.urls')),
]

if settings.MEDIA_URL and settings.MEDIA_ROOT:
    media_prefix = settings.MEDIA_URL.strip('/')
    urlpatterns.insert(0, re_path(
        r'^' + media_prefix + r'/(?P<file_path>.+)$',
        serve_media_files,
        name='serve_media'
    ))

handler404 = 'fdpp_ems.urls.api_404'
