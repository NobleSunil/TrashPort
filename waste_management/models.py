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


class SubscriptionTier(models.Model):
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (${self.price})"


class Subscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    tier = models.ForeignKey(SubscriptionTier, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.tier.name}"


class WasteCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    fee_per_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        help_text="Collection fee per kg"
    )
    points_per_kg = models.IntegerField(
        default=0,
        help_text="Points rewarded per kg for recycling valuable metals (Copper, Aluminum, Steel)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Waste Categories"

    def __str__(self):
        return self.name


class PickupRequest(models.Model):
    class StatusChoices(models.TextChoices):
        AWAITING_PAYMENT = "AWAITING_PAYMENT", "Awaiting Payment"
        PENDING = "PENDING", "Pending"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

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
    weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=1.00,
        validators=[MinValueValidator(0.01)],
        help_text="Estimated weight in kg"
    )
    quantity_estimate = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Additional quantity estimate (e.g. 2 bags, 3 boxes)"
    )
    fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Calculated collection fee"
    )
    points_earned = models.IntegerField(
        default=0,
        help_text="Points earned for recycling valuable metals"
    )
    is_paid = models.BooleanField(
        default=False
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

    def save(self, *args, **kwargs):
        is_new = not self.pk
        if is_new:
            # Check subscription
            has_sub = Subscription.objects.filter(user=self.citizen, is_active=True).exists()
            if has_sub:
                self.fee = 0.00
            else:
                self.fee = self.weight_kg * self.category.fee_per_kg
            
            self.points_earned = int(self.weight_kg * self.category.points_per_kg)
            
            if self.fee > 0:
                self.status = self.StatusChoices.AWAITING_PAYMENT
                self.is_paid = False
            else:
                self.status = self.StatusChoices.PENDING
                self.is_paid = True
        else:
            # Check if status has transitioned to COMPLETED
            orig = PickupRequest.objects.get(pk=self.pk)
            if orig.status != self.StatusChoices.COMPLETED and self.status == self.StatusChoices.COMPLETED:
                self.citizen.wallet_points += self.points_earned
                self.citizen.save()

        super().save(*args, **kwargs)

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
