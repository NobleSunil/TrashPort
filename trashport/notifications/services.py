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
