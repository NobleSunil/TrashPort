import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from trashport.users.models import User
from trashport.core.waste_management.models import (
    City,
    Hub,
    Vehicle,
    Route,
    RoutePickup,
    PickupRequest,
    Address,
    WasteCategory,
)
from trashport.core.waste_management.services import RouteService


@pytest.fixture
def db_setup(db):
    """Set up base testing fixtures: citizen, collectors, waste category, and test cities."""
    citizen = User.objects.create_user(
        email="citizen@example.com",
        name="Citizen User",
        password="password123",
        role=User.Roles.CITIZEN,
    )

    collector1 = User.objects.create_user(
        email="collector1@example.com",
        name="Collector One",
        password="password123",
        role=User.Roles.COLLECTOR,
        is_verified=True,
        verification_status=User.VerificationStatus.APPROVED,
    )

    collector2 = User.objects.create_user(
        email="collector2@example.com",
        name="Collector Two",
        password="password123",
        role=User.Roles.COLLECTOR,
        is_verified=True,
        verification_status=User.VerificationStatus.APPROVED,
    )

    category = WasteCategory.objects.create(
        name="Dry Recyclable Waste",
        fee_per_kg=Decimal("10.00"),
        points_per_kg=5,
    )

    # City 1: Kochi - Has Hub AND Active Collector
    kochi = City.objects.create(name="Kochi", state="Kerala", is_active=True)
    kochi_hub = Hub.objects.create(
        name="Kochi Central Hub",
        city=kochi,
        latitude=Decimal("9.931233"),
        longitude=Decimal("76.267304"),
        is_active=True,
    )
    # Assign collector1 to kochi_hub
    collector1.hub = kochi_hub
    collector1.save()

    # City 2: Kozhikode - Has Hub BUT NO registered collectors (coming soon test)
    kozhikode = City.objects.create(name="Kozhikode", state="Kerala", is_active=True)
    kozhikode_hub = Hub.objects.create(
        name="Kozhikode North Hub",
        city=kozhikode,
        latitude=Decimal("11.258753"),
        longitude=Decimal("75.780410"),
        is_active=True,
    )

    # City 3: Munnar - Active City BUT NO active hub registered
    munnar = City.objects.create(name="Munnar", state="Kerala", is_active=True)

    # Fleet Vehicle for Kochi
    vehicle = Vehicle.objects.create(
        vehicle_number="KL-07-TP-1001",
        hub=kochi_hub,
        driver=collector1,
        max_capacity=5,
        status=Vehicle.StatusChoices.AVAILABLE,
    )

    return {
        "citizen": citizen,
        "collector1": collector1,
        "collector2": collector2,
        "category": category,
        "kochi": kochi,
        "kochi_hub": kochi_hub,
        "kozhikode": kozhikode,
        "kozhikode_hub": kozhikode_hub,
        "munnar": munnar,
        "vehicle": vehicle,
    }


@pytest.mark.django_db
class TestCityAndHubRules:
    def test_city_without_active_hub_rejected(self, db_setup):
        """Rule 1: City with no active hub registered must be rejected with exact error message."""
        munnar = db_setup["munnar"]
        with pytest.raises(ValidationError) as exc_info:
            RouteService.validate_pickup_eligibility(
                city=munnar,
                latitude=10.0889,
                longitude=77.0595,
            )
        assert "Pickup service is currently unavailable in this city because no active hub is registered." in str(exc_info.value)

    def test_city_with_hub_but_no_collectors_rejected_with_coming_soon(self, db_setup):
        """Rule 2: City with hub but no active collectors registered must be rejected with 'available soon' message."""
        kozhikode = db_setup["kozhikode"]
        assert kozhikode.active_hub is not None
        assert kozhikode.has_active_collectors is False

        with pytest.raises(ValidationError) as exc_info:
            RouteService.validate_pickup_eligibility(
                city=kozhikode,
                latitude=11.2588,
                longitude=75.7805,
            )
        assert "Pickup service is currently unavailable in your city. It will be available soon as collectors are registered in this area." in str(exc_info.value)

    def test_city_with_collectors_outside_20km_radius_rejected(self, db_setup):
        """Rule 3: Location farther than 20 km from nearest active hub must be rejected with exact error message."""
        kochi = db_setup["kochi"]
        assert kochi.has_active_collectors is True

        # Coordinates ~35 km from Kochi hub (near Alappuzha border)
        far_lat = 9.600000
        far_lng = 76.350000

        with pytest.raises(ValidationError) as exc_info:
            RouteService.validate_pickup_eligibility(
                city=kochi,
                latitude=far_lat,
                longitude=far_lng,
            )
        assert "Pickup service is unavailable at this location. The pickup address is outside the 20 km service area of the nearest active hub." in str(exc_info.value)

    def test_city_with_collectors_within_20km_radius_accepted(self, db_setup):
        """Rule 4: Location within 20 km from active hub with registered collectors must be accepted."""
        kochi = db_setup["kochi"]
        # Marine Drive Kochi (~3 km from Hub at 9.9312, 76.2673)
        marine_drive_lat = 9.9785
        marine_drive_lng = 76.2755

        eligible, hub, distance_km = RouteService.validate_pickup_eligibility(
            city=kochi,
            latitude=marine_drive_lat,
            longitude=marine_drive_lng,
        )
        assert eligible is True
        assert hub == db_setup["kochi_hub"]
        assert distance_km < 20.0


@pytest.mark.django_db
class TestVehicleCapacityAndRoutes:
    def test_maximum_5_pickups_capacity_enforced(self, db_setup):
        """Rule 5: Vehicle capacity limit of 5 pickups per trip strictly enforced. 6th pickup rejected."""
        kochi_hub = db_setup["kochi_hub"]
        vehicle = db_setup["vehicle"]
        citizen = db_setup["citizen"]
        category = db_setup["category"]

        # Create route starting and ending at Kochi Hub
        route = Route.objects.create(
            vehicle=vehicle,
            hub=kochi_hub,
            status=Route.StatusChoices.PLANNED,
        )

        # Create 6 pickup requests within 20 km of Kochi Hub
        pickups = []
        for i in range(6):
            addr = Address.objects.create(
                user=citizen,
                address_line1=f"Stop #{i+1} MG Road",
                city="Kochi",
                latitude=Decimal(str(9.9350 + (i * 0.005))),
                longitude=Decimal(str(76.2680 + (i * 0.005))),
            )
            p = PickupRequest.objects.create(
                citizen=citizen,
                address=addr,
                city=db_setup["kochi"],
                hub=kochi_hub,
                latitude=addr.latitude,
                longitude=addr.longitude,
                category=category,
                weight_kg=Decimal("10.00"),
                fee=Decimal("100.00"),
                schedule_date=timezone.now() + timedelta(days=1),
                status=PickupRequest.StatusChoices.PENDING,
            )
            pickups.append(p)

        # Assign 1 to 5 pickups successfully
        for i in range(5):
            rp = RouteService.assign_pickup_to_route(route.id, pickups[i].id)
            assert rp.sequence == i + 1
            pickups[i].refresh_from_db()
            assert pickups[i].status == PickupRequest.StatusChoices.ASSIGNED

        route.refresh_from_db()
        assert route.route_pickups.count() == 5

        # 6th pickup MUST be rejected with exact capacity message
        with pytest.raises(ValidationError) as exc_info:
            RouteService.assign_pickup_to_route(route.id, pickups[5].id)
        assert "This vehicle has reached its maximum capacity of 5 pickups." in str(exc_info.value)

        # The 6th pickup can be placed on HELD
        held_p = RouteService.hold_pickup_request(pickups[5].id, "Capacity exceeded")
        assert held_p.status == PickupRequest.StatusChoices.HELD

    def test_route_waypoints_start_and_end_at_hub(self, db_setup):
        """Rule 6: Collection route waypoints must start at Hub and end at Hub."""
        kochi_hub = db_setup["kochi_hub"]
        vehicle = db_setup["vehicle"]
        citizen = db_setup["citizen"]
        category = db_setup["category"]

        route = Route.objects.create(
            vehicle=vehicle,
            hub=kochi_hub,
            status=Route.StatusChoices.PLANNED,
        )

        addr1 = Address.objects.create(
            user=citizen,
            address_line1="Palarivattom",
            city="Kochi",
            latitude=Decimal("10.0021"),
            longitude=Decimal("76.3075"),
        )
        p1 = PickupRequest.objects.create(
            citizen=citizen,
            address=addr1,
            city=db_setup["kochi"],
            hub=kochi_hub,
            latitude=addr1.latitude,
            longitude=addr1.longitude,
            category=category,
            weight_kg=Decimal("15.00"),
            fee=Decimal("150.00"),
            schedule_date=timezone.now() + timedelta(days=1),
            status=PickupRequest.StatusChoices.PENDING,
        )

        RouteService.assign_pickup_to_route(route.id, p1.id)

        waypoints = route.get_waypoints()
        assert len(waypoints) == 3  # Origin Hub, Stop 1, Terminus Hub
        hub_coords = (float(kochi_hub.latitude), float(kochi_hub.longitude))
        # Origin is Hub
        assert waypoints[0] == hub_coords
        # Stop 1 is p1 coordinates
        assert waypoints[1] == (float(p1.effective_latitude), float(p1.effective_longitude))
        # Terminus is Hub
        assert waypoints[2] == hub_coords

        # Distance calculation
        total_dist = route.calculate_total_distance()
        assert total_dist > 0


@pytest.mark.django_db
class TestRestApiEndpoints:
    def test_city_service_status_endpoint(self, db_setup):
        """REST API /api/cities/{id}/service-status/ accurately returns hub & collector state."""
        client = APIClient()
        kochi = db_setup["kochi"]
        kozhikode = db_setup["kozhikode"]

        # Kochi: Hub=True, Collectors=True
        resp_kochi = client.get(f"/api/cities/{kochi.id}/service-status/")
        assert resp_kochi.status_code == 200
        assert resp_kochi.data["has_active_hub"] is True
        assert resp_kochi.data["has_active_collectors"] is True

        # Kozhikode: Hub=True, Collectors=False
        resp_koz = client.get(f"/api/cities/{kozhikode.id}/service-status/")
        assert resp_koz.status_code == 200
        assert resp_koz.data["has_active_hub"] is True
        assert resp_koz.data["has_active_collectors"] is False

    def test_pickup_request_api_validates_20km_rule(self, db_setup):
        """Creating a pickup via API validates the 20 km rule."""
        client = APIClient()
        citizen = db_setup["citizen"]
        category = db_setup["category"]
        kochi = db_setup["kochi"]
        client.force_authenticate(user=citizen)

        addr = Address.objects.create(
            user=citizen,
            address_line1="Faraway Point",
            city="Kochi",
            latitude=Decimal("9.5000"),
            longitude=Decimal("76.3500"),
        )

        schedule_time = (timezone.now() + timedelta(days=2)).isoformat()
        payload = {
            "citizen": citizen.id,
            "city": kochi.id,
            "address": addr.id,
            "latitude": "9.5000",
            "longitude": "76.3500",
            "category": category.id,
            "weight_kg": "12.00",
            "schedule_date": schedule_time,
        }

        resp = client.post("/api/pickup-requests/", data=payload)
        assert resp.status_code == 400
        resp_text = str(resp.data)
        assert "outside the 20 km service area" in resp_text
