import logging
from django.db import transaction
from trashport.notifications.models import Notification
from trashport.notifications.services import NotificationService

logger = logging.getLogger(__name__)


def send_pickup_requested_notification(pickup):
    """
    Sends in-app and email notifications to the citizen when a pickup is requested.
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

        NotificationService.create_notification(
            user=citizen,
            title=title,
            message=message,
            notification_type=Notification.Types.PICKUP,
        )

        if citizen.email:
            addr_str = str(pickup.address) if pickup.address else "Selected Location"
            time_str = pickup.schedule_date.strftime("%b %d, %Y %I:%M %p") if pickup.schedule_date else "Scheduled"
            user_name = getattr(citizen, "name", None) or citizen.email.split("@")[0]

            NotificationService.send_email_notification(
                to_email=citizen.email,
                subject=f"Pickup Request Confirmed #{pickup.display_id}",
                template_base="pickup_confirmed",
                context={
                    "user_name": user_name,
                    "pickup_id": pickup.display_id,
                    "scheduled_time": time_str,
                    "address": addr_str,
                },
            )
    except Exception as e:
        logger.error(f"Failed to send pickup requested notification for #{pickup.pk}: {e}")


def send_pickup_assigned_notification(pickup, collector=None):
    """
    Sends in-app and email notifications to the citizen when a collector is assigned.
    """
    try:
        citizen = pickup.citizen
        if not citizen:
            return

        col = collector or pickup.collector
        col_name = getattr(col, "name", None) or (col.email.split("@")[0] if col else "Collector")
        title = f"Collector Assigned #{pickup.display_id}"
        message = f"Collector {col_name} has been assigned to your pickup request #{pickup.display_id}."

        NotificationService.create_notification(
            user=citizen,
            title=title,
            message=message,
            notification_type=Notification.Types.PICKUP,
        )

        if citizen.email:
            user_name = getattr(citizen, "name", None) or citizen.email.split("@")[0]
            NotificationService.send_email_notification(
                to_email=citizen.email,
                subject=f"Collector Assigned - Pickup #{pickup.display_id}",
                template_base="pickup_assigned",
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
    Sends in-app and email notifications to the citizen when a pickup is cancelled.
    """
    try:
        citizen = pickup.citizen
        if not citizen:
            return

        title = f"Pickup Cancelled #{pickup.display_id}"
        message = f"Your pickup request #{pickup.display_id} has been cancelled. Reason: {reason}"

        NotificationService.create_notification(
            user=citizen,
            title=title,
            message=message,
            notification_type=Notification.Types.PICKUP,
        )

        if citizen.email:
            user_name = getattr(citizen, "name", None) or citizen.email.split("@")[0]
            NotificationService.send_email_notification(
                to_email=citizen.email,
                subject=f"Pickup Request Cancelled #{pickup.display_id}",
                template_base="pickup_cancelled",
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
    Sends in-app and email notifications (payment receipt & invoice) to citizen when payment is done.
    """
    try:
        if not user:
            return

        amount = getattr(transaction, "amount", pickup.fee)
        currency = getattr(transaction, "currency", "INR")
        txn_id = getattr(transaction, "transaction_id", f"txn_{pickup.id}")
        desc = getattr(transaction, "description", f"Payment for Pickup #{pickup.display_id}")

        curr_sym = "₹" if currency == "INR" else ("$" if currency == "USD" else f"{currency} ")
        title = f"Payment Receipt: Pickup #{pickup.display_id}"
        message = (
            f"Payment of {curr_sym}{amount} for Pickup #{pickup.display_id} completed successfully. "
            f"Txn ID: {txn_id}."
        )

        NotificationService.create_notification(
            user=user,
            title=title,
            message=message,
            notification_type=Notification.Types.PAYMENT,
        )

        if user.email:
            user_name = getattr(user, "name", None) or user.email.split("@")[0]
            NotificationService.send_email_notification(
                to_email=user.email,
                subject=f"Payment Receipt #{txn_id} - Pickup #{pickup.display_id}",
                template_base="payment_receipt",
                context={
                    "user_name": user_name,
                    "amount": amount,
                    "currency": currency,
                    "transaction_id": txn_id,
                    "description": desc,
                    "invoice_url": invoice_url,
                },
            )
    except Exception as e:
        logger.error(f"Failed to send payment notification for user {user.pk}: {e}")
