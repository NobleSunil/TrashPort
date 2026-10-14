"""
trashport/tests/test_admin_hub_and_user_deletion.py — Tests for Map-Based Hub Operations & User Deletion
========================================================================================================

PURPOSE:
  Validates administrator capabilities and security controls:
  1. Map-based hub registration with query parameter pre-population (lat, lng, address, city).
  2. Role authorization barriers preventing non-admins from creating hubs or deleting users.
  3. Permanent user deletion by administrator with operational safeguards:
     - Prevention of self-deletion.
     - Privilege guard preventing non-superusers from deleting superusers.
     - Blocking deletion when active in-progress pickups exist (collector or citizen).
     - Clean detachment of deleted collectors from fleet vehicles.
"""

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from trashport.core.waste_management.models import Address
from trashport.core.waste_management.models import City
from trashport.core.waste_management.models import Hub
from trashport.core.waste_management.models import PickupRequest
from trashport.core.waste_management.models import Vehicle
from trashport.core.waste_management.models import WasteCategory
from trashport.users.models import User


@pytest.fixture
def test_setup(db):
    """Initializes admin, superuser, collector, and citizen test accounts."""
    admin = User.objects.create_user(
        email="admin@trashport.org",
        name="Admin Operations",
        password="password123",
        role=User.Roles.ADMIN,
        is_staff=True,
    )

    superuser = User.objects.create_superuser(
        email="super@trashport.org",
        name="Super Admin",
        password="password123",
        role=User.Roles.ADMIN,
    )

    collector = User.objects.create_user(
        email="collector@trashport.org",
        name="Collector Mohan",
        password="password123",
        role=User.Roles.COLLECTOR,
        is_verified=True,
        verification_status=User.VerificationStatus.APPROVED,
    )

    citizen = User.objects.create_user(
        email="citizen@trashport.org",
        name="Citizen Anjali",
        password="password123",
        role=User.Roles.CITIZEN,
    )

    city = City.objects.create(name="Kochi", state="Kerala", is_active=True)

    hub = Hub.objects.create(
        name="Kochi North Hub",
        city=city,
        latitude=Decimal("9.931200"),
        longitude=Decimal("76.267300"),
        address="Kaloor Metro Station, Kochi",
        is_active=True,
    )

    category = WasteCategory.objects.create(
        name="Household Recyclables",
        fee_per_kg=Decimal("15.00"),
        points_per_kg=5,
    )

    return {
        "admin": admin,
        "superuser": superuser,
        "collector": collector,
        "citizen": citizen,
        "city": city,
        "hub": hub,
        "category": category,
    }


@pytest.mark.django_db
class TestAdminHubMapOperations:
    """Test suite for interactive map-based hub creation and view permissions."""

    def test_hub_create_view_prefills_from_map_query_params(self, test_setup):
        """Verify GET query params from map click pre-populate latitude, longitude, and address."""
        client = Client()
        client.force_login(test_setup["admin"])

        url = reverse("waste_management:hub_create")
        params = {
            "lat": "9.981234",
            "lng": "76.289123",
            "address": "Marine Drive, Kochi",
            "city": test_setup["city"].id,
        }
        response = client.get(url, params)
        assert response.status_code == 200
        form = response.context["form"]
        assert Decimal(str(form.initial["latitude"])) == Decimal("9.981234")
        assert Decimal(str(form.initial["longitude"])) == Decimal("76.289123")
        assert form.initial["address"] == "Marine Drive, Kochi"
        assert form.initial["city"] == test_setup["city"].id

    def test_admin_can_create_hub_successfully(self, test_setup):
        """Verify Admin can submit new hub with coordinates selected from map."""
        client = Client()
        client.force_login(test_setup["admin"])

        url = reverse("waste_management:hub_create")
        payload = {
            "name": "Kakkanad Smart Hub",
            "city": test_setup["city"].id,
            "latitude": "10.015860",
            "longitude": "76.341860",
            "address": "Infopark Road, Kakkanad",
            "is_active": True,
        }
        response = client.post(url, data=payload)
        assert response.status_code == 302
        assert Hub.objects.filter(name="Kakkanad Smart Hub").exists()
        new_hub = Hub.objects.get(name="Kakkanad Smart Hub")
        assert new_hub.latitude == Decimal("10.015860")
        assert new_hub.longitude == Decimal("76.341860")

    def test_non_admin_cannot_access_hub_create(self, test_setup):
        """Verify Citizen is blocked from accessing the hub creation form."""
        client = Client()
        client.force_login(test_setup["citizen"])

        url = reverse("waste_management:hub_create")
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse("waste_management:dashboard")

    def test_hub_list_contains_serialized_hubs_for_map(self, test_setup):
        """Verify hub_list view context provides serialized hubs_json for the interactive network map."""
        client = Client()
        client.force_login(test_setup["admin"])

        url = reverse("waste_management:hub_list")
        response = client.get(url)
        assert response.status_code == 200
        assert "hubs_json" in response.context
        assert "Kochi North Hub" in response.context["hubs_json"]

    def test_operations_report_template_renders_curly_braces_cleanly(self, test_setup):
        """Verify Operations Report renders date range and admin email without literal curly braces."""
        client = Client()
        client.force_login(test_setup["admin"])

        url = reverse("waste_management:operations_report")
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        # Must not contain un-evaluated literal template tags
        assert "{{ date_range_display" not in content
        assert "{{ request.user.email" not in content
        assert "admin@trashport.org" in content

    def test_admin_dashboard_renders_reports_dropdown_with_hover_wrapper(self, test_setup):
        """Verify Admin Dashboard renders the Reports & Exports button with hover-responsive container."""
        client = Client()
        client.force_login(test_setup["admin"])

        url = reverse("waste_management:dashboard")
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "reports-dropdown-wrapper" in content
        assert "Reports &amp; Exports" in content or "Reports & Exports" in content


@pytest.mark.django_db
class TestAdminUserDeletion:
    """Test suite for Admin user deletion with security and operational validation checks."""

    def test_admin_can_delete_citizen_without_active_pickups(self, test_setup):
        """Verify Admin can permanently delete a citizen account."""
        client = Client()
        client.force_login(test_setup["admin"])

        citizen_id = test_setup["citizen"].id
        url = reverse("waste_management:user_delete", kwargs={"pk": citizen_id})
        response = client.post(url)
        assert response.status_code == 302
        assert not User.objects.filter(id=citizen_id).exists()

    def test_admin_can_delete_collector_and_unassigns_vehicle(self, test_setup):
        """Verify Admin can delete a collector, releasing vehicle driver assignment."""
        collector = test_setup["collector"]
        vehicle = Vehicle.objects.create(
            vehicle_number="KL-07-TP-9999",
            hub=test_setup["hub"],
            driver=collector,
            max_capacity=5,
            status=Vehicle.StatusChoices.ASSIGNED,
        )

        client = Client()
        client.force_login(test_setup["admin"])

        url = reverse("waste_management:user_delete", kwargs={"pk": collector.id})
        response = client.post(url)
        assert response.status_code == 302
        assert not User.objects.filter(id=collector.id).exists()

        # Vehicle must remain intact with driver set to None and status Available
        vehicle.refresh_from_db()
        assert vehicle.driver is None
        assert vehicle.status == Vehicle.StatusChoices.AVAILABLE

    def test_admin_cannot_delete_own_account(self, test_setup):
        """Verify security guard prevents admin from deleting their own active session."""
        admin = test_setup["admin"]
        client = Client()
        client.force_login(admin)

        url = reverse("waste_management:user_delete", kwargs={"pk": admin.id})
        response = client.post(url)
        assert response.status_code == 302
        assert User.objects.filter(id=admin.id).exists()

    def test_non_superuser_cannot_delete_superuser(self, test_setup):
        """Verify privilege escalation prevention: staff admin cannot delete superuser."""
        superuser = test_setup["superuser"]
        client = Client()
        client.force_login(test_setup["admin"])

        url = reverse("waste_management:user_delete", kwargs={"pk": superuser.id})
        response = client.post(url)
        assert response.status_code == 302
        assert User.objects.filter(id=superuser.id).exists()

    def test_cannot_delete_collector_with_active_in_progress_pickups(self, test_setup):
        """Verify operational check blocks deleting a collector currently assigned to a pickup."""
        collector = test_setup["collector"]
        citizen = test_setup["citizen"]

        address = Address.objects.create(
            user=citizen,
            address_line1="Marine Drive Walkway",
            city="Kochi",
            state="Kerala",
            postal_code="682011",
            latitude=Decimal("9.932000"),
            longitude=Decimal("76.268000"),
        )

        # Create pickup actively assigned to collector
        pickup = PickupRequest.objects.create(
            citizen=citizen,
            collector=collector,
            category=test_setup["category"],
            hub=test_setup["hub"],
            city=test_setup["city"],
            schedule_date=timezone.now(),
            latitude=Decimal("9.932000"),
            longitude=Decimal("76.268000"),
            address=address,
        )
        PickupRequest.objects.filter(id=pickup.id).update(status=PickupRequest.StatusChoices.ASSIGNED)

        client = Client()
        client.force_login(test_setup["admin"])

        url = reverse("waste_management:user_delete", kwargs={"pk": collector.id})
        response = client.post(url)
        assert response.status_code == 302
        # Collector must NOT be deleted while servicing active pickup
        assert User.objects.filter(id=collector.id).exists()

    def test_cannot_delete_citizen_with_active_in_progress_pickups(self, test_setup):
        """Verify operational check blocks deleting a citizen while their pickup is on the way."""
        collector = test_setup["collector"]
        citizen = test_setup["citizen"]

        address = Address.objects.create(
            user=citizen,
            address_line1="Marine Drive Walkway",
            city="Kochi",
            state="Kerala",
            postal_code="682011",
            latitude=Decimal("9.932000"),
            longitude=Decimal("76.268000"),
        )

        pickup = PickupRequest.objects.create(
            citizen=citizen,
            collector=collector,
            category=test_setup["category"],
            hub=test_setup["hub"],
            city=test_setup["city"],
            schedule_date=timezone.now(),
            latitude=Decimal("9.932000"),
            longitude=Decimal("76.268000"),
            address=address,
        )
        PickupRequest.objects.filter(id=pickup.id).update(status=PickupRequest.StatusChoices.IN_TRANSIT)

        client = Client()
        client.force_login(test_setup["admin"])

        url = reverse("waste_management:user_delete", kwargs={"pk": citizen.id})
        response = client.post(url)
        assert response.status_code == 302
        # Citizen must NOT be deleted while pickup is in transit
        assert User.objects.filter(id=citizen.id).exists()

    def test_non_admin_cannot_delete_user(self, test_setup):
        """Verify RoleDispatchView returns 403 Forbidden when a citizen attempts to delete a user."""
        client = Client()
        client.force_login(test_setup["citizen"])

        url = reverse("waste_management:user_delete", kwargs={"pk": test_setup["collector"].id})
        response = client.post(url)
        assert response.status_code == 403
        assert User.objects.filter(id=test_setup["collector"].id).exists()
