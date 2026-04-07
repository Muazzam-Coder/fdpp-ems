from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    # Attendance real-time updates (for UI/mobile apps)
    re_path(r'ws/attendance/$', consumers.AttendanceConsumer.as_asgi()),
    
    # Biometric device integration (for biometric script)
    re_path(r'ws/biometric/$', consumers.BiometricConsumer.as_asgi()),
]
