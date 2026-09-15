from decimal import Decimal
import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from trashport.services.payments.models import PaymentTransaction

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestPaymentViews:
    def test_create_intent_view(self):
        user = User.objects.create_user(email="intentuser@trashport.local", name="Intent User")
        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("payments:create_intent")
        response = client.post(url, {
            "amount": "25.00",
            "currency": "USD",
            "description": "Monthly pickup package"
        }, format="json")

        assert response.status_code == 201
        data = response.json()
        assert "transaction_id" in data
        assert data["amount"] == 25.00

    def test_payment_history_view(self):
        user = User.objects.create_user(email="histuser@trashport.local", name="History User")
        PaymentTransaction.objects.create(
            user=user,
            amount=Decimal("30.00"),
            currency="USD",
            status=PaymentTransaction.Statuses.COMPLETED,
            transaction_id="pi_12345"
        )

        client = APIClient()
        client.force_authenticate(user=user)
        url = reverse("payments:payment_history")
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.json()) == 1
