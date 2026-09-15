"""
waste_management/notifications.py — Pickup Lifecycle Notification Dispatcher
=============================================================================

PURPOSE:
  This module contains standalone functions that trigger both in-app notifications
  and email alerts at key moments in the PickupRequest lifecycle.

  These functions are called from inside PickupRequest.save() (waste_management/models.py)
  and from trashport/payments/services.py. They MUST be imported lazily inside
  save() to avoid circular import issues (models.py → notifications.py → models.py).

CONNECTION MAP:
  - waste_management/models.py        → calls functions here on status transitions
  - trashport/payments/services.py    → calls send_payment_completed_notification()
  - trashport/notifications/services.py → NotificationService provides the
                                          create_notification() and send_email_notification()
                                          utility methods used here
  - trashport/notifications/models.py  → Notification model used for in-app records

WHEN EACH FUNCTION IS CALLED:
  send_pickup_requested_notification()   → after PickupRequest.save() on CREATE
  send_pickup_assigned_notification()    → when pickup.collector changes (UPDATE)
  send_pickup_cancelled_notification()   → when status → CANCELLED (UPDATE)
  send_payment_completed_notification()  → after PaymentGatewayService._mark_pickup_paid()

EMAIL TEMPLATES:
  HTML and text templates are expected in:
    trashport/notifications/templates/emails/
      pickup_confirmed.html / .txt
      pickup_assigned.html / .txt
      pickup_cancelled.html / .txt
      payment_receipt.html / .txt

  If a template is missing, NotificationService.send_email_notification()
  falls back to a plain-text fallback (logs a warning).

IMPACT:
  - All functions catch and log exceptions silently — notification failures
    should NEVER cause the calling view to crash or show an error to users.
  - To add a new lifecycle event notification:
      1. Add a new function here.
      2. Call it from PickupRequest.save() in the appropriate transition block.
      3. Create the corresponding email templates.
"""

import logging
from trashport.notifications.models import Notification
from trashport.notifications.services import NotificationService

logger = logging.getLogger(__name__)


def send_pickup_requested_notification(pickup):
    """
    Sends a booking confirmation to the citizen immediately after
    a new PickupRequest is created.

    Called from: waste_management/models.py → PickupRequest.save() (CREATE path, post-save)

    In-app notification: Created in the Notification model for in-dashboard display.
    Email: Sends a styled HTML pickup_confirmed email template.

    IMPACT: Failure is caught and logged — does NOT raise or affect the booking.
    """
    try:
        citizen = pickup.citizen
        if not citizen:
            return

        title = f"Pickup Request Confirmed #{pickup.display_id}"
        message = (
            f"Your waste collection request #{pickup.display_id} has been booked. "
            f"Scheduled time: {pickup.schedule_date.strftime('%b %d, %Y %I:%M %p') if pickup.schedule_date else 'Scheduled'}."
        )

        # --- Step 1: Create in-app notification record ---
        NotificationService.create_notification(
            user=citizen,
            title=title,
            message=message,
            notification_type=Notification.Types.PICKUP,
        )

        # --- Step 2: Send email notification ---
        if citizen.email:
            addr_str = str(pickup.address) if pickup.address else "Selected Location"
            time_str = pickup.schedule_date.strftime("%b %d, %Y %I:%M %p") if pickup.schedule_date else "Scheduled"
            user_name = getattr(citizen, "name", None) or citizen.email.split("@")[0]

            NotificationService.send_email_notification(
                to_email=citizen.email,
                subject=f"Pickup Request Confirmed #{pickup.display_id}",
                template_base="pickup_confirmed",   # → templates/emails/pickup_confirmed.html/.txt
                context={
                    "user_name": user_name,
                    "pickup_id": pickup.display_id,
                    "scheduled_time": time_str,
                    "address": addr_str,
                },
            )
    except Exception as e:
        # Non-fatal: log and continue. Pickup booking must not fail due to notification issues.
        logger.error(f"Failed to send pickup requested notification for #{pickup.pk}: {e}")


def send_pickup_assigned_notification(pickup, collector=None):
    """
    Notifies the citizen that a collector has been assigned to their pickup.

    Called from: waste_management/models.py → PickupRequest.save() (UPDATE path)
    Trigger condition: pickup.collector changes from None/other to a new collector.

    In-app notification: Created in the Notification model.
    Email: Sends pickup_assigned email template.

    Args:
        pickup    : The PickupRequest instance being updated.
        collector : The newly assigned collector User instance.

    IMPACT: Failure is caught and logged — does NOT raise or affect the assignment.
    """
    try:
        citizen = pickup.citizen
        if not citizen:
            return

        col = collector or pickup.collector
        col_name = getattr(col, "name", None) or (col.email.split("@")[0] if col else "Collector")
        title = f"Collector Assigned #{pickup.display_id}"
        message = f"Collector {col_name} has been assigned to your pickup request #{pickup.display_id}."

        # --- Step 1: In-app notification ---
        NotificationService.create_notification(
            user=citizen,
            title=title,
            message=message,
            notification_type=Notification.Types.PICKUP,
        )

        # --- Step 2: Email notification ---
        if citizen.email:
            user_name = getattr(citizen, "name", None) or citizen.email.split("@")[0]
            NotificationService.send_email_notification(
                to_email=citizen.email,
                subject=f"Collector Assigned - Pickup #{pickup.display_id}",
                template_base="pickup_assigned",    # → templates/emails/pickup_assigned.html/.txt
                context={
                    "user_name": user_name,
                    "collector_name": col_name,
                    "pickup_id": pickup.display_id,
                },
            )
    except Exception as e:
        logger.error(f"Failed to send pickup assigned notification for #{pickup.pk}: {e}")


def send_pickup_cancelled_notification(pickup, reason="Cancelled by user or administrator"):
    """
    Notifies the citizen when their pickup request is cancelled.

    Called from: waste_management/models.py → PickupRequest.save() (UPDATE path)
    Trigger condition: status changes to CANCELLED.

    Args:
        pickup : The PickupRequest instance being cancelled.
        reason : Human-readable cancellation reason (logged in message).

    IMPACT: Failure is caught and logged — does NOT raise or affect the cancellation.
    """
    try:
        citizen = pickup.citizen
        if not citizen:
            return

        title = f"Pickup Cancelled #{pickup.display_id}"
        message = f"Your pickup request #{pickup.display_id} has been cancelled. Reason: {reason}"

        # --- Step 1: In-app notification ---
        NotificationService.create_notification(
            user=citizen,
            title=title,
            message=message,
            notification_type=Notification.Types.PICKUP,
        )

        # --- Step 2: Email notification ---
        if citizen.email:
            user_name = getattr(citizen, "name", None) or citizen.email.split("@")[0]
            NotificationService.send_email_notification(
                to_email=citizen.email,
                subject=f"Pickup Request Cancelled #{pickup.display_id}",
                template_base="pickup_cancelled",   # → templates/emails/pickup_cancelled.html/.txt
                context={
                    "user_name": user_name,
                    "pickup_id": pickup.display_id,
                    "reason": reason,
                },
            )
    except Exception as e:
        logger.error(f"Failed to send pickup cancelled notification for #{pickup.pk}: {e}")


def send_payment_completed_notification(user, pickup, transaction, invoice_url=None):
    """
    Sends a payment receipt and invoice link to the citizen after a successful payment.

    Called from: trashport/payments/services.py → PaymentGatewayService._mark_pickup_paid()
    (NOT called from PickupRequest.save() — payments trigger this directly)

    In-app notification: Payment type, includes transaction ID and amount.
    Email: Sends payment_receipt email template with invoice download link.

    Args:
        user        : The paying citizen's User instance.
        pickup      : The PickupRequest that was paid for.
        transaction : The PaymentTransaction record created by the gateway.
        invoice_url : URL to the printable invoice page (optional).

    IMPACT: Failure is caught and logged — does NOT raise or affect payment marking.
    """
    try:
        if not user:
            return

        # Extract transaction details (with safe fallbacks)
        amount = getattr(transaction, "amount", pickup.fee)
        currency = getattr(transaction, "currency", "INR")
        txn_id = getattr(transaction, "transaction_id", f"txn_{pickup.id}")
        desc = getattr(transaction, "description", f"Payment for Pickup #{pickup.display_id}")

        # Format currency symbol
        curr_sym = "₹" if currency == "INR" else ("$" if currency == "USD" else f"{currency} ")
        title = f"Payment Receipt: Pickup #{pickup.display_id}"
        message = (
            f"Payment of {curr_sym}{amount} for Pickup #{pickup.display_id} completed successfully. "
            f"Txn ID: {txn_id}."
        )

        # --- Step 1: In-app notification ---
        NotificationService.create_notification(
            user=user,
            title=title,
            message=message,
            notification_type=Notification.Types.PAYMENT,
        )

        # --- Step 2: Email receipt with invoice link ---
        if user.email:
            user_name = getattr(user, "name", None) or user.email.split("@")[0]
            NotificationService.send_email_notification(
                to_email=user.email,
                subject=f"Payment Receipt #{txn_id} - Pickup #{pickup.display_id}",
                template_base="payment_receipt",    # → templates/emails/payment_receipt.html/.txt
                context={
                    "user_name": user_name,
                    "amount": amount,
                    "currency": currency,
                    "transaction_id": txn_id,
                    "description": desc,
                    "invoice_url": invoice_url,     # Link citizen can click to download invoice
                },
            )
    except Exception as e:
        logger.error(f"Failed to send payment notification for user {user.pk}: {e}")
