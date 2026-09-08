import logging
import uuid
from decimal import Decimal
from django.db import transaction as db_transaction
from .models import PaymentTransaction, WalletHistory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dummy Gateway — Test Card Catalog
# Each entry maps a sanitized card number to a (success, decline_code) tuple.
# ---------------------------------------------------------------------------
DUMMY_CARDS = {
    "4242424242424242": (True, None),          # Visa — always succeeds
    "5555555555554444": (True, None),          # Mastercard — always succeeds
    "4000000000000002": (False, "card_declined"),
    "4000000000009995": (False, "insufficient_funds"),
    "4000000000000069": (False, "expired_card"),
    "4000000000000127": (False, "incorrect_cvc"),
}

# Points to INR conversion rate: 100 points = Rs. 10 (1 point = Rs. 0.10)
POINTS_TO_INR_RATE = Decimal("0.10")


class StripePaymentService:
    @staticmethod
    def create_payment_intent(user, amount: Decimal, currency: str = "USD", description: str = ""):
        """Simulates or connects to Stripe PaymentIntent creation."""
        txn_id = f"pi_mock_{uuid.uuid4().hex[:16]}"
        PaymentTransaction.objects.create(
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
    @db_transaction.atomic
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


# ---------------------------------------------------------------------------
# Dummy Payment Gateway Service
# ---------------------------------------------------------------------------

_DECLINE_MESSAGES = {
    "card_declined": "Your card was declined. Please try a different card.",
    "insufficient_funds": "Insufficient funds. Please use a different payment method.",
    "expired_card": "Your card has expired. Please check the expiry date and try again.",
    "incorrect_cvc": "The CVC code is incorrect. Please check and try again.",
}


class PaymentGatewayService:
    """
    Simulates a realistic payment gateway for TrashPort.

    Supports three payment methods:
      - CARD  : Validates card details against the dummy card catalog.
      - UPI   : Accepts any syntactically valid UPI ID (user@bank pattern).
      - WALLET: Redeems recycling wallet points at Rs. 0.01 / point.

    On success:
      - Creates a COMPLETED PaymentTransaction record.
      - Sets pickup.is_paid = True and transitions status to PENDING.

    On failure:
      - Creates a FAILED PaymentTransaction for audit purposes.
      - Returns a human-readable decline reason.
    """

    @staticmethod
    @db_transaction.atomic
    def process_card_payment(user, pickup, card_number: str, card_name: str,
                             expiry: str, cvv: str):
        """Process a card payment against the dummy card catalog."""
        sanitized = card_number.replace(" ", "").replace("-", "")
        success, decline_code = DUMMY_CARDS.get(sanitized, (True, None))

        txn_id = f"ch_{''.join(uuid.uuid4().hex)[:24]}"
        amount = Decimal(str(pickup.fee))

        if success:
            txn = PaymentTransaction.objects.create(
                user=user,
                amount=amount,
                currency="INR",
                payment_method=PaymentTransaction.PaymentMethods.STRIPE,
                status=PaymentTransaction.Statuses.COMPLETED,
                transaction_id=txn_id,
                description=f"Pickup #{pickup.id} — Card payment by {card_name}",
            )
            PaymentGatewayService._mark_pickup_paid(pickup)
            logger.info(f"[Gateway] Card payment SUCCESS — {txn_id} — Rs. {amount} for pickup #{pickup.id}")
            return {
                "success": True,
                "transaction_id": txn_id,
                "amount": float(amount),
                "method": "card",
                "card_last4": sanitized[-4:],
                "transaction": txn,
            }
        else:
            # Record the failed attempt for audit
            PaymentTransaction.objects.create(
                user=user,
                amount=amount,
                currency="INR",
                payment_method=PaymentTransaction.PaymentMethods.STRIPE,
                status=PaymentTransaction.Statuses.FAILED,
                transaction_id=txn_id,
                description=f"Pickup #{pickup.id} — Card payment FAILED ({decline_code})",
            )
            error_msg = _DECLINE_MESSAGES.get(decline_code, "Payment failed. Please try again.")
            logger.warning(f"[Gateway] Card payment FAILED — {decline_code} — pickup #{pickup.id}")
            return {
                "success": False,
                "error_code": decline_code,
                "error_message": error_msg,
            }

    @staticmethod
    @db_transaction.atomic
    def process_upi_payment(user, pickup, upi_id: str):
        """Process a UPI payment (always succeeds for any valid UPI ID format)."""
        import re
        upi_pattern = re.compile(r"^[\w.\-]+@[\w]+$")
        if not upi_pattern.match(upi_id):
            return {
                "success": False,
                "error_code": "invalid_upi",
                "error_message": "Invalid UPI ID format. Please enter a valid VPA (e.g. name@okaxis).",
            }

        txn_id = f"upi_{uuid.uuid4().hex[:20]}"
        amount = Decimal(str(pickup.fee))

        txn = PaymentTransaction.objects.create(
            user=user,
            amount=amount,
            currency="INR",
            payment_method=PaymentTransaction.PaymentMethods.STRIPE,  # closest available
            status=PaymentTransaction.Statuses.COMPLETED,
            transaction_id=txn_id,
            description=f"Pickup #{pickup.id} — UPI payment via {upi_id}",
        )
        PaymentGatewayService._mark_pickup_paid(pickup)
        logger.info(f"[Gateway] UPI payment SUCCESS — {txn_id} — Rs. {amount} for pickup #{pickup.id}")
        return {
            "success": True,
            "transaction_id": txn_id,
            "amount": float(amount),
            "method": "upi",
            "upi_id": upi_id,
            "transaction": txn,
        }

    @staticmethod
    @db_transaction.atomic
    def process_wallet_payment(user, pickup):
        """Redeem wallet points to pay the pickup fee (100 pts = Rs. 10)."""
        fee = Decimal(str(pickup.fee))
        if fee <= Decimal("0.00"):
            PaymentGatewayService._mark_pickup_paid(pickup)
            txn_id = f"wlt_{uuid.uuid4().hex[:20]}"
            txn = PaymentTransaction.objects.create(
                user=user,
                amount=Decimal("0.00"),
                currency="INR",
                payment_method=PaymentTransaction.PaymentMethods.WALLET,
                status=PaymentTransaction.Statuses.COMPLETED,
                transaction_id=txn_id,
                description=f"Pickup #{pickup.id} — Fully covered by coupon / wallet points",
            )
            return {
                "success": True,
                "transaction_id": txn_id,
                "amount": 0.0,
                "method": "wallet",
                "points_used": 0,
                "transaction": txn,
            }

        required_points = int((fee / POINTS_TO_INR_RATE).to_integral_value())
        current_points = getattr(user, "wallet_points", 0)

        if current_points < required_points:
            shortfall_inr = (required_points - current_points) * POINTS_TO_INR_RATE
            return {
                "success": False,
                "error_code": "insufficient_points",
                "error_message": (
                    f"You need {required_points:,} points to pay Rs. {fee:.2f}, "
                    f"but only have {current_points:,} points. "
                    f"You are short by {required_points - current_points:,} points "
                    f"(Rs. {shortfall_inr:.2f})."
                ),
            }

        txn_id = f"wlt_{uuid.uuid4().hex[:20]}"

        txn = PaymentTransaction.objects.create(
            user=user,
            amount=fee,
            currency="INR",
            payment_method=PaymentTransaction.PaymentMethods.WALLET,
            status=PaymentTransaction.Statuses.COMPLETED,
            transaction_id=txn_id,
            description=f"Pickup #{pickup.id} — Wallet redemption ({required_points:,} pts)",
        )

        # Deduct points from wallet
        WalletService.adjust_points(
            user=user,
            points_delta=-required_points,
            reason=f"Redeemed for Pickup #{pickup.id} payment (Rs. {fee:.2f})",
        )

        PaymentGatewayService._mark_pickup_paid(pickup)
        logger.info(f"[Gateway] Wallet payment SUCCESS — {txn_id} — {required_points} pts for pickup #{pickup.id}")
        return {
            "success": True,
            "transaction_id": txn_id,
            "amount": float(fee),
            "method": "wallet",
            "points_used": required_points,
            "transaction": txn,
        }

    @staticmethod
    def _mark_pickup_paid(pickup):
        """Mark a pickup as paid and transition it to PENDING status."""
        from waste_management.models import PickupRequest
        pickup.is_paid = True
        pickup.status = PickupRequest.StatusChoices.PENDING
        pickup.save(update_fields=["is_paid", "status"])
