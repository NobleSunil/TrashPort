from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class DispatchBatch(models.Model):
    class Algorithms(models.TextChoices):
        NEAREST = "NEAREST", _("Nearest Collector")
        LEAST_BUSY = "LEAST_BUSY", _("Least Busy Collector")
        ZONE_BASED = "ZONE_BASED", _("Zone-Based Dispatch")

    algorithm_used = models.CharField(
        max_length=50,
        choices=Algorithms.choices,
        default=Algorithms.NEAREST,
    )
    assigned_count = models.IntegerField(default=0)
    unassigned_count = models.IntegerField(default=0)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatched_batches",
    )
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Batch #{self.id} ({self.algorithm_used}) - {self.assigned_count} assigned"
