from decimal import Decimal
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from trashport.services.payments.models import UPIPayoutRequest
from trashport.core.waste_management.models import Address, PickupRequest, WasteCategory

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestCollectorViews:
    def test_collector_dashboard(self):
        user = User.objects.create_user(
            email="colview@trashport.local",
            name="Col View",
            role=User.Roles.COLLECTOR,
        )
        client = Client()
        client.force_login(user)
        response = client.get(reverse("waste_management:dashboard"))
        assert response.status_code == 200
        assert "Wallet Balance" in response.content.decode()

    def test_unverified_collector_cannot_claim_pickup(self):
        collector = User.objects.create_user(
            email="unverified_col@trashport.local",
            name="Unverified Col",
            role=User.Roles.COLLECTOR,
        )
        assert collector.is_verified is False
        assert collector.verification_status == User.VerificationStatus.PENDING

        citizen = User.objects.create_user(
            email="cit1@trashport.local",
            name="Citizen One",
            role=User.Roles.CITIZEN,
        )
        address = Address.objects.create(
            user=citizen, address_line1="123 Green Way", city="Kochi", state="Kerala", postal_code="682001"
        )
        category = WasteCategory.objects.create(name="Paper", fee_per_kg=Decimal("10.00"), points_per_kg=5)
        pickup = PickupRequest.objects.create(
            citizen=citizen,
            address=address,
            category=category,
            weight_kg=Decimal("5.00"),
            schedule_date=timezone.now(),
        )
        pickup.is_paid = True
        pickup.status = PickupRequest.StatusChoices.PENDING
        pickup.save()

        client = Client()
        client.force_login(collector)
        response = client.post(
            reverse("waste_management:pickup_status_update", kwargs={"pk": pickup.pk}),
            data={"action": "claim"},
            follow=True,
        )
        assert response.status_code == 200
        pickup.refresh_from_db()
        # Still pending, not assigned to unverified collector
        assert pickup.status == PickupRequest.StatusChoices.PENDING
        assert pickup.collector is None

    def test_verified_collector_earnings_formula_35_percent_plus_distance(self):
        collector = User.objects.create_user(
            email="verified_col@trashport.local",
            name="Verified Col",
            role=User.Roles.COLLECTOR,
            is_verified=True,
            verification_status=User.VerificationStatus.APPROVED,
        )
        assert collector.is_verified is True
        initial_wallet = Decimal(str(collector.wallet_balance or "0.00"))

        citizen = User.objects.create_user(
            email="cit2@trashport.local",
            name="Citizen Two",
            role=User.Roles.CITIZEN,
        )
        address = Address.objects.create(
            user=citizen, address_line1="456 Clean St", city="Kochi", state="Kerala", postal_code="682002"
        )
        category = WasteCategory.objects.create(name="Metal", fee_per_kg=Decimal("20.00"), points_per_kg=10)
        pickup = PickupRequest.objects.create(
            citizen=citizen,
            address=address,
            category=category,
            weight_kg=Decimal("10.00"),
            distance_km=Decimal("6.00"),
            schedule_date=timezone.now(),
        )
        pickup.is_paid = True
        pickup.status = PickupRequest.StatusChoices.PENDING
        pickup.save()

        client = Client()
        client.force_login(collector)

        # 1. Claim job
        client.post(
            reverse("waste_management:pickup_status_update", kwargs={"pk": pickup.pk}),
            data={"action": "claim"},
            follow=True,
        )
        pickup.refresh_from_db()
        assert pickup.status == PickupRequest.StatusChoices.ASSIGNED
        assert pickup.collector == collector

        # 2. Start transit
        client.post(
            reverse("waste_management:pickup_status_update", kwargs={"pk": pickup.pk}),
            data={"action": "transit"},
            follow=True,
        )
        pickup.refresh_from_db()
        assert pickup.status == PickupRequest.StatusChoices.IN_TRANSIT

        # 3. Complete job with standard weight (10 kg)
        client.post(
            reverse("waste_management:pickup_status_update", kwargs={"pk": pickup.pk}),
            data={"action": "complete", "actual_weight_kg": "10.00"},
            follow=True,
        )
        pickup.refresh_from_db()
        assert pickup.status == PickupRequest.StatusChoices.COMPLETED
        assert pickup.is_weight_verified is True

        # Fee: 10kg * Rs 20 = Rs 200. Distance: 6km.
        # Earning: Rs 25 min base + (6km * Rs 2.00) = Rs 25.00 + Rs 12.00 = Rs 37.00
        assert pickup.collector_earnings == Decimal("37.00")
        collector.refresh_from_db()
        assert Decimal(str(collector.wallet_balance)) == Decimal("37.00")

    def test_waste_weight_verification_excess_weight_charges_2x_penalty(self):
        collector = User.objects.create_user(
            email="verified_col_excess@trashport.local",
            name="Verified Col Excess",
            role=User.Roles.COLLECTOR,
            is_verified=True,
            verification_status=User.VerificationStatus.APPROVED,
        )
        citizen = User.objects.create_user(
            email="cit_excess@trashport.local",
            name="Citizen Excess",
            role=User.Roles.CITIZEN,
        )
        address = Address.objects.create(
            user=citizen, address_line1="789 Green Rd", city="Kochi", state="Kerala", postal_code="682003"
        )
        category = WasteCategory.objects.create(name="E-Waste", fee_per_kg=Decimal("30.00"), points_per_kg=15)
        pickup = PickupRequest.objects.create(
            citizen=citizen,
            address=address,
            category=category,
            weight_kg=Decimal("10.00"),
            distance_km=Decimal("8.00"),
            schedule_date=timezone.now(),
        )
        pickup.is_paid = True
        pickup.status = PickupRequest.StatusChoices.IN_TRANSIT
        pickup.collector = collector
        pickup.save()

        client = Client()
        client.force_login(collector)

        # Collector measures actual weight on-site: 15 kg (5 kg excess)
        client.post(
            reverse("waste_management:pickup_status_update", kwargs={"pk": pickup.pk}),
            data={"action": "complete", "actual_weight_kg": "15.00"},
            follow=True,
        )
        pickup.refresh_from_db()
        assert pickup.status == PickupRequest.StatusChoices.COMPLETED
        assert pickup.is_weight_verified is True
        assert pickup.actual_weight_kg == Decimal("15.00")

        # Base fee = 10kg * Rs 30 = Rs 300.
        # Excess fee = 5kg * Rs 30 * 2 (2x penalty) = Rs 300.
        # Total final fee = Rs 600.
        assert pickup.extra_fee == Decimal("300.00")
        assert pickup.fee == Decimal("600.00")

        # Collector Earning: Rs 25.00 (min base) + (8km * Rs 2.00 = Rs 16.00) + 20% of extra_fee (Rs 300 * 0.20 = Rs 60.00)
        # Total = 25.00 + 16.00 + 60.00 = Rs 101.00
        assert pickup.collector_earnings == Decimal("101.00")
        collector.refresh_from_db()
        assert Decimal(str(collector.wallet_balance)) == Decimal("101.00")

    def test_collector_can_claim_and_manage_multiple_pickup_jobs(self):
        collector = User.objects.create_user(
            email="multijob_col@trashport.local",
            name="MultiJob Col",
            role=User.Roles.COLLECTOR,
            is_verified=True,
            verification_status=User.VerificationStatus.APPROVED,
        )
        citizen = User.objects.create_user(
            email="multi_citizen@trashport.local",
            name="Multi Citizen",
            role=User.Roles.CITIZEN,
        )
        addr1 = Address.objects.create(user=citizen, address_line1="1st St", city="Kochi", postal_code="682001")
        addr2 = Address.objects.create(user=citizen, address_line1="2nd St", city="Kochi", postal_code="682001")
        cat = WasteCategory.objects.create(name="Paper", fee_per_kg=Decimal("10.00"))

        p1 = PickupRequest.objects.create(citizen=citizen, address=addr1, category=cat, weight_kg=Decimal("5.00"), distance_km=Decimal("3.00"), schedule_date=timezone.now(), is_paid=True, status=PickupRequest.StatusChoices.PENDING)
        p2 = PickupRequest.objects.create(citizen=citizen, address=addr2, category=cat, weight_kg=Decimal("8.00"), distance_km=Decimal("4.00"), schedule_date=timezone.now(), is_paid=True, status=PickupRequest.StatusChoices.PENDING)

        client = Client()
        client.force_login(collector)

        # Claim first job
        res1 = client.post(reverse("waste_management:pickup_status_update", kwargs={"pk": p1.pk}), data={"action": "claim"}, follow=True)
        assert res1.status_code == 200
        p1.refresh_from_db()
        assert p1.collector == collector
        assert p1.status == PickupRequest.StatusChoices.ASSIGNED

        # Claim second job concurrently
        res2 = client.post(reverse("waste_management:pickup_status_update", kwargs={"pk": p2.pk}), data={"action": "claim"}, follow=True)
        assert res2.status_code == 200
        p2.refresh_from_db()
        assert p2.collector == collector
        assert p2.status == PickupRequest.StatusChoices.ASSIGNED

        # Collector has 2 active assigned jobs
        active_count = PickupRequest.objects.filter(collector=collector, status__in=[PickupRequest.StatusChoices.ASSIGNED, PickupRequest.StatusChoices.IN_TRANSIT]).count()
        assert active_count == 2

    def test_collector_redeem_wallet_to_upi_success(self):
        collector = User.objects.create_user(
            email="redeem_col@trashport.local",
            name="Redeem Col",
            role=User.Roles.COLLECTOR,
            is_verified=True,
            verification_status=User.VerificationStatus.APPROVED,
            wallet_balance=Decimal("500.00"),
        )
        client = Client()
        client.force_login(collector)

        response = client.post(
            reverse("waste_management:collector_redeem_upi"),
            data={"upi_id": "testcollector@okaxis", "amount": "300.00"},
            follow=True,
        )
        assert response.status_code == 200
        collector.refresh_from_db()
        # 500 - 300 = 200
        assert collector.wallet_balance == Decimal("200.00")

        payout = UPIPayoutRequest.objects.filter(collector=collector).first()
        assert payout is not None
        assert payout.amount == Decimal("300.00")
        assert payout.upi_id == "testcollector@okaxis"
        assert payout.status == UPIPayoutRequest.Statuses.COMPLETED
        assert payout.transaction_ref.startswith("UPI-")

    def test_collector_redeem_to_upi_insufficient_balance(self):
        collector = User.objects.create_user(
            email="lowbal_col@trashport.local",
            name="Low Bal Col",
            role=User.Roles.COLLECTOR,
            is_verified=True,
            verification_status=User.VerificationStatus.APPROVED,
            wallet_balance=Decimal("50.00"),
        )
        client = Client()
        client.force_login(collector)

        response = client.post(
            reverse("waste_management:collector_redeem_upi"),
            data={"upi_id": "testcollector@okaxis", "amount": "100.00"},
            follow=True,
        )
        assert response.status_code == 200
        collector.refresh_from_db()
        # Balance untouched
        assert collector.wallet_balance == Decimal("50.00")
        assert UPIPayoutRequest.objects.filter(collector=collector).count() == 0
