# ==============================================================================
# TrashPort - Asynchronous Notification Background Tasks
# ==============================================================================
# This module defines Celery tasks for non-blocking email dispatching.
# Background processing prevents slow SMTP network requests from delaying
# user HTTP request-response cycles.
# ==============================================================================

import logging

from .services import NotificationService

# Logger instance for task execution logging
logger = logging.getLogger(__name__)

# ==============================================================================
# Celery Asynchronous Task Definition (with Synchronous Fallback)
# ==============================================================================
try:
    # Import Celery application instance from config
    from config.celery import app as celery_app

    @celery_app.task
    def async_send_email_notification(to_email: str, subject: str, template_base: str, context: dict):
        """
        Asynchronous Celery task that sends emails in the background.
        Dispatched via Redis broker to Celery worker processes.
        """
        NotificationService.send_email_notification(to_email, subject, template_base, context)

except Exception:
    # Graceful fallback: If Celery or message broker is offline in development,
    # execute the notification synchronously without crashing the application.
    def async_send_email_notification(to_email: str, subject: str, template_base: str, context: dict):
        """
        Synchronous fallback function used when Celery worker is not configured.
        """
        NotificationService.send_email_notification(to_email, subject, template_base, context)
