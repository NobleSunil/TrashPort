from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from waste_management.models import Address, WasteCategory, PickupRequest

User = get_user_model()

class PayPerPickupTestCase(TestCase):
    def setUp(self):
        # Create users
        self.citizen = User.objects.create_user(
            email="citizen@example.com",
            password="password123",
            role=User.Roles.CITIZEN,
            name="Test Citizen"
        )
        self.collector = User.objects.create_user(
            email="collector@example.com",
            password="password123",
            role=User.Roles.COLLECTOR,
            name="Test Collector"
        )
        # Create Address
        self.address = Address.objects.create(
            user=self.citizen,
            address_line1="123 Street",
            city="Kochi",
            state="Kerala",
            postal_code="682001",
            is_default=True
        )
        # Create WasteCategory with price_per_kg
        self.category = WasteCategory.objects.create(
            name="Organic",
            price_per_kg=Decimal("0.50"),
            description="Organic waste"
        )
        # Create PickupRequest
        self.pickup = PickupRequest.objects.create(
            citizen=self.citizen,
            address=self.address,
            category=self.category,
            quantity_estimate="Around 5kg",
            schedule_date=timezone.now()
        )

    def test_initial_values(self):
        # Check initial values are set correctly
        self.assertEqual(self.pickup.status, PickupRequest.StatusChoices.PENDING)
        self.assertEqual(self.pickup.payment_status, PickupRequest.PaymentStatus.UNPAID)
        self.assertIsNone(self.pickup.weight)
        self.assertEqual(self.pickup.cost, Decimal("0.00"))

    def test_complete_pickup_cost_calculation(self):
        # Simulate collector completing collection with weight
        self.pickup.collector = self.collector
        self.pickup.status = PickupRequest.StatusChoices.IN_TRANSIT
        self.pickup.save()

        # Collector completes collection with 10.5 kg
        weight = Decimal("10.5")
        self.pickup.weight = weight
        self.pickup.cost = weight * self.pickup.category.price_per_kg
        self.pickup.status = PickupRequest.StatusChoices.COMPLETED
        self.pickup.save()

        self.assertEqual(self.pickup.weight, Decimal("10.5"))
        self.assertEqual(self.pickup.cost, Decimal("5.25"))
        self.assertEqual(self.pickup.status, PickupRequest.StatusChoices.COMPLETED)
        self.assertEqual(self.pickup.payment_status, PickupRequest.PaymentStatus.UNPAID)

    def test_payment(self):
        # Simulate citizen payment
        self.pickup.payment_status = PickupRequest.PaymentStatus.PAID
        self.pickup.save()
        self.assertEqual(self.pickup.payment_status, PickupRequest.PaymentStatus.PAID)
