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
