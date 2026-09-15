import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from trashport.core.waste_management.models import Address, WasteCategory, PickupRequest
from trashport.services.dispatch.algorithms import (
    NearestCollectorDispatch,
    LeastBusyCollectorDispatch,
    ZoneBasedDispatch,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestDispatchAlgorithms:
    @pytest.fixture
    def setup_data(self):
        citizen = User.objects.create_user(email="disp_cit@trashport.local", name="Disp Citizen")
        collector1 = User.objects.create_user(
            email="coll1@trashport.local",
            name="Collector One",
            role=User.Roles.COLLECTOR
        )
        collector2 = User.objects.create_user(
            email="coll2@trashport.local",
            name="Collector Two",
            role=User.Roles.COLLECTOR
        )
        cat = WasteCategory.objects.create(name="Plastic", fee_per_kg=1.5)
        addr = Address.objects.create(
            user=citizen,
            address_line1="123 Main St",
            city="City",
            state="Karnataka",
            postal_code="12345"
        )

        pickup1 = PickupRequest.objects.create(
            citizen=citizen,
            address=addr,
            category=cat,
            schedule_date=timezone.now(),
            status="PENDING",
            weight_kg=10
        )

        pickup2 = PickupRequest.objects.create(
            citizen=citizen,
            address=addr,
            category=cat,
            schedule_date=timezone.now(),
            status="PENDING",
            weight_kg=20
        )

        return {
            "collectors": [collector1, collector2],
            "pickups": [pickup1, pickup2],
        }

    def test_nearest_dispatch(self, setup_data):
        assigned, unassigned = NearestCollectorDispatch.assign_pickups(
            setup_data["pickups"],
            setup_data["collectors"]
        )
        assert len(assigned) == 2
        assert assigned[0][0].collector is not None

    def test_least_busy_dispatch(self, setup_data):
        assigned, unassigned = LeastBusyCollectorDispatch.assign_pickups(
            setup_data["pickups"],
            setup_data["collectors"]
        )
        assert len(assigned) == 2

    def test_zone_based_dispatch(self, setup_data):
        assigned, unassigned = ZoneBasedDispatch.assign_pickups(
            setup_data["pickups"],
            setup_data["collectors"]
        )
        assert len(assigned) == 2
