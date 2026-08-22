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
