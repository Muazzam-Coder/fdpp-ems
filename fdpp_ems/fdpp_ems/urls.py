from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def api_404(request, exception=None):
    """Return JSON 404 for API paths, otherwise fall back to default HTML 404.

    This helps API clients receive a consistent, user-friendly message when
    an endpoint is not found or required path parameters are missing.
    """
    # Only return JSON for API namespace; let Django handle regular site 404s
    if request.path.startswith('/api/'):
        return JsonResponse({
            'error': 'Endpoint not found',
            'detail': 'The requested API endpoint or resource was not found. Verify the URL and required parameters.'
        }, status=404)
    # For non-API requests, let Django render the default 404 page
    from django.shortcuts import render
    return render(request, '404.html', status=404)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include('management.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Wire up our custom 404 handler for API-friendly JSON responses
handler404 = 'fdpp_ems.urls.api_404'