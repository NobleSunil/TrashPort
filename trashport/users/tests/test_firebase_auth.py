import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import AuthenticationFailed
from trashport.users.authentication import FirebaseAuthentication

User = get_user_model()
pytestmark = pytest.mark.django_db

class TestFirebaseAuthentication:
    @pytest.fixture
    def auth(self) -> FirebaseAuthentication:
        return FirebaseAuthentication()

    @pytest.fixture
    def api_rf(self) -> APIRequestFactory:
        return APIRequestFactory()

    def test_no_auth_header(self, auth: FirebaseAuthentication, api_rf: APIRequestFactory):
        request = api_rf.get("/api/users/me/")
        result = auth.authenticate(request)
        assert result is None

    def test_malformed_auth_header(self, auth: FirebaseAuthentication, api_rf: APIRequestFactory):
        request = api_rf.get("/api/users/me/", HTTP_AUTHORIZATION="Bearer")
        result = auth.authenticate(request)
        assert result is None

        request = api_rf.get("/api/users/me/", HTTP_AUTHORIZATION="Token some_token")
        result = auth.authenticate(request)
        assert result is None

    @patch("firebase_admin.auth.verify_id_token")
    def test_invalid_firebase_token(self, mock_verify, auth: FirebaseAuthentication, api_rf: APIRequestFactory):
        mock_verify.side_effect = Exception("Token expired")
        request = api_rf.get("/api/users/me/", HTTP_AUTHORIZATION="Bearer invalid-token")
        
        with pytest.raises(AuthenticationFailed) as exc_info:
            auth.authenticate(request)
        assert "Invalid or expired Firebase token" in str(exc_info.value)

    def test_valid_mock_token_creates_user(self, auth: FirebaseAuthentication, api_rf: APIRequestFactory):
        uid = "firebase-test-123"
        email = f"{uid}@example.com"
        
        # Ensure user does not exist beforehand
        assert not User.objects.filter(firebase_uid=uid).exists()
        assert not User.objects.filter(email=email).exists()

        request = api_rf.get("/api/users/me/", HTTP_AUTHORIZATION=f"Bearer mock-token-{uid}")
        user, decoded = auth.authenticate(request)

        # User should be created
        assert user.firebase_uid == uid
        assert user.email == email
        assert user.name == uid.capitalize()
        assert decoded["uid"] == uid

    def test_valid_mock_token_retrieves_existing_user_by_uid(self, auth: FirebaseAuthentication, api_rf: APIRequestFactory):
        uid = "firebase-test-456"
        email = f"{uid}@example.com"
        
        # Pre-create user with firebase_uid
        existing_user = User.objects.create(
            firebase_uid=uid,
            email=email,
            name="Existing User",
            role=User.Roles.CITIZEN
        )

        request = api_rf.get("/api/users/me/", HTTP_AUTHORIZATION=f"Bearer mock-token-{uid}")
        user, decoded = auth.authenticate(request)

        assert user.pk == existing_user.pk
        assert user.firebase_uid == uid

    def test_valid_mock_token_maps_existing_user_by_email(self, auth: FirebaseAuthentication, api_rf: APIRequestFactory):
        uid = "firebase-test-789"
        email = f"{uid}@example.com"
        
        # Pre-create user with matching email but no firebase_uid
        existing_user = User.objects.create(
            email=email,
            name="Existing Email User",
            role=User.Roles.CITIZEN
        )

        request = api_rf.get("/api/users/me/", HTTP_AUTHORIZATION=f"Bearer mock-token-{uid}")
        user, decoded = auth.authenticate(request)

        assert user.pk == existing_user.pk
        assert user.firebase_uid == uid  # Should be updated and linked


from django.test import Client
from django.urls import reverse

class TestFirebaseSessionLoginView:
    def test_get_not_allowed(self):
        client = Client()
        url = reverse("users:firebase_login")
        response = client.get(url)
        assert response.status_code == 405

    def test_post_missing_token(self):
        client = Client()
        url = reverse("users:firebase_login")
        response = client.post(url, data={}, content_type="application/json")
        assert response.status_code == 400
        assert "Missing Firebase token" in response.json()["message"]

    def test_post_valid_mock_token_logs_in(self):
        client = Client()
        url = reverse("users:firebase_login")

        uid = "mock-citizen"
        response = client.post(
            url,
            data={"token": f"mock-token-{uid}", "role": "CITIZEN"},
            content_type="application/json"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        # New users are redirected to profile setup
        assert data["redirect_url"] == "/users/~update/"
        assert data["is_new_user"] is True

        # Check that user is logged in
        assert int(client.session["_auth_user_id"]) > 0

        # Second login with same token → existing user → dashboard
        response2 = client.post(
            url,
            data={"token": f"mock-token-{uid}"},
            content_type="application/json"
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["redirect_url"] == "/dashboard/"
        assert data2["is_new_user"] is False


class TestPasswordSessionAuthView:
    def test_signup_creates_and_logs_in_user(self):
        client = Client()
        url = reverse("users:password_signup")
        email = "newcitizen@example.com"
        password = "SecurePassword123!"

        response = client.post(
            url,
            data={"email": email, "password": password, "role": "CITIZEN"},
            content_type="application/json"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        user = User.objects.get(email=email)
        assert user.role == User.Roles.CITIZEN
        assert user.check_password(password)
        assert int(client.session["_auth_user_id"]) == user.pk

    def test_login_authenticates_existing_user(self):
        client = Client()
        email = "existingcitizen@example.com"
        password = "SecurePassword123!"
        User.objects.create_user(email=email, password=password, role=User.Roles.CITIZEN)

        url = reverse("users:password_login")
        response = client.post(
            url,
            data={"email": email, "password": password},
            content_type="application/json"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert int(client.session["_auth_user_id"]) > 0

