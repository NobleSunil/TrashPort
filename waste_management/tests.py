import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from waste_management.models import (
    Address, SubscriptionTier, Subscription, WasteCategory, PickupRequest
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


def test_subscribed_pickup_fee_calculation():
    # 1. Setup users, category, subscription tier, and address
    citizen = User.objects.create_user(
        email="citizen_sub@example.com",
        password="password123",
        role=User.Roles.CITIZEN,
        wallet_points=0
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
    
    # Setup active subscription
    tier = SubscriptionTier.objects.create(
        name="Premium Plan",
        price=20.00,
        is_active=True
    )
    Subscription.objects.create(
        user=citizen,
        tier=tier,
        start_date=timezone.now().date(),
        is_active=True
    )
    
    # 2. Book pickup
    pickup = PickupRequest.objects.create(
        citizen=citizen,
        address=address,
        category=category,
        weight_kg=10.00,
        schedule_date=timezone.now()
    )
    
    # Subscribed user: fee should be 0
    assert pickup.fee == 0.00
    assert pickup.points_earned == 20
    # Status should be PENDING immediately, since no payment is needed
    assert pickup.status == PickupRequest.StatusChoices.PENDING
    assert pickup.is_paid
