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

    def test_pickup_schedule_validation_operating_hours_and_3h_advance(self):
        from datetime import timedelta
        from decimal import Decimal
        from django.utils import timezone
        from waste_management.models import Address, WasteCategory
        from trashport.citizens.forms import PickupRequestForm

        user = User.objects.create_user(email="timeval_cit@trashport.local", name="TimeVal Cit", role=User.Roles.CITIZEN)
        addr = Address.objects.create(user=user, address_line1="123 Test St", city="Kochi", postal_code="682001")
        cat = WasteCategory.objects.create(name="Plastic", fee_per_kg=Decimal("10.00"))

        now_local = timezone.localtime(timezone.now())

        # 1. Reject if less than 3 hours in advance
        too_early = now_local + timedelta(hours=1)
        form_early = PickupRequestForm(data={
            "address": addr.id,
            "category": cat.id,
            "weight_kg": "5.0",
            "schedule_date": too_early.strftime("%Y-%m-%dT%H:%M"),
        }, user=user)
        assert not form_early.is_valid()
        assert "at least 3 hours in advance" in str(form_early.errors["schedule_date"])

        # 2. Reject if scheduled at 5:00 AM (before 7:00 AM)
        early_morning = (now_local + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
        form_morning = PickupRequestForm(data={
            "address": addr.id,
            "category": cat.id,
            "weight_kg": "5.0",
            "schedule_date": early_morning.strftime("%Y-%m-%dT%H:%M"),
        }, user=user)
        assert not form_morning.is_valid()
        assert "7:00 AM and 8:30 PM" in str(form_morning.errors["schedule_date"])

        # 3. Reject if scheduled at 9:00 PM (21:00) (after 8:30 PM)
        late_night = (now_local + timedelta(days=1)).replace(hour=21, minute=0, second=0, microsecond=0)
        form_night = PickupRequestForm(data={
            "address": addr.id,
            "category": cat.id,
            "weight_kg": "5.0",
            "schedule_date": late_night.strftime("%Y-%m-%dT%H:%M"),
        }, user=user)
        assert not form_night.is_valid()
        assert "7:00 AM and 8:30 PM" in str(form_night.errors["schedule_date"])

        # 4. Accept if within 7:00 AM - 8:30 PM and at least 3 hours in advance (e.g. tomorrow at 10:00 AM)
        valid_time = (now_local + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        form_valid = PickupRequestForm(data={
            "address": addr.id,
            "category": cat.id,
            "weight_kg": "5.0",
            "schedule_date": valid_time.strftime("%Y-%m-%dT%H:%M"),
        }, user=user)
        assert form_valid.is_valid()

    def test_weight_limit_up_to_100kg_and_admin_custom(self):
        from datetime import timedelta
        from decimal import Decimal
        from django.utils import timezone
        from waste_management.models import Address, WasteCategory
        from trashport.citizens.forms import PickupRequestForm

        user = User.objects.create_user(email="wt_cit@trashport.local", name="Weight Cit", role=User.Roles.CITIZEN)
        addr = Address.objects.create(user=user, address_line1="45 Weight Way", city="Kochi", postal_code="682001")
        # Category with custom admin weight limit 50 kg
        cat_50 = WasteCategory.objects.create(name="E-Waste Capped", fee_per_kg=Decimal("15.00"), max_weight_kg=Decimal("50.00"))
        # Category with standard 100 kg limit
        cat_100 = WasteCategory.objects.create(name="Standard Waste", fee_per_kg=Decimal("5.00"), max_weight_kg=Decimal("100.00"))

        valid_time = (timezone.localtime(timezone.now()) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")

        # 1. Weight > 100 kg is rejected by default
        f1 = PickupRequestForm(data={"address": addr.id, "category": cat_100.id, "weight_kg": "105.0", "schedule_date": valid_time}, user=user)
        assert not f1.is_valid()
        assert "100 kg" in str(f1.errors.get("weight_kg"))

        # 2. Weight > custom admin limit (50 kg) is rejected
        f2 = PickupRequestForm(data={"address": addr.id, "category": cat_50.id, "weight_kg": "65.0", "schedule_date": valid_time}, user=user)
        assert not f2.is_valid()
        assert "50" in str(f2.errors.get("weight_kg"))

        # 3. Weight within custom admin limit (40 kg) is valid
        f3 = PickupRequestForm(data={"address": addr.id, "category": cat_50.id, "weight_kg": "40.0", "schedule_date": valid_time}, user=user)
        assert f3.is_valid()

        # 4. Weight exactly 100 kg for 100 kg limit category is valid
        f4 = PickupRequestForm(data={"address": addr.id, "category": cat_100.id, "weight_kg": "100.0", "schedule_date": valid_time}, user=user)
        assert f4.is_valid()

    def test_payment_checkout_mandatory_details(self):
        from decimal import Decimal
        from django.utils import timezone
        from waste_management.models import Address, PickupRequest, WasteCategory

        user = User.objects.create_user(email="pay_mand_cit@trashport.local", name="Pay Mand Cit", role=User.Roles.CITIZEN)
        addr = Address.objects.create(user=user, address_line1="12 Payment Rd", city="Kochi", postal_code="682001")
        cat = WasteCategory.objects.create(name="General Waste", fee_per_kg=Decimal("10.00"), max_weight_kg=Decimal("100.00"))
        pickup = PickupRequest.objects.create(
            citizen=user,
            address=addr,
            category=cat,
            weight_kg=Decimal("5.00"),
            fee=Decimal("50.00"),
            schedule_date=timezone.now() + timezone.timedelta(days=1),
            status=PickupRequest.StatusChoices.AWAITING_PAYMENT,
        )

        client = Client()
        client.force_login(user)

        checkout_url = reverse("waste_management:payment_checkout", kwargs={"pk": pickup.id})

        # 1. Submitting card payment with missing fields is rejected
        res_card_empty = client.post(checkout_url, {
            "payment_method": "card",
            "card_number": "",
            "card_name": "",
            "expiry": "",
            "cvv": "",
        })
        assert res_card_empty.status_code == 200
        assert "All card details" in res_card_empty.content.decode("utf-8")
        pickup.refresh_from_db()
        assert not pickup.is_paid

        # 2. Submitting UPI payment with missing UPI ID is rejected
        res_upi_empty = client.post(checkout_url, {
            "payment_method": "upi",
            "upi_id": "",
        })
        assert res_upi_empty.status_code == 200
        assert "UPI ID is mandatory" in res_upi_empty.content.decode("utf-8")
        pickup.refresh_from_db()
        assert not pickup.is_paid

        # 3. Submitting valid UPI payment succeeds
        res_upi_valid = client.post(checkout_url, {
            "payment_method": "upi",
            "upi_id": "citizen@okaxis",
        })
        assert res_upi_valid.status_code == 302
        pickup.refresh_from_db()
        assert pickup.is_paid
        assert pickup.status == PickupRequest.StatusChoices.PENDING

    def test_pickup_cancellation_reason_and_assignment_lock(self):
        from decimal import Decimal
        from django.utils import timezone
        from waste_management.models import Address, PickupRequest, WasteCategory

        user = User.objects.create_user(email="cancel_cit@trashport.local", name="Cancel Cit", role=User.Roles.CITIZEN)
        collector = User.objects.create_user(email="cancel_col@trashport.local", name="Cancel Col", role=User.Roles.COLLECTOR)
        addr = Address.objects.create(user=user, address_line1="99 Cancel Way", city="Kochi", postal_code="682001")
        cat = WasteCategory.objects.create(name="Paper Waste", fee_per_kg=Decimal("8.00"))

        client = Client()
        client.force_login(user)

        # 1. Reject cancellation without a reason
        pickup_unassigned = PickupRequest.objects.create(
            citizen=user,
            address=addr,
            category=cat,
            weight_kg=Decimal("10.00"),
            fee=Decimal("80.00"),
            schedule_date=timezone.now() + timezone.timedelta(days=1),
            status=PickupRequest.StatusChoices.PENDING,
        )
        url1 = reverse("waste_management:pickup_status_update", kwargs={"pk": pickup_unassigned.id})
        res1 = client.post(url1, {"action": "cancel", "cancellation_reason": ""}, follow=True)
        assert res1.status_code == 200
        pickup_unassigned.refresh_from_db()
        assert pickup_unassigned.status == PickupRequest.StatusChoices.AWAITING_PAYMENT

        # 2. Successfully cancel unassigned pickup with reason (unpaid)
        res2 = client.post(url1, {"action": "cancel", "cancellation_reason": "Change of plans"}, follow=True)
        assert res2.status_code == 200
        pickup_unassigned.refresh_from_db()
        assert pickup_unassigned.status == PickupRequest.StatusChoices.CANCELLED
        assert pickup_unassigned.cancellation_reason == "Change of plans"
        assert pickup_unassigned.cancelled_at is not None

        # 3. Cannot cancel if collector is already assigned or status is ASSIGNED
        pickup_assigned = PickupRequest.objects.create(
            citizen=user,
            collector=collector,
            address=addr,
            category=cat,
            weight_kg=Decimal("10.00"),
            fee=Decimal("80.00"),
            schedule_date=timezone.now() + timezone.timedelta(days=1),
        )
        PickupRequest.objects.filter(pk=pickup_assigned.pk).update(status=PickupRequest.StatusChoices.ASSIGNED)
        pickup_assigned.refresh_from_db()

        url2 = reverse("waste_management:pickup_status_update", kwargs={"pk": pickup_assigned.id})
        res3 = client.post(url2, {"action": "cancel", "cancellation_reason": "Need to cancel"}, follow=True)
        assert res3.status_code == 200
        pickup_assigned.refresh_from_db()
        assert pickup_assigned.status == PickupRequest.StatusChoices.ASSIGNED
        content3 = res3.content.decode("utf-8")
        assert "cannot be cancelled because a collector has already been assigned" in content3

        # 4. Cancelling a paid pickup confirms 3 to 7 business days refund
        pickup_paid = PickupRequest.objects.create(
            citizen=user,
            address=addr,
            category=cat,
            weight_kg=Decimal("10.00"),
            fee=Decimal("80.00"),
            schedule_date=timezone.now() + timezone.timedelta(days=1),
        )
        PickupRequest.objects.filter(pk=pickup_paid.pk).update(is_paid=True, status=PickupRequest.StatusChoices.PENDING)
        pickup_paid.refresh_from_db()
        url3 = reverse("waste_management:pickup_status_update", kwargs={"pk": pickup_paid.id})
        res4 = client.post(url3, {"action": "cancel", "cancellation_reason": "Wrong location"}, follow=True)
        assert res4.status_code == 200
        pickup_paid.refresh_from_db()
        assert pickup_paid.status == PickupRequest.StatusChoices.CANCELLED
        content4 = res4.content.decode("utf-8")
        assert "3 to 7 business days" in content4

        # 5. History tab includes both completed and cancelled pickups
        dash_res = client.get(reverse("citizens:dashboard"))
        assert dash_res.status_code == 200
        assert "history_pickups" in dash_res.context
        assert dash_res.context["cancelled_count"] >= 2




