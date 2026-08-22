from django.urls import path
from .views import send_chat_message_view

app_name = "chatbot"

urlpatterns = [
    path("message/", send_chat_message_view, name="send_message"),
]
