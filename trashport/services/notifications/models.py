"""
trashport/notifications/models.py — In-App Notification Model
==============================================================

PURPOSE:
  Defines the Notification model which stores in-app alerts for users.
  These appear in the notification bell/panel on the dashboard and are
  distinct from email notifications.

CONNECTION MAP:
  - waste_management/notifications.py → creates Notification records via
                                         NotificationService.create_notification()
  - trashport/notifications/services.py → NotificationService.create_notification()
                                          is the only method that should create records
  - All role dashboards (citizen/collector/admin) read Notification.objects.filter(user=user)
    to populate the notification panel in the nav bar.

TYPES (Notification.Types):
  PICKUP  : For all pickup lifecycle events (created, assigned, cancelled, completed)
  PAYMENT : For payment receipt and confirmation events
  SYSTEM  : For platform-wide announcements (maintenance, policy updates)

IMPACT:
  - Marking is_read=True hides the notification from the unread count badge.
  - Notifications are NEVER automatically deleted. Consider adding a cleanup
    management command for archiving old notifications in production.
  - Adding a new notification type: add to Notification.Types and update
    the appropriate dashboard template notification icon logic.
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Types(models.TextChoices):
        PICKUP = "PICKUP", _("Pickup Alert")
        PAYMENT = "PAYMENT", _("Payment Alert")
        COMPLAINT = "COMPLAINT", _("Complaint Alert")
        SYSTEM = "SYSTEM", _("System Message")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=Types.choices,
        default=Types.SYSTEM,
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.title} ({'Read' if self.is_read else 'Unread'})"
