import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from waste_management.models import (
    Address, WasteCategory, PickupRequest
)

User = get_user_model()

pytestmark = pytest.mark.django_db

def test_pickup_calculations_and_status_transitions():
    # 1. Setup users, category, and address
    citizen = User.objects.create_user(
        email="citizen@example.com",
        password="password123",
        role=User.Roles.CITIZEN,
        wallet_points=0
    )
    collector = User.objects.create_user(
        email="collector@example.com",
        password="password123",
        role=User.Roles.COLLECTOR
    )
    address = Address.objects.create(
        user=citizen,
        address_line1="123 Main St",
        city="Kochi",
        state="Kerala",
        postal_code="682001",
        is_default=True
    )
    category = WasteCategory.objects.create(
        name="Metals",
        description="Copper, Aluminum, Steel",
        fee_per_kg=2.50,
        points_per_kg=10
    )
    
    # 2. Test unsubscribed booking
    pickup = PickupRequest.objects.create(
        citizen=citizen,
        address=address,
        category=category,
        weight_kg=6.00,
        schedule_date=timezone.now()
    )
    
    # Fee should be 6 * 2.50 = 15.00
    assert pickup.fee == 15.00
    # Points should be 6 * 10 = 60
    assert pickup.points_earned == 60
    # Status should be AWAITING_PAYMENT
    assert pickup.status == PickupRequest.StatusChoices.AWAITING_PAYMENT
    assert not pickup.is_paid
    
    # 3. Test pay action
    pickup.is_paid = True
    pickup.status = PickupRequest.StatusChoices.PENDING
    pickup.save()
    
    # Refetch
    pickup.refresh_from_db()
    assert pickup.is_paid
    assert pickup.status == PickupRequest.StatusChoices.PENDING
    
    # 4. Test collector transit and completion
    pickup.collector = collector
    pickup.status = PickupRequest.StatusChoices.ASSIGNED
    pickup.save()
    
    # Transit
    pickup.status = PickupRequest.StatusChoices.IN_TRANSIT
    pickup.save()
    
    # Complete
    pickup.status = PickupRequest.StatusChoices.COMPLETED
    pickup.save()
    
    # Citizen should receive reward points in their wallet
    citizen.refresh_from_db()
    assert citizen.wallet_points == 60


def test_pickup_standard_fee_calculation():
    citizen = User.objects.create_user(
        email="subcitizen@example.com",
        password="password123",
        role=User.Roles.CITIZEN
    )
    address = Address.objects.create(
        user=citizen,
        address_line1="456 Sub Rd",
        city="Kochi",
        state="Kerala",
        postal_code="682001",
        is_default=True
    )
    category = WasteCategory.objects.create(
        name="Plastics",
        description="Plastic waste",
        fee_per_kg=1.50,
        points_per_kg=2
    )
    
    pickup = PickupRequest.objects.create(
        citizen=citizen,
        address=address,
        category=category,
        weight_kg=10.00,
        schedule_date=timezone.now()
    )
    
    assert pickup.fee == 15.00
    assert pickup.points_earned == 20
    assert pickup.status == PickupRequest.StatusChoices.AWAITING_PAYMENT
    assert not pickup.is_paid


def test_admin_dashboard_view_analytics_and_filtering(client):
    admin = User.objects.create_user(
        email="admin@trashport.org",
        password="Password123!",
        role=User.Roles.ADMIN,
        is_staff=True,
        is_superuser=True
    )
    client.force_login(admin)

    # Access dashboard endpoint
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert "total_revenue" in response.context
    assert "cat_labels_json" in response.context
    assert "status_counts_json" in response.context

    # Test filtering by status and search query
    response_filter = client.get("/dashboard/?status=PENDING&q=Kochi")
    assert response_filter.status_code == 200
    assert response_filter.context["selected_status"] == "PENDING"
    assert response_filter.context["search_query"] == "Kochi"


def test_admin_user_management_and_collector_creation(client):
    admin = User.objects.create_user(
        email="admin_user_mgr@trashport.org",
        password="Password123!",
        role=User.Roles.ADMIN,
        is_staff=True,
        is_superuser=True
    )
    client.force_login(admin)

    # 1. User Directory View
    res = client.get("/manage/users/")
    assert res.status_code == 200

    # 2. Register Collector
    post_res = client.post("/manage/users/collectors/new/", {
        "email": "new_collector@trashport.org",
        "name": "New Collector Staff",
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert post_res.status_code == 302
    created_col = User.objects.get(email="new_collector@trashport.org")
    assert created_col.role == User.Roles.COLLECTOR

    # 3. Toggle Active status
    toggle_res = client.post(f"/manage/users/{created_col.id}/toggle/")
    assert toggle_res.status_code == 302
    created_col.refresh_from_db()
    assert not created_col.is_active


def test_admin_auto_assign_pickups_and_wallet_adjustment(client):
    admin = User.objects.create_user(
        email="admin_auto@trashport.org",
        password="Password123!",
        role=User.Roles.ADMIN,
        is_staff=True,
        is_superuser=True
    )
    citizen = User.objects.create_user(
        email="cit_auto@trashport.org",
        password="Password123!",
        role=User.Roles.CITIZEN,
        wallet_points=10
    )
    collector = User.objects.create_user(
        email="col_auto@trashport.org",
        password="Password123!",
        role=User.Roles.COLLECTOR,
        is_active=True
    )
    address = Address.objects.create(
        user=citizen,
        address_line1="500 Park Ave",
        city="Kochi",
        state="Kerala",
        postal_code="682001"
    )
    category = WasteCategory.objects.create(
        name="Glass & Bottles",
        fee_per_kg=1.0,
        points_per_kg=5
    )
    pickup = PickupRequest.objects.create(
        citizen=citizen,
        address=address,
        category=category,
        weight_kg=4.0,
        schedule_date=timezone.now(),
        is_paid=True,
        status=PickupRequest.StatusChoices.PENDING
    )
    pickup.is_paid = True
    pickup.status = PickupRequest.StatusChoices.PENDING
    pickup.save()


    client.force_login(admin)

    # 1. Auto-assign pending pickups
    assign_res = client.post("/manage/pickups/auto-assign/")
    assert assign_res.status_code == 302
    pickup.refresh_from_db()
    assert pickup.collector == collector
    assert pickup.status == PickupRequest.StatusChoices.ASSIGNED

    # 2. Adjust Wallet Points
    wallet_res = client.post(f"/manage/users/{citizen.id}/wallet/", {
        "points": 50,
        "reason": "Recycling Contest Winner"
    })
    assert wallet_res.status_code == 302
    citizen.refresh_from_db()
    assert citizen.wallet_points == 60


def test_admin_csv_exports(client):
    admin = User.objects.create_user(
        email="admin_csv@trashport.org",
        password="Password123!",
        role=User.Roles.ADMIN,
        is_staff=True,
        is_superuser=True
    )
    client.force_login(admin)

    res_pickups = client.get("/manage/export/pickups/")
    assert res_pickups.status_code == 200
    assert res_pickups["Content-Type"] == "text/csv"

    res_revenue = client.get("/manage/export/revenue/")
    assert res_revenue.status_code == 200
    assert res_revenue["Content-Type"] == "text/csv"



