"""
trashport/payments/services.py — Payment Gateway and Wallet Service Layer
==========================================================================

PURPOSE:
  This module provides all payment processing logic for TrashPort. It acts as
  the intermediary between the view layer (citizens/views.py) and the payment
  data models (payments/models.py).

  All three payment methods (Card, UPI, Wallet) go through this layer —
  never directly through the view. This ensures consistent audit trail creation,
  wallet point deduction logic, and pickup status transitions.

CONNECTION MAP:
  - trashport/citizens/views.py       → CitizenPaymentCheckoutView calls
                                        process_card_payment(), process_upi_payment(),
                                        process_wallet_payment()
  - trashport/payments/models.py      → Creates PaymentTransaction and WalletHistory records
  - waste_management/models.py        → PickupRequest (marks is_paid, updates status to PENDING)
  - waste_management/notifications.py → send_payment_completed_notification()
                                        (called from _mark_pickup_paid)

DUMMY / SIMULATED GATEWAY:
  This is a SIMULATED payment gateway — no real money changes hands.
  Specific test card numbers produce specific outcomes (success or decline).
  UPI payments always succeed for any syntactically valid UPI ID.
  Wallet payments succeed if the user has enough points.

  DUMMY_CARDS catalog (defined at module top):
    "4242424242424242" → Always succeeds (Visa)
    "5555555555554444" → Always succeeds (Mastercard)
    "4000000000000002" → card_declined
    "4000000000009995" → insufficient_funds
    "4000000000000069" → expired_card
    "4000000000000127" → incorrect_cvc

POINTS-TO-INR CONVERSION:
  POINTS_TO_INR_RATE = Rs. 0.10 per point
  100 points = Rs. 10 discount

FLOW FOR EACH PAYMENT METHOD:
  1. process_card_payment()  → Validates card vs DUMMY_CARDS → creates transaction → _mark_pickup_paid()
  2. process_upi_payment()   → Validates UPI ID regex format → creates transaction → _mark_pickup_paid()
  3. process_wallet_payment()→ Calculates required points → deducts via WalletService → _mark_pickup_paid()

  _mark_pickup_paid() (shared helper):
    • Sets pickup.is_paid = True and pickup.status = PENDING
    • Saves pickup to DB
    • Sends payment receipt notification + email (with invoice link)

RETURN FORMAT (all methods return a dict):
  Success: {"success": True, "transaction_id": ..., "amount": ..., "method": ..., ...}
  Failure: {"success": False, "error_code": ..., "error_message": ...}

IMPACT:
  - All public methods use @db_transaction.atomic — if anything fails mid-payment,
    the entire transaction (DB writes) is rolled back.
  - Changing POINTS_TO_INR_RATE affects all wallet redemptions immediately.
  - Changing _mark_pickup_paid() affects how all payment methods finalize a pickup.
"""

import logging
import uuid
from decimal import Decimal

from django.db import transaction as db_transaction

from .models import PaymentTransaction, WalletHistory

logger = logging.getLogger(__name__)


# ==============================================================================
# Test Card Catalog (Dummy Gateway)
# ==============================================================================
# Maps sanitized card numbers (no spaces/dashes) to (success, decline_code) tuples.
# Cards NOT in this dict are treated as successful (default=True, None).
#
# IMPACT: Add entries here to simulate new failure scenarios for testing.
# These values are also displayed in the checkout UI as a "test cards" guide.
# ==============================================================================

DUMMY_CARDS = {
    "4242424242424242": (True, None),           # Visa — always succeeds
    "5555555555554444": (True, None),           # Mastercard — always succeeds
    "4000000000000002": (False, "card_declined"),
    "4000000000009995": (False, "insufficient_funds"),
    "4000000000000069": (False, "expired_card"),
    "4000000000000127": (False, "incorrect_cvc"),
}

# Points-to-INR conversion rate.
# IMPACT: Changing this affects all wallet payment amounts and coupon values.
# 100 points = Rs. 10 → 1 point = Rs. 0.10
POINTS_TO_INR_RATE = Decimal("0.10")


# ==============================================================================
# Human-readable decline messages (shown to user on card failure)
# ==============================================================================

_DECLINE_MESSAGES = {
    "card_declined": "Your card was declined. Please try a different card.",
    "insufficient_funds": "Insufficient funds. Please use a different payment method.",
    "expired_card": "Your card has expired. Please check the expiry date and try again.",
    "incorrect_cvc": "The CVC code is incorrect. Please check and try again.",
}


# ==============================================================================
# StripePaymentService
# ==============================================================================
# Legacy service wrapper for Stripe PaymentIntent simulation.
# Used for creating pending transaction records before payment is confirmed.
#
# CONNECTION: Not actively used by current checkout views (PaymentGatewayService
#             is the primary service). Kept for potential future Stripe integration.
#
# IMPACT: If connecting to real Stripe, replace the mock txn_id generation
#         with actual Stripe SDK calls here.
# ==============================================================================

class StripePaymentService:

    @staticmethod
    def create_payment_intent(user, amount: Decimal, currency: str = "USD", description: str = ""):
        """
        Simulates Stripe PaymentIntent creation.

        Creates a PENDING PaymentTransaction record and returns a mock
        client_secret and transaction_id.

        IMPACT: In production, replace mock logic with real Stripe API call:
            stripe.PaymentIntent.create(amount=int(amount*100), currency=currency)
        """
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
        """
        Marks a PENDING PaymentTransaction as COMPLETED by transaction_id.
        Used to finalize a payment after client-side Stripe confirmation.
        """
        txn = PaymentTransaction.objects.filter(transaction_id=transaction_id).first()
        if txn and txn.status != PaymentTransaction.Statuses.COMPLETED:
            txn.status = PaymentTransaction.Statuses.COMPLETED
            txn.save()
            logger.info(f"Payment transaction {transaction_id} marked as COMPLETED.")
        return txn


# ==============================================================================
# WalletService
# ==============================================================================
# Utility service for safe wallet point adjustments with audit logging.
#
# Used by:
#   - waste_management/models.py → PickupRequest.save() credits citizen points on COMPLETED
#   - trashport/citizens/views.py → CitizenRedeemCouponView / CitizenRemoveCouponView
#   - PaymentGatewayService.process_wallet_payment() (below) for point deductions
#   - trashport/admins/views.py  → AdminWalletAdjustView for manual admin adjustments
#
# IMPACT:
#   - Always use this service to change wallet_points — never set user.wallet_points
#     directly, as this method creates the WalletHistory audit record.
#   - Uses @atomic to ensure points deduction and history record are always in sync.
# ==============================================================================

class WalletService:

    @staticmethod
    @db_transaction.atomic
    def adjust_points(user, points_delta: int, reason: str):
        """
        Atomically credits or debits wallet points and creates a WalletHistory record.

        Args:
            user         : The User whose wallet_points to adjust.
            points_delta : Positive to credit (earn points), negative to debit (spend points).
                           If deduction would go below 0, balance is floored at 0.
            reason       : Human-readable reason for the adjustment (shown in wallet history).

        Returns:
            WalletHistory: The newly created history record.

        Example:
            # Award 50 points for recycling 5kg of Metal
            WalletService.adjust_points(user=citizen, points_delta=50, reason="Recycling reward: 5kg Metal (Pickup #12)")

            # Deduct 100 points for coupon redemption
            WalletService.adjust_points(user=citizen, points_delta=-100, reason="Coupon TP3A8B9C1D")

        IMPACT:
            - Balance is floored at 0 (max(0, current + delta)).
            - Creates a WalletHistory record for every call (audit trail).
        """
        current_points = getattr(user, "wallet_points", 0)
        new_balance = max(0, current_points + points_delta)
        user.wallet_points = new_balance
        user.save(update_fields=["wallet_points"])

        # Create audit record in WalletHistory table
        record = WalletHistory.objects.create(
            user=user,
            points_delta=points_delta,
            reason=reason,
        )
        return record


# ==============================================================================
# PaymentGatewayService
# ==============================================================================
# The primary payment processing service for the checkout flow.
# Handles three payment methods: CARD, UPI, and WALLET.
#
# All methods are @db_transaction.atomic — if anything fails mid-method,
# all DB changes in that method call are rolled back.
#
# All methods call _mark_pickup_paid() on success to:
#   1. Set pickup.is_paid = True
#   2. Transition pickup.status → PENDING (enters collector queue)
#   3. Send payment receipt notification + email to citizen
#
# CONNECTION:
#   - Called from: trashport/citizens/views.py → CitizenPaymentCheckoutView.post()
#   - Reads pickup.fee for the amount to charge (may be discounted by coupon)
#   - Creates PaymentTransaction records for audit
#   - Calls WalletService.adjust_points() for WALLET payments
# ==============================================================================

class PaymentGatewayService:
    """
    Simulated payment gateway for TrashPort checkout.

    Supports three payment methods:
      - CARD  : Validates card details against DUMMY_CARDS catalog.
      - UPI   : Accepts any syntactically valid VPA (user@bank format).
      - WALLET: Redeems citizen recycling points at Rs. 0.10/point.

    On success:
      - Creates a COMPLETED PaymentTransaction record.
      - Calls _mark_pickup_paid() → sets pickup.is_paid=True, status=PENDING.
      - Returns {"success": True, "transaction_id": ..., ...}

    On failure:
      - Creates a FAILED PaymentTransaction record (for audit trail).
      - Returns {"success": False, "error_code": ..., "error_message": ...}
    """

    @staticmethod
    @db_transaction.atomic
    def process_card_payment(user, pickup, card_number: str, card_name: str,
                             expiry: str, cvv: str):
        """
        Processes a card payment using the dummy card catalog.

        STEP-BY-STEP:
          1. Strip spaces/dashes from card_number to get sanitized 16-digit string.
          2. Look up sanitized number in DUMMY_CARDS:
               - Found: use mapped (success, decline_code)
               - Not found: treat as success (default = True, None)
          3. If success:
               - Create COMPLETED PaymentTransaction record
               - Call _mark_pickup_paid() to finalize pickup
               - Return success dict with card_last4 for receipt display
          4. If failure:
               - Create FAILED PaymentTransaction record (audit)
               - Return failure dict with human-readable error message

        Args:
            user       : The paying citizen's User instance.
            pickup     : The PickupRequest being paid for.
            card_number: Raw card number (may contain spaces or dashes).
            card_name  : Name on card (for transaction description only).
            expiry     : Card expiry string (not validated, display only).
            cvv        : Card CVV (not validated in dummy mode, display only).

        IMPACT: To add real card validation, replace DUMMY_CARDS lookup with
                actual Stripe/Razorpay SDK charge call.
        """
        # Normalize card number: remove spaces and dashes for catalog lookup
        sanitized = card_number.replace(" ", "").replace("-", "")
        success, decline_code = DUMMY_CARDS.get(sanitized, (True, None))  # Default: success

        txn_id = f"ch_{''.join(uuid.uuid4().hex)[:24]}"
        amount = Decimal(str(pickup.fee))

        if success:
            # --- Create COMPLETED transaction record ---
            txn = PaymentTransaction.objects.create(
                user=user,
                amount=amount,
                currency="INR",
                payment_method=PaymentTransaction.PaymentMethods.STRIPE,
                status=PaymentTransaction.Statuses.COMPLETED,
                transaction_id=txn_id,
                description=f"Pickup #{pickup.id} — Card payment by {card_name}",
            )
            # Mark pickup as paid and transition to PENDING (enters collector queue)
            PaymentGatewayService._mark_pickup_paid(pickup, transaction=txn)
            logger.info(f"[Gateway] Card payment SUCCESS — {txn_id} — Rs. {amount} for pickup #{pickup.id}")
            return {
                "success": True,
                "transaction_id": txn_id,
                "amount": float(amount),
                "method": "card",
                "card_last4": sanitized[-4:],    # Last 4 digits shown on receipt
                "transaction": txn,
            }
        else:
            # --- Create FAILED transaction record (audit trail) ---
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
        """
        Processes a UPI payment (always succeeds for valid UPI ID format).

        VALIDATION:
          UPI ID must match pattern: alphanumeric/dot/dash@bankcode
          e.g., "user@okaxis", "9876543210@paytm", "myname.123@icici"

          Invalid format → returns failure without creating any transaction.
          Valid format → always succeeds (simulated approval).

        STEP-BY-STEP:
          1. Validate UPI ID regex format.
          2. Generate unique txn_id (prefix: "upi_").
          3. Create COMPLETED PaymentTransaction record.
          4. Call _mark_pickup_paid().
          5. Return success dict with upi_id for receipt display.

        IMPACT: To connect real UPI payments, replace with actual UPI gateway
                API call (e.g., Razorpay, PhonePe, PayU).
        """
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

        # --- UPI always succeeds for valid format ---
        txn = PaymentTransaction.objects.create(
            user=user,
            amount=amount,
            currency="INR",
            payment_method=PaymentTransaction.PaymentMethods.STRIPE,
            status=PaymentTransaction.Statuses.COMPLETED,
            transaction_id=txn_id,
            description=f"Pickup #{pickup.id} — UPI payment via {upi_id}",
        )
        PaymentGatewayService._mark_pickup_paid(pickup, transaction=txn)
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
        """
        Redeems citizen wallet points to pay the pickup fee.

        CONVERSION: POINTS_TO_INR_RATE = Rs. 0.10 per point.
          Required points = ceil(fee / 0.10) = fee × 10

        STEP-BY-STEP:
          1. If fee = 0.00 (coupon fully covers it):
               - Create a Rs. 0 COMPLETED transaction.
               - Mark pickup as paid immediately.
               - Return success with points_used = 0.
          2. If fee > 0:
               - Calculate required_points = int(fee / POINTS_TO_INR_RATE)
               - If user.wallet_points < required_points: return "insufficient_points" failure.
               - Otherwise: create COMPLETED transaction + deduct points via WalletService.
               - Mark pickup as paid.

        IMPACT:
          - Changing POINTS_TO_INR_RATE changes how many points are needed per Rs.
          - WalletService.adjust_points() creates the WalletHistory audit record.
        """
        fee = Decimal(str(pickup.fee))

        # --- Special case: fee fully covered by coupon (fee = 0.00) ---
        if fee <= Decimal("0.00"):
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
            PaymentGatewayService._mark_pickup_paid(pickup, transaction=txn)
            return {
                "success": True,
                "transaction_id": txn_id,
                "amount": 0.0,
                "method": "wallet",
                "points_used": 0,
                "transaction": txn,
            }

        # --- Normal wallet payment: check and deduct points ---
        required_points = int((fee / POINTS_TO_INR_RATE).to_integral_value())
        current_points = getattr(user, "wallet_points", 0)

        if current_points < required_points:
            # Not enough points — show detailed shortfall message
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

        # --- Create COMPLETED transaction record ---
        txn = PaymentTransaction.objects.create(
            user=user,
            amount=fee,
            currency="INR",
            payment_method=PaymentTransaction.PaymentMethods.WALLET,
            status=PaymentTransaction.Statuses.COMPLETED,
            transaction_id=txn_id,
            description=f"Pickup #{pickup.id} — Wallet redemption ({required_points:,} pts)",
        )

        # --- Deduct points from user wallet (creates WalletHistory record) ---
        WalletService.adjust_points(
            user=user,
            points_delta=-required_points,
            reason=f"Redeemed for Pickup #{pickup.id} payment (Rs. {fee:.2f})",
        )

        PaymentGatewayService._mark_pickup_paid(pickup, transaction=txn)
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
    def _mark_pickup_paid(pickup, transaction=None):
        """
        Shared helper called by all three payment methods on success.

        WHAT IT DOES:
          1. Sets pickup.is_paid = True
          2. Sets pickup.status = PENDING (enters the collector job queue)
          3. Saves both fields to DB
          4. Resolves the invoice URL for the notification email
          5. Calls send_payment_completed_notification() to:
               - Create in-app payment notification
               - Send HTML payment receipt email to citizen

        IMPACT:
          - After this runs, the pickup is visible to collectors as PENDING.
          - The invoice URL uses 'waste_management:payment_invoice' — if the URL
            name changes in urls.py, update this reverse() call.
          - Exception in notification is caught and logged; does NOT fail the payment.

        CONNECTION:
          - waste_management/models.py  → PickupRequest.StatusChoices (PENDING)
          - waste_management/notifications.py → send_payment_completed_notification()
          - waste_management/urls.py    → 'waste_management:payment_invoice' URL name
        """
        from waste_management.models import PickupRequest

        # Step 1 & 2: Mark paid and transition to collector queue
        pickup.is_paid = True
        pickup.status = PickupRequest.StatusChoices.PENDING
        pickup.save(update_fields=["is_paid", "status"])

        # Step 3: Resolve invoice URL (used in email notification)
        try:
            from django.urls import reverse
            # The URL name is 'waste_management:payment_invoice'
            # Registered in waste_management/urls.py as path("pickups/<int:pk>/invoice/", ...)
            invoice_url = reverse("waste_management:payment_invoice", kwargs={"pk": pickup.pk})
        except Exception:
            # Fallback if URL resolution fails (e.g., during tests)
            invoice_url = f"/waste-management/pickups/{pickup.pk}/invoice/"

        # Step 4: Send receipt notification and email
        try:
            from waste_management.notifications import send_payment_completed_notification
            send_payment_completed_notification(
                user=pickup.citizen,
                pickup=pickup,
                transaction=transaction,
                invoice_url=invoice_url,
            )
        except Exception as e:
            # Non-fatal: notification failure must NOT undo a successful payment
            logger.error(f"Failed to send payment receipt notification: {e}")
