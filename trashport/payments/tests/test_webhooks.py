import json
from decimal import Decimal
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from trashport.payments.services import StripePaymentService
from trashport.payments.models import PaymentTransaction

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestStripeWebhook:
    def test_webhook_succeeded_event(self):
        user = User.objects.create_user(email="hookuser@trashport.local", name="Hook User")
        res = StripePaymentService.create_payment_intent(user=user, amount=Decimal("15.00"))
        txn_id = res["transaction_id"]

        client = Client()
        url = reverse("payments:stripe_webhook")
        payload = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": txn_id
                }
            }
        }
        response = client.post(url, data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        txn = PaymentTransaction.objects.get(transaction_id=txn_id)
        assert txn.status == PaymentTransaction.Statuses.COMPLETED
