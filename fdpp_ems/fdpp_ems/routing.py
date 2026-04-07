# WebSocket routing is now handled directly in asgi.py
# This file is kept for reference only

from django.urls import re_path, include
from management.routing import websocket_urlpatterns

# Not used - asgi.py imports consumers directly
# websocket_urlpatterns = websocket_urlpatterns

