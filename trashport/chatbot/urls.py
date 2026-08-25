from django.urls import path
from .views import ChatFeedbackView

app_name = "chatbot"

urlpatterns = [
    path("feedback/", ChatFeedbackView.as_view(), name="chatbot-feedback"),
]
