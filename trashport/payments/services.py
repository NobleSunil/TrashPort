import logging
import uuid
from decimal import Decimal
from django.db import transaction
from .models import PaymentTransaction, WalletHistory

logger = logging.getLogger(__name__)


class StripePaymentService:
    @staticmethod
    def create_payment_intent(user, amount: Decimal, currency: str = "USD", description: str = ""):
        """Simulates or connects to Stripe PaymentIntent creation."""
        txn_id = f"pi_mock_{uuid.uuid4().hex[:16]}"
        txn = PaymentTransaction.objects.create(
            user=user,
            amount=amount,
            currency=currency,
            payment_method=PaymentTransaction.PaymentMethods.STRIPE,
            status=PaymentTransaction.Statuses.PENDING,
            transaction_id=txn_id,
            description=description,
        )
        return {
            "client_secret": f"{txn_id}_secret_{uuid.uuid4().hex[:8]}",
            "transaction_id": txn_id,
            "amount": float(amount),
            "currency": currency,
        }

    @staticmethod
    def complete_payment(transaction_id: str):
        txn = PaymentTransaction.objects.filter(transaction_id=transaction_id).first()
        if txn and txn.status != PaymentTransaction.Statuses.COMPLETED:
            txn.status = PaymentTransaction.Statuses.COMPLETED
            txn.save()
            logger.info(f"Payment transaction {transaction_id} marked as COMPLETED.")
            return txn
        return txn


class WalletService:
    @staticmethod
    @transaction.atomic
    def adjust_points(user, points_delta: int, reason: str):
        """Safely credits or debits points from user wallet with transaction logging."""
        current_points = getattr(user, "wallet_points", 0)
        new_balance = max(0, current_points + points_delta)
        user.wallet_points = new_balance
        user.save(update_fields=["wallet_points"])

        record = WalletHistory.objects.create(
            user=user,
            points_delta=points_delta,
            balance_after=new_balance,
            reason=reason,
        )
        return record
