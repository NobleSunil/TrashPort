"""
WebSocket URL routing definitions for maps and live GPS tracking.

Maps ASGI WebSocket endpoints to LiveTrackingConsumer for citizen and admin clients.
"""

from django.urls import path
from .consumers import LiveTrackingConsumer

# WebSocket URL patterns consumed by config/asgi.py
websocket_urlpatterns = [
    # Citizen-facing live tracking endpoint for an individual pickup request
    path("ws/maps/tracking/<int:pickup_id>/", LiveTrackingConsumer.as_asgi()),
    # Admin-facing live map endpoint streaming telemetry for all active collectors
    path("ws/maps/admin-live/", LiveTrackingConsumer.as_asgi()),
]
