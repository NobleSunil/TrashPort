from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from trashport.payments.services import StripePaymentService, WalletService
from trashport.payments.models import PaymentTransaction

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestPaymentServices:
    def test_create_payment_intent(self):
        user = User.objects.create_user(email="paytest@trashport.local", name="Pay Test")
        res = StripePaymentService.create_payment_intent(
            user=user,
            amount=Decimal("49.99"),
            currency="USD",
            description="Premium Tier Subscription"
        )
        assert "transaction_id" in res
        assert res["amount"] == 49.99
        txn = PaymentTransaction.objects.get(transaction_id=res["transaction_id"])
        assert txn.status == PaymentTransaction.Statuses.PENDING

    def test_complete_payment(self):
        user = User.objects.create_user(email="paycomplete@trashport.local", name="Pay Complete")
        res = StripePaymentService.create_payment_intent(user=user, amount=Decimal("20.00"))
        txn = StripePaymentService.complete_payment(res["transaction_id"])
        assert txn.status == PaymentTransaction.Statuses.COMPLETED

    def test_wallet_adjust_points(self):
        user = User.objects.create_user(email="walletuser@trashport.local", name="Wallet User")
        record = WalletService.adjust_points(user, 100, "Recycling bonus")
        assert record.balance_after == 100
        user.refresh_from_db()
        assert user.wallet_points == 100
