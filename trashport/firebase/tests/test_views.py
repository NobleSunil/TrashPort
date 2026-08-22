import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestFirebaseViews:
    def test_verify_token_view(self):
        client = APIClient()
        url = reverse("firebase:verify_token")
        response = client.post(url, {
            "token": "mock-token-firebasecitizen",
            "role": "CITIZEN",
            "name": "Firebase Citizen"
        }, format="json")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["user"]["email"] == "firebasecitizen@trashport.local"
        assert data["user"]["role"] == "CITIZEN"

    def test_me_view_authenticated(self):
        client = APIClient()
        user = User.objects.create_user(
            email="meuser@trashport.local",
            name="Me User",
            role="CITIZEN",
        )
        client.force_authenticate(user=user)
        url = reverse("firebase:me")
        response = client.get(url)
        assert response.status_code == 200
        assert response.json()["email"] == "meuser@trashport.local"
