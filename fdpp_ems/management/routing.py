from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    # Biometric device integration (for biometric script)
    re_path(r'ws/biometric/$', consumers.BiometricConsumer.as_asgi()),
]
