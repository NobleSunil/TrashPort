import logging
from .services import NotificationService

logger = logging.getLogger(__name__)

# Celery tasks (or synchronous fallback if celery broker not connected)
try:
    from config.celery import app as celery_app
    
    @celery_app.task
    def async_send_email_notification(to_email: str, subject: str, template_base: str, context: dict):
        NotificationService.send_email_notification(to_email, subject, template_base, context)
except Exception:
    def async_send_email_notification(to_email: str, subject: str, template_base: str, context: dict):
        NotificationService.send_email_notification(to_email, subject, template_base, context)
