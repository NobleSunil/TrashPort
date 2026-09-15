from django.urls import path
from .consumers import ChatbotConsumer

websocket_urlpatterns = [
    path("ws/chatbot/", ChatbotConsumer.as_asgi()),
]
