"""
trashport/notifications/services.py — In-App and Email Notification Utilities
===============================================================================

PURPOSE:
  Provides two core notification delivery methods:
  1. create_notification()       — Creates a Notification DB record for in-dashboard display.
  2. send_email_notification()   — Renders HTML/text email templates and sends via Django's mail.

  All lifecycle notification triggers live in waste_management/notifications.py
  which CALLS these services. This file is the low-level delivery layer only.

CONNECTION MAP:
  - waste_management/notifications.py → calls both methods for pickup/payment events
  - trashport/notifications/models.py → Notification model (used by create_notification)
  - Email templates directory:
      trashport/notifications/templates/emails/
        pickup_confirmed.html / .txt
        pickup_assigned.html / .txt
        pickup_cancelled.html / .txt
        payment_receipt.html / .txt

EMAIL CONFIGURATION:
  Sender address: settings.DEFAULT_FROM_EMAIL (default: "support@trashport.local")
  Uses Django's send_mail() with fail_silently=True (email errors are logged, not raised).

IMPACT:
  - If email templates are missing, falls back to a plain-text message (logs a warning).
  - To switch email backends (SMTP, SendGrid, SES), configure EMAIL_BACKEND in settings/.
  - To add a new notification type, add the type to Notification.Types in models.py
    and call create_notification() with that type.
"""

import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def create_notification(user, title: str, message: str, notification_type: str = Notification.Types.SYSTEM):
        """Creates an in-app notification record."""
        return Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
        )

    @staticmethod
    def send_email_notification(to_email: str, subject: str, template_base: str, context: dict):
        """Renders HTML and text email templates and sends email."""
        try:
            html_message = render_to_string(f"emails/{template_base}.html", context)
            text_message = render_to_string(f"emails/{template_base}.txt", context)
        except Exception as e:
            logger.warning(f"Template rendering fallback for {template_base}: {e}")
            html_message = f"<p>{subject}</p>"
            text_message = subject

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "support@trashport.local")
        try:
            send_mail(
                subject=subject,
                message=text_message,
                from_email=from_email,
                recipient_list=[to_email],
                html_message=html_message,
                fail_silently=True,
            )
            logger.info(f"Email sent to {to_email}: {subject}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
