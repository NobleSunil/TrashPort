import pytest
from rest_framework.test import APIClient
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestChatbotAPI:
    def test_send_chat_message_endpoint(self):
        client = APIClient()
        url = reverse("chatbot:send_message")
        response = client.post(url, {
            "message": "Hi, can you help me schedule a pickup?"
        }, format="json")
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "session_key" in data
