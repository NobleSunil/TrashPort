from decimal import Decimal
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestAdminViews:
    def test_category_list_view(self):
        admin = User.objects.create_superuser(email="admin_view@trashport.local", password="password")
        client = Client()
        client.force_login(admin)
        response = client.get(reverse("waste_management:category_list"))
        assert response.status_code == 200

    def test_tier_list_view(self):
        admin = User.objects.create_superuser(email="admin_tier@trashport.local", password="password")
        client = Client()
        client.force_login(admin)
        response = client.get(reverse("waste_management:tier_list"))
        assert response.status_code == 200

    def test_admin_approve_collector_verification(self):
        admin = User.objects.create_superuser(email="admin_verify@trashport.local", password="password")
        collector = User.objects.create_user(
            email="pending_col@trashport.local",
            name="Pending Col",
            role=User.Roles.COLLECTOR,
        )
        assert collector.is_verified is False
        assert collector.verification_status == User.VerificationStatus.PENDING

        client = Client()
        client.force_login(admin)
        response = client.post(
            reverse("waste_management:collector_verify", kwargs={"pk": collector.pk}),
            data={"action": "approve"},
            follow=True,
        )
        assert response.status_code == 200
        collector.refresh_from_db()
        assert collector.is_verified is True
        assert collector.verification_status == User.VerificationStatus.APPROVED

    def test_admin_reject_collector_verification(self):
        admin = User.objects.create_superuser(email="admin_reject@trashport.local", password="password")
        collector = User.objects.create_user(
            email="reject_col@trashport.local",
            name="Reject Col",
            role=User.Roles.COLLECTOR,
        )
        client = Client()
        client.force_login(admin)
        response = client.post(
            reverse("waste_management:collector_verify", kwargs={"pk": collector.pk}),
            data={"action": "reject"},
            follow=True,
        )
        assert response.status_code == 200
        collector.refresh_from_db()
        assert collector.is_verified is False
        assert collector.verification_status == User.VerificationStatus.REJECTED

    def test_admin_adjust_collector_cash_wallet(self):
        admin = User.objects.create_superuser(email="admin_cash@trashport.local", password="password")
        collector = User.objects.create_user(
            email="col_cash@trashport.local",
            name="Col Cash",
            role=User.Roles.COLLECTOR,
            wallet_balance=Decimal("100.00"),
        )
        client = Client()
        client.force_login(admin)
        response = client.post(
            reverse("waste_management:user_wallet_adjust", kwargs={"pk": collector.pk}),
            data={"cash_amount": "250.50"},
            follow=True,
        )
        assert response.status_code == 200
        collector.refresh_from_db()
        assert collector.wallet_balance == Decimal("350.50")

    def test_admin_operations_report_view_access(self):
        admin = User.objects.create_superuser(email="admin_rep@trashport.local", password="password")
        citizen = User.objects.create_user(email="citizen_rep@trashport.local", password="password", role=User.Roles.CITIZEN)
        client = Client()

        # Unauthenticated redirects to login
        resp = client.get(reverse("waste_management:operations_report"))
        assert resp.status_code == 302

        # Citizen gets 403 Forbidden
        client.force_login(citizen)
        resp = client.get(reverse("waste_management:operations_report"))
        assert resp.status_code == 403

        # Admin gets 200 OK
        client.force_login(admin)
        resp = client.get(reverse("waste_management:operations_report"))
        assert resp.status_code == 200
        assert "date_range_display" in resp.context
        assert "trend_labels_json" in resp.context
        assert "cat_labels_json" in resp.context
        assert "status_labels_json" in resp.context

    def test_admin_operations_report_filtering_and_graphs(self):
        from django.utils import timezone
        from waste_management.models import Address, PickupRequest, WasteCategory

        admin = User.objects.create_superuser(email="admin_rep2@trashport.local", password="password")
        citizen = User.objects.create_user(email="cit_data@trashport.local", password="password", role=User.Roles.CITIZEN)
        addr = Address.objects.create(user=citizen, address_line1="123 Main St", city="Bangalore", state="Karnataka", postal_code="560001", latitude=Decimal("12.9716"), longitude=Decimal("77.5946"))
        category = WasteCategory.objects.create(name="Plastics", fee_per_kg=Decimal("15.00"), points_per_kg=5)

        today = timezone.localdate()
        # Create a pickup for today
        p1 = PickupRequest.objects.create(
            citizen=citizen,
            address=addr,
            category=category,
            weight_kg=Decimal("20.00"),
            fee=Decimal("300.00"),
            collector_earnings=Decimal("110.00"),
            schedule_date=timezone.now(),
        )
        PickupRequest.objects.filter(pk=p1.pk).update(
            status=PickupRequest.StatusChoices.COMPLETED,
            is_paid=True,
            fee=Decimal("300.00"),
            weight_kg=Decimal("20.00"),
            collector_earnings=Decimal("110.00"),
        )

        client = Client()
        client.force_login(admin)

        # Test preset duration: today
        resp = client.get(reverse("waste_management:operations_report"), {"duration": "today"})
        assert resp.status_code == 200
        assert resp.context["total_pickups"] >= 1
        assert resp.context["completed_pickups"] >= 1
        assert resp.context["total_revenue"] >= 300.00
        assert resp.context["total_weight_kg"] >= 20.00

        # Test custom duration: start_date and end_date
        s_date = (today - timezone.timedelta(days=1)).strftime("%Y-%m-%d")
        e_date = today.strftime("%Y-%m-%d")
        resp = client.get(reverse("waste_management:operations_report"), {"start_date": s_date, "end_date": e_date})
        assert resp.status_code == 200
        assert resp.context["duration"] == "custom"
        assert resp.context["total_pickups"] >= 1

    def test_admin_export_csv_filtered_by_date(self):
        from django.utils import timezone
        from waste_management.models import Address, PickupRequest, WasteCategory

        admin = User.objects.create_superuser(email="admin_csv@trashport.local", password="password")
        citizen = User.objects.create_user(email="cit_csv@trashport.local", password="password", role=User.Roles.CITIZEN)
        addr = Address.objects.create(user=citizen, address_line1="456 High St", city="Bangalore", state="Karnataka", postal_code="560002", latitude=Decimal("12.9716"), longitude=Decimal("77.5946"))
        category = WasteCategory.objects.create(name="E-Waste", fee_per_kg=Decimal("50.00"), points_per_kg=10)

        PickupRequest.objects.create(
            citizen=citizen,
            address=addr,
            category=category,
            weight_kg=Decimal("5.00"),
            fee=Decimal("250.00"),
            status=PickupRequest.StatusChoices.COMPLETED,
            is_paid=True,
            schedule_date=timezone.now(),
        )

        client = Client()
        client.force_login(admin)

        today = timezone.localdate()
        s_date = today.strftime("%Y-%m-%d")
        e_date = today.strftime("%Y-%m-%d")

        # Pickups CSV
        resp = client.get(reverse("waste_management:export_pickups_csv"), {"start_date": s_date, "end_date": e_date})
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/csv"
        content = resp.content.decode("utf-8")
        assert "E-Waste" in content
        assert "250" in content

        # Revenue CSV
        resp_rev = client.get(reverse("waste_management:export_revenue_csv"), {"start_date": s_date, "end_date": e_date})
        assert resp_rev.status_code == 200
        assert resp_rev["Content-Type"] == "text/csv"
        content_rev = resp_rev.content.decode("utf-8")
        assert "E-Waste" in content_rev

