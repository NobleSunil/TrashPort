import pytest
from decimal import Decimal
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from trashport.users.forms import UserSignupForm
from trashport.users.models import User
from trashport.core.waste_management.models import (
    City,
    Hub,
    PickupRequest,
    Address,
    WasteCategory,
)
from trashport.core.maps.models import CollectorLocation
from trashport.collectors.views import (
    CollectorDashboardView,
    CollectorPickupStatusUpdateView,
)


from django.utils import timezone

@pytest.fixture
def base_hub_setup(db):
    """Set up base cities and hubs for range testing."""
    kochi_city = City.objects.create(name="Kochi", state="Kerala", is_active=True)
    kochi_hub = Hub.objects.create(
        name="Kochi Central Hub",
        city=kochi_city,
        latitude=Decimal("9.931200"),
        longitude=Decimal("76.267300"),
        address="Marine Drive, Kochi",
        is_active=True,
    )

    kumarakom_city = City.objects.create(name="Kumarakom Grama Panchayat", state="Kerala", is_active=True)
    kumarakom_hub = Hub.objects.create(
        name="Kumarakom Backwater Hub",
        city=kumarakom_city,
        latitude=Decimal("9.617500"),
        longitude=Decimal("76.430100"),
        address="Boat Jetty Road, Kumarakom",
        is_active=True,
    )

    category = WasteCategory.objects.create(
        name="Dry Recyclable Waste",
        fee_per_kg=Decimal("10.00"),
        points_per_kg=5,
    )

    citizen = User.objects.create_user(
        email="citizen_tester@example.com",
        name="Citizen Tester",
        password="password123",
        role=User.Roles.CITIZEN,
    )

    collector = User.objects.create_user(
        email="collector_tester@example.com",
        name="Collector Tester",
        password="password123",
        role=User.Roles.COLLECTOR,
        is_verified=True,
        verification_status=User.VerificationStatus.APPROVED,
    )
    collector.hub = kochi_hub
    collector.save()

    return {
        "kochi_city": kochi_city,
        "kochi_hub": kochi_hub,
        "kumarakom_city": kumarakom_city,
        "kumarakom_hub": kumarakom_hub,
        "category": category,
        "citizen": citizen,
        "collector": collector,
    }


@pytest.mark.django_db
class TestCollectorHubSignupRequirement:
    """Test collector hub specification requirements during registration."""

    def test_collector_signup_requires_hub(self, base_hub_setup):
        """Collectors must specify an operating hub upon signup."""
        form_data = {
            "name": "New Collector",
            "email": "new_collector@example.com",
            "role": User.Roles.COLLECTOR,
            "hub": "",  # Missing hub
        }
        form = UserSignupForm(data=form_data)
        assert not form.is_valid()
        assert "hub" in form.errors
        assert "Collectors must specify their operating Hub / Panchayath." in form.errors["hub"]

    def test_collector_signup_with_valid_hub(self, base_hub_setup):
        """Collectors with a valid hub have no hub validation errors."""
        form_data = {
            "name": "Valid Collector",
            "email": "valid_collector@example.com",
            "role": User.Roles.COLLECTOR,
            "hub": base_hub_setup["kochi_hub"].id,
        }
        form = UserSignupForm(data=form_data)
        form.is_valid()
        assert "hub" not in form.errors

    def test_citizen_signup_does_not_require_hub(self, base_hub_setup):
        """Citizens do not need to specify an operating hub."""
        form_data = {
            "name": "Citizen Without Hub",
            "email": "citizen_nohub@example.com",
            "role": User.Roles.CITIZEN,
            "hub": "",
        }
        form = UserSignupForm(data=form_data)
        form.is_valid()
        assert "hub" not in form.errors


@pytest.mark.django_db
class TestCollector25KmRangeFiltering:
    """Test strict 25 km radius enforcement for collectors."""

    def test_dashboard_unassigned_pickups_strictly_filtered_to_25km(self, base_hub_setup):
        """Pickups beyond 25 km must be excluded from collector opportunity listings."""
        collector = base_hub_setup["collector"]
        citizen = base_hub_setup["citizen"]
        category = base_hub_setup["category"]

        # 1. Nearby pickup in Kumbalangi (~6.5 km from Kochi Hub)
        addr_nearby = Address.objects.create(
            user=citizen,
            address_line1="Kumbalangi Eco Village",
            city="Kochi",
            postal_code="682007",
            latitude=Decimal("9.874400"),
            longitude=Decimal("76.284700"),
        )
        pickup_nearby = PickupRequest.objects.create(
            citizen=citizen,
            category=category,
            address=addr_nearby,
            weight_kg=Decimal("15.00"),
            schedule_date=timezone.now(),
            status=PickupRequest.StatusChoices.PENDING,
        )

        # 2. Distant pickup in Kumarakom (~38 km from Kochi Hub)
        addr_far = Address.objects.create(
            user=citizen,
            address_line1="Kumarakom Boat Jetty",
            city="Kumarakom Grama Panchayat",
            postal_code="686563",
            latitude=Decimal("9.617500"),
            longitude=Decimal("76.430100"),
        )
        pickup_far = PickupRequest.objects.create(
            citizen=citizen,
            category=category,
            address=addr_far,
            weight_kg=Decimal("20.00"),
            schedule_date=timezone.now(),
            status=PickupRequest.StatusChoices.PENDING,
        )

        # Fetch unassigned pickups for collector (currently anchored at Kochi Hub)
        unassigned_pickups, _, _, _ = CollectorDashboardView()._get_unassigned_pickup_data(collector)
        pickup_ids = [p.id for p in unassigned_pickups]

        assert pickup_nearby.id in pickup_ids
        assert pickup_far.id not in pickup_ids

        # Ensure all listed pickups are <= 25.0 km
        for p in unassigned_pickups:
            assert p.calculated_distance_km <= 25.0

    def test_live_gps_overrides_static_hub_for_range(self, base_hub_setup):
        """When live GPS is transmitted, pickup distance and range adapt to current GPS position."""
        collector = base_hub_setup["collector"]
        citizen = base_hub_setup["citizen"]
        category = base_hub_setup["category"]

        # Pickup in Kumarakom (~38 km from Kochi, but ~0 km from Kumarakom GPS)
        addr_kumarakom = Address.objects.create(
            user=citizen,
            address_line1="Kumarakom Center",
            city="Kumarakom Grama Panchayat",
            postal_code="686563",
            latitude=Decimal("9.617500"),
            longitude=Decimal("76.430100"),
        )
        pickup_kumarakom = PickupRequest.objects.create(
            citizen=citizen,
            category=category,
            address=addr_kumarakom,
            weight_kg=Decimal("10.00"),
            schedule_date=timezone.now(),
            status=PickupRequest.StatusChoices.PENDING,
        )

        # Before live GPS: Collector at Kochi Hub, so Kumarakom pickup is > 25 km and not visible
        initial_pickups, _, _, _ = CollectorDashboardView()._get_unassigned_pickup_data(collector)
        assert pickup_kumarakom.id not in [p.id for p in initial_pickups]

        # Simulate collector transmitting live GPS near Kumarakom
        CollectorLocation.objects.update_or_create(
            collector=collector,
            defaults={
                "latitude": Decimal("9.618000"),
                "longitude": Decimal("76.431000"),
            },
        )

        # After live GPS: Kumarakom pickup is < 1 km away and strictly within 25 km
        updated_pickups, _, _, _ = CollectorDashboardView()._get_unassigned_pickup_data(collector)
        updated_ids = [p.id for p in updated_pickups]
        assert pickup_kumarakom.id in updated_ids

        kumarakom_data = next(p for p in updated_pickups if p.id == pickup_kumarakom.id)
        assert kumarakom_data.calculated_distance_km < 1.0

    def test_cannot_claim_pickup_exceeding_25km(self, base_hub_setup):
        """Collector cannot claim a pickup that exceeds 25 km."""
        collector = base_hub_setup["collector"]
        citizen = base_hub_setup["citizen"]
        category = base_hub_setup["category"]

        # Pickup 38 km away in Kumarakom
        addr_far = Address.objects.create(
            user=citizen,
            address_line1="Kumarakom Lake",
            city="Kumarakom Grama Panchayat",
            postal_code="686563",
            latitude=Decimal("9.617500"),
            longitude=Decimal("76.430100"),
        )
        pickup_far = PickupRequest.objects.create(
            citizen=citizen,
            category=category,
            address=addr_far,
            weight_kg=Decimal("20.00"),
            schedule_date=timezone.now(),
            status=PickupRequest.StatusChoices.PENDING,
        )
        pickup_far.status = PickupRequest.StatusChoices.PENDING
        pickup_far.is_paid = True
        pickup_far.save()

        client = Client()
        client.force_login(collector)

        response = client.post(
            reverse("waste_management:pickup_status_update", kwargs={"pk": pickup_far.id}),
            data={"action": "claim"},
            follow=True,
        )

        # Status update should be rejected because distance (38 km) > 25 km
        pickup_far.refresh_from_db()
        assert pickup_far.status == PickupRequest.StatusChoices.PENDING
        assert pickup_far.collector is None

    def test_can_claim_pickup_within_25km(self, base_hub_setup):
        """Collector can claim a pickup within 25 km."""
        collector = base_hub_setup["collector"]
        citizen = base_hub_setup["citizen"]
        category = base_hub_setup["category"]

        # Pickup in Kumbalangi (~6.5 km away from Kochi Hub)
        addr_near = Address.objects.create(
            user=citizen,
            address_line1="Kumbalangi Village",
            city="Kochi",
            postal_code="682007",
            latitude=Decimal("9.874400"),
            longitude=Decimal("76.284700"),
        )
        pickup_near = PickupRequest.objects.create(
            citizen=citizen,
            category=category,
            address=addr_near,
            weight_kg=Decimal("15.00"),
            schedule_date=timezone.now(),
            status=PickupRequest.StatusChoices.PENDING,
        )
        pickup_near.status = PickupRequest.StatusChoices.PENDING
        pickup_near.is_paid = True
        pickup_near.save()

        client = Client()
        client.force_login(collector)

        response = client.post(
            reverse("waste_management:pickup_status_update", kwargs={"pk": pickup_near.id}),
            data={"action": "claim"},
            follow=True,
        )

        pickup_near.refresh_from_db()
        assert pickup_near.status == PickupRequest.StatusChoices.ASSIGNED
        assert pickup_near.collector == collector


@pytest.mark.django_db
class TestLiveLocationHubAlignment:
    """Test live location API updates nearest hub and CollectorLocation."""

    def test_live_location_api_updates_hub_within_range(self, base_hub_setup):
        """Posting live location near a new hub updates collector's operating hub."""
        collector = base_hub_setup["collector"]
        assert collector.hub == base_hub_setup["kochi_hub"]

        client = APIClient()
        client.force_authenticate(user=collector)

        # Move collector to Kumarakom Hub (lat: 9.617500, lng: 76.430100)
        response = client.post(
            "/api/maps/locations/update/",
            data={
                "latitude": 9.617500,
                "longitude": 76.430100,
                "speed": 10.5,
                "heading": 90.0,
            },
            format="json",
        )
        assert response.status_code == 200

        # Verify CollectorLocation record
        loc = CollectorLocation.objects.get(collector=collector)
        assert float(loc.latitude) == pytest.approx(9.617500, rel=1e-5)
        assert float(loc.longitude) == pytest.approx(76.430100, rel=1e-5)

        # Verify collector's hub dynamically updated to Kumarakom Hub
        collector = User.objects.get(pk=collector.pk)
        assert collector.hub == base_hub_setup["kumarakom_hub"]


@pytest.mark.django_db
class TestSeedCitiesAndHubsCommand:
    """Test seed_cities_and_hubs management command."""

    def test_seed_cities_and_hubs_creates_panchayaths(self):
        """Verifies operational hubs and vehicles seeded across Kerala districts."""
        call_command("seed_cities_and_hubs")

        # Check key panchayaths and hubs exist
        expected_panchayaths = [
            "Kumarakom Grama Panchayat",
            "Venganoor Grama Panchayat",
            "Mayyanad Grama Panchayat",
            "Kozhencherry Grama Panchayat",
            "Mararikulam Grama Panchayat",
            "Munnar Grama Panchayat",
            "Mulavukad Grama Panchayat",
            "Cherpu Grama Panchayat",
            "Malampuzha Grama Panchayat",
            "Kondotty Grama Panchayat",
            "Kunnamangalam Grama Panchayat",
            "Meppadi Grama Panchayat",
            "Dharmadam Grama Panchayat",
            "Udma Grama Panchayat",
        ]

        for p_name in expected_panchayaths:
            assert City.objects.filter(name=p_name).exists(), f"City/Panchayath '{p_name}' not found"

        # Check that hubs are active and have vehicles
        hubs_count = Hub.objects.filter(is_active=True).count()
        assert hubs_count >= 20

        kumarakom_hub = Hub.objects.get(name="Kumarakom Backwater Hub")
        assert kumarakom_hub.city.name == "Kumarakom Grama Panchayat"
        assert kumarakom_hub.vehicles.count() >= 1
