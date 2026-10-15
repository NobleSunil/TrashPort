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

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Notification

# Logger instance for tracking email delivery and notification events
logger = logging.getLogger(__name__)


# ==============================================================================
# Notification Service Layer
# ==============================================================================
class NotificationService:
    """
    Centralized service class responsible for:
    1. Generating in-app notification database records
    2. Rendering and sending multi-part (HTML & plain-text) transactional emails
    """

    @staticmethod
    def create_notification(user, title: str, message: str, notification_type: str = Notification.Types.SYSTEM):
        """
        Creates an in-app notification database record for the given user.
        Parameters:
            user (User): Recipient user instance
            title (str): Brief summary heading
            message (str): Full notification message body
            notification_type (str): Category (PICKUP, PAYMENT, COMPLAINT, SYSTEM)
        Returns:
            Notification: The newly created model instance
        """
        # Save notification to PostgreSQL database
        return Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
        )

    @staticmethod
    def send_email_notification(to_email: str, subject: str, template_base: str, context: dict):
        """
        Renders HTML and plain-text email templates and sends the message via SMTP.
        Parameters:
            to_email (str): Recipient email address
            subject (str): Email subject line
            template_base (str): Base template filename (e.g. 'pickup_assigned')
            context (dict): Dynamic variables passed to the Django template engine
        """
        # Attempt to render both HTML and plain-text versions of the email template
        try:
            html_message = render_to_string(f"emails/{template_base}.html", context)
            text_message = render_to_string(f"emails/{template_base}.txt", context)
        except Exception as e:
            # Fallback if specific template files are unavailable
            logger.warning(f"Template rendering fallback for {template_base}: {e}")
            html_message = f"<p>{subject}</p>"
            text_message = subject

        # Align sender email with authenticated SMTP user to prevent Gmail delivery rejections
        host_user = getattr(settings, "EMAIL_HOST_USER", "")
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "")
        if not from_email or "noreply@" in from_email or "support@trashport.local" in from_email:
            if host_user:
                from_email = f"TrashPort <{host_user}>"
            else:
                from_email = "TrashPort <noreply@trashport.com>"

        # 1. Dispatch email through configured Django email backend
        try:
            send_mail(
                subject=subject,
                message=text_message,
                from_email=from_email,
                recipient_list=[to_email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info("Email sent successfully to %s: %s", to_email, subject)
            return True
        except Exception as primary_err:
            logger.warning(
                "Primary email dispatch to %s failed (%s). Attempting Port 465 SSL fallback...",
                to_email,
                primary_err,
            )

            # 2. Automated fallback via Port 465 SSL if Gmail SMTP credentials are configured
            host_pass = getattr(settings, "EMAIL_HOST_PASSWORD", "")
            host = getattr(settings, "EMAIL_HOST", "smtp.gmail.com")

            if host_user and host_pass and "gmail" in host.lower():
                try:
                    from django.core.mail import get_connection, EmailMultiAlternatives
                    ssl_conn = get_connection(
                        backend="django.core.mail.backends.smtp.EmailBackend",
                        host=host,
                        port=465,
                        username=host_user,
                        password=host_pass,
                        use_ssl=True,
                        use_tls=False,
                        timeout=10,
                    )
                    email_obj = EmailMultiAlternatives(
                        subject=subject,
                        body=text_message,
                        from_email=from_email,
                        to=[to_email],
                        connection=ssl_conn,
                    )
                    if html_message:
                        email_obj.attach_alternative(html_message, "text/html")
                    email_obj.send(fail_silently=False)
                    logger.info("Email sent successfully via Port 465 SSL fallback to %s: %s", to_email, subject)
                    return True
                except Exception as ssl_err:
                    logger.error("Port 465 SSL fallback also failed for %s: %s", to_email, ssl_err)

            logger.error("Failed to deliver email to %s: %s", to_email, primary_err)
            return False
