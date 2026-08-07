from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses"
    )
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.is_default:
            # Mark all other addresses of this user as not default
            Address.objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.address_line1}, {self.city} ({self.user.email})"


class WasteCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Waste Categories"

    def __str__(self):
        return f"{self.name} (${self.price_per_kg}/kg)"


class PickupRequest(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PAID = "PAID", "Paid"

    citizen = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pickup_requests"
    )
    collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="assigned_pickups"
    )
    address = models.ForeignKey(Address, on_delete=models.PROTECT)
    category = models.ForeignKey(WasteCategory, on_delete=models.PROTECT)
    quantity_estimate = models.CharField(
        max_length=100,
        help_text="Estimated weight or volume (e.g. 5kg, 2 bags)"
    )
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual collected weight in kg"
    )
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Calculated cost of collection"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID
    )
    schedule_date = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING
    )
    feedback_rating = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    feedback_comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pickup #{self.id} ({self.status}) for {self.citizen.email}"


class Complaint(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RESOLVED = "RESOLVED", "Resolved"

    citizen = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="complaints"
    )
    pickup_request = models.ForeignKey(
        PickupRequest,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="complaints"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Complaint #{self.id}: {self.title} ({self.status})"
