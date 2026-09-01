from django.urls import path
from .views import ChatFeedbackView, send_chat_message_view

app_name = "chatbot"

urlpatterns = [
    path("send-message/", send_chat_message_view, name="send_message"),
    path("feedback/", ChatFeedbackView.as_view(), name="chatbot-feedback"),
]
