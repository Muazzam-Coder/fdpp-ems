"""
ASGI config for fdpp_ems project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
import django
from django.urls import re_path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fdpp_ems.settings')

# Initialize Django first before importing anything that uses models
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

django_asgi_app = get_asgi_application()

# Now import consumers after Django is initialized
from management import consumers

websocket_urlpatterns = [
    # re_path(r'ws/attendance/$', consumers.AttendanceConsumer.as_asgi()),
    re_path(r'ws/biometric/$', consumers.BiometricConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
