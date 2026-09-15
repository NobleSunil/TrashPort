import pytest
from rest_framework.test import APIRequestFactory
from trashport.firebase.authentication import FirebaseTokenAuthentication
from django.contrib.auth import get_user_model

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestFirebaseTokenAuthentication:
    def test_valid_mock_token_authenticates(self):
        auth = FirebaseTokenAuthentication()
        factory = APIRequestFactory()
        request = factory.get("/api/firebase/me/", HTTP_AUTHORIZATION="Bearer mock-token-testuser")

        user, decoded = auth.authenticate(request)
        assert user is not None
        assert user.firebase_uid == "testuser"
        assert decoded["uid"] == "testuser"

    def test_no_auth_header_returns_none(self):
        auth = FirebaseTokenAuthentication()
        factory = APIRequestFactory()
        request = factory.get("/api/firebase/me/")
        assert auth.authenticate(request) is None
