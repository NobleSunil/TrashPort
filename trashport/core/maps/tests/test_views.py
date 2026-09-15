import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from trashport.core.maps.models import ServiceZone, CollectorLocation

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestMapsViews:
    def test_service_zones_list(self):
        ServiceZone.objects.create(name="Zone North", code="ZN01")
        client = APIClient()
        url = reverse("maps:zones")
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_update_collector_location(self):
        collector = User.objects.create_user(
            email="collmap@trashport.local",
            name="Collector Map",
            role=User.Roles.COLLECTOR
        )
        client = APIClient()
        client.force_authenticate(user=collector)

        url = reverse("maps:update_location")
        response = client.post(url, {
            "latitude": "12.971600",
            "longitude": "77.594600",
            "speed": 25.5,
            "heading": 90.0,
        }, format="json")

        assert response.status_code == 200
        assert CollectorLocation.objects.filter(collector=collector).exists()
