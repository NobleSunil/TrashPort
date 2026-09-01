from django.urls import path
from .consumers import LiveTrackingConsumer

websocket_urlpatterns = [
    path("ws/maps/tracking/<int:pickup_id>/", LiveTrackingConsumer.as_asgi()),
    path("ws/maps/admin-live/", LiveTrackingConsumer.as_asgi()),
]
