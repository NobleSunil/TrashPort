import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestCitizenViews:
    def test_dashboard_view(self):
        user = User.objects.create_user(email="citview@trashport.local", name="Cit View")
        client = Client()
        client.force_login(user)
        response = client.get(reverse("citizens:dashboard"))
        assert response.status_code == 200

    def test_address_list_view(self):
        user = User.objects.create_user(email="addrview@trashport.local", name="Addr View")
        client = Client()
        client.force_login(user)
        response = client.get(reverse("citizens:address_list"))
        assert response.status_code == 200
