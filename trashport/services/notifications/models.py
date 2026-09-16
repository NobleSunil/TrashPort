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

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """
    In-App Notification entity stored in PostgreSQL database.
    Represents an alert displayed in the user's dashboard notification center.
    """
    # Notification category choices for UI badge icons and filtering
    class Types(models.TextChoices):
        PICKUP = "PICKUP", _("Pickup Alert")          # Waste collection scheduling, assignment, or completion
        PAYMENT = "PAYMENT", _("Payment Alert")        # Invoices, fee payments, and collector payout confirmations
        COMPLAINT = "COMPLAINT", _("Complaint Alert")  # Citizen grievance updates and administrative resolutions
        SYSTEM = "SYSTEM", _("System Message")         # Global announcements, maintenance, and policy updates

    # Foreign key linking notification to the recipient User (Citizen, Collector, or Admin)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    # Short summary title of the notification
    title = models.CharField(max_length=255)
    # Detailed message or notification body content
    message = models.TextField()
    # Categorization field based on the Types choice enum above
    notification_type = models.CharField(
        max_length=20,
        choices=Types.choices,
        default=Types.SYSTEM,
    )
    # Boolean flag indicating whether the user has viewed the notification
    is_read = models.BooleanField(default=False)
    # Timestamp when the notification was generated (auto-set on creation)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Default sort ordering: newest notifications appear first
        ordering = ["-created_at"]

    def __str__(self):
        # Human-readable string representation for admin panel and debugging
        return f"{self.user} - {self.title} ({'Read' if self.is_read else 'Unread'})"
