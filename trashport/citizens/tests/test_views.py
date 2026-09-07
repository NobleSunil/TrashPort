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

    def test_invoice_view_paid_success(self):
        from decimal import Decimal
        from django.utils import timezone
        from waste_management.models import Address, PickupRequest, WasteCategory
        from trashport.payments.models import PaymentTransaction

        user = User.objects.create_user(email="invoice_user@trashport.local", name="Invoice User", role=User.Roles.CITIZEN)
        addr = Address.objects.create(
            user=user,
            address_line1="777 Green Way",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            latitude=Decimal("12.9716"),
            longitude=Decimal("77.5946"),
        )
        cat = WasteCategory.objects.create(name="Paper & Cardboard", fee_per_kg=Decimal("10.00"), points_per_kg=2)

        pickup = PickupRequest.objects.create(
            citizen=user,
            address=addr,
            category=cat,
            weight_kg=Decimal("15.00"),
            fee=Decimal("150.00"),
            schedule_date=timezone.now(),
        )
        # Mark paid
        PickupRequest.objects.filter(pk=pickup.pk).update(
            is_paid=True,
            status=PickupRequest.StatusChoices.PENDING,
            fee=Decimal("150.00"),
        )
        pickup.refresh_from_db()

        # Create matching PaymentTransaction
        txn = PaymentTransaction.objects.create(
            user=user,
            amount=Decimal("150.00"),
            currency="INR",
            payment_method=PaymentTransaction.PaymentMethods.STRIPE,
            status=PaymentTransaction.Statuses.COMPLETED,
            transaction_id="TXN_TEST_123456",
            description=f"Pickup #{pickup.id} - Paper & Cardboard",
        )

        client = Client()
        client.force_login(user)
        response = client.get(reverse("waste_management:payment_invoice", kwargs={"pk": pickup.id}))
        assert response.status_code == 200
        assert "invoice_number" in response.context
        assert response.context["total_amount"] == Decimal("150.00")
        assert response.context["transaction"] == txn
        content = response.content.decode("utf-8")
        assert "TAX INVOICE" in content
        assert "TXN_TEST_123456" in content
        assert "Paper &amp; Cardboard" in content or "Paper & Cardboard" in content

    def test_invoice_view_unpaid_redirects(self):
        from decimal import Decimal
        from django.utils import timezone
        from waste_management.models import Address, PickupRequest, WasteCategory

        user = User.objects.create_user(email="unpaid_user@trashport.local", name="Unpaid User", role=User.Roles.CITIZEN)
        addr = Address.objects.create(
            user=user,
            address_line1="123 Oak St",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            latitude=Decimal("12.9716"),
            longitude=Decimal("77.5946"),
        )
        cat = WasteCategory.objects.create(name="Plastic", fee_per_kg=Decimal("12.00"), points_per_kg=3)

        pickup = PickupRequest.objects.create(
            citizen=user,
            address=addr,
            category=cat,
            weight_kg=Decimal("10.00"),
            fee=Decimal("120.00"),
            schedule_date=timezone.now(),
        )
        # By default is_paid is False and status is AWAITING_PAYMENT
        client = Client()
        client.force_login(user)
        response = client.get(reverse("waste_management:payment_invoice", kwargs={"pk": pickup.id}))
        # Redirects to checkout
        assert response.status_code == 302
        assert reverse("waste_management:payment_checkout", kwargs={"pk": pickup.id}) in response.url

    def test_invoice_view_forbidden_for_other_citizen(self):
        from decimal import Decimal
        from django.utils import timezone
        from waste_management.models import Address, PickupRequest, WasteCategory

        owner = User.objects.create_user(email="owner@trashport.local", name="Owner User", role=User.Roles.CITIZEN)
        intruder = User.objects.create_user(email="intruder@trashport.local", name="Intruder User", role=User.Roles.CITIZEN)
        addr = Address.objects.create(
            user=owner,
            address_line1="888 Pine St",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            latitude=Decimal("12.9716"),
            longitude=Decimal("77.5946"),
        )
        cat = WasteCategory.objects.create(name="Glass", fee_per_kg=Decimal("8.00"), points_per_kg=1)

        pickup = PickupRequest.objects.create(
            citizen=owner,
            address=addr,
            category=cat,
            weight_kg=Decimal("10.00"),
            fee=Decimal("80.00"),
            schedule_date=timezone.now(),
        )
        PickupRequest.objects.filter(pk=pickup.pk).update(is_paid=True)

        client = Client()
        client.force_login(intruder)
        response = client.get(reverse("waste_management:payment_invoice", kwargs={"pk": pickup.id}))
        assert response.status_code == 403

    def test_citizen_dashboard_includes_invoices_tab(self):
        from decimal import Decimal
        from django.utils import timezone
        from waste_management.models import Address, PickupRequest, WasteCategory

        user = User.objects.create_user(email="cit_dash_inv@trashport.local", name="Dash Inv", role=User.Roles.CITIZEN)
        addr = Address.objects.create(
            user=user,
            address_line1="999 Elm St",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            latitude=Decimal("12.9716"),
            longitude=Decimal("77.5946"),
        )
        cat = WasteCategory.objects.create(name="Metal Scrap", fee_per_kg=Decimal("25.00"), points_per_kg=8)

        pickup = PickupRequest.objects.create(
            citizen=user,
            address=addr,
            category=cat,
            weight_kg=Decimal("5.00"),
            fee=Decimal("125.00"),
            schedule_date=timezone.now(),
        )
        PickupRequest.objects.filter(pk=pickup.pk).update(is_paid=True)

        client = Client()
        client.force_login(user)
        response = client.get(reverse("citizens:dashboard"))
        assert response.status_code == 200
        assert "paid_pickups" in response.context
        assert response.context["invoice_count"] >= 1
        content = response.content.decode("utf-8")
        assert "Invoices &amp; Payments" in content

