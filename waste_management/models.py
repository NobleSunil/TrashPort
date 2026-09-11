from decimal import Decimal
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
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    is_hidden = models.BooleanField(
        default=False,
        help_text="Soft-delete flag — hidden from citizen view but retained in the database."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.is_default:
            # Mark all other visible addresses of this user as not default
            Address.objects.filter(user=self.user, is_hidden=False).exclude(pk=self.pk).update(is_default=False)
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
        return f"{self.name} (Rs. {self.price})"


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
        PENDING = "PENDING", "Pending"
        AWAITING_PAYMENT = "AWAITING_PAYMENT", "Awaiting Payment"
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
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
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
    actual_weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual measured weight verified by collector"
    )
    extra_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Additional surcharge for excess weight (2x rate)"
    )
    distance_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=5.00,
        help_text="Estimated collection distance in kilometers"
    )
    collector_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Earnings calculated for collector: 35% fee + Rs. 0.25/km"
    )
    is_weight_verified = models.BooleanField(
        default=False,
        help_text="Set to True once collector measures and verifies waste weight"
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
    user_pickup_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Sequential pickup number for this user starting from 1"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def display_id(self) -> int:
        return self.user_pickup_number or self.id

    @property
    def effective_latitude(self) -> float:
        if self.latitude is not None and abs(float(self.latitude) - 12.9716) > 0.0001:
            return float(self.latitude)
        if self.address and self.address.latitude is not None:
            return float(self.address.latitude)
        return float(self.latitude) if self.latitude is not None else 12.9716

    @property
    def effective_longitude(self) -> float:
        if self.longitude is not None and abs(float(self.longitude) - 77.5946) > 0.0001:
            return float(self.longitude)
        if self.address and self.address.longitude is not None:
            return float(self.address.longitude)
        return float(self.longitude) if self.longitude is not None else 77.5946

    def calculate_collector_earnings(self) -> Decimal:
        """
        Calculates collector earnings: 35% of total charge fee + Rs. 0.25 per km.
        """
        fee_part = Decimal(str(self.fee or 0)) * Decimal("0.35")
        distance_part = Decimal(str(self.distance_km or 0)) * Decimal("0.25")
        return round(fee_part + distance_part, 2)

    def save(self, *args, **kwargs):
        is_new = not self.pk
        if self.address:
            # Sync coordinates: prioritize exact address coordinates if self.latitude is missing or default
            address_has_coords = self.address.latitude is not None and self.address.longitude is not None
            self_has_default_coords = (
                self.latitude is None or 
                abs(float(self.latitude or 0) - 12.9716) < 0.0001
            )
            if address_has_coords and self_has_default_coords:
                self.latitude = self.address.latitude
                self.longitude = self.address.longitude
            elif not address_has_coords and self.latitude is not None and abs(float(self.latitude) - 12.9716) > 0.0001:
                # Update saved address record if it lacked coordinates
                self.address.latitude = self.latitude
                self.address.longitude = self.longitude
                self.address.save(update_fields=["latitude", "longitude"])
        if is_new:
            # Assign sequential user pickup number starting from 1 for each citizen
            if not self.user_pickup_number and self.citizen_id:
                max_num = (
                    PickupRequest.objects.filter(citizen_id=self.citizen_id)
                    .aggregate(models.Max("user_pickup_number"))["user_pickup_number__max"]
                )
                if max_num:
                    self.user_pickup_number = max_num + 1
                else:
                    count = PickupRequest.objects.filter(citizen_id=self.citizen_id).count()
                    self.user_pickup_number = count + 1

            # Check subscription
            has_sub = Subscription.objects.filter(user=self.citizen, is_active=True).exists()
            if has_sub:
                self.fee = Decimal("0.00")
            else:
                self.fee = Decimal(str(self.weight_kg)) * Decimal(str(self.category.fee_per_kg))
            
            self.points_earned = int(Decimal(str(self.weight_kg)) * Decimal(str(self.category.points_per_kg)))
            
            if self.fee > 0:
                self.status = self.StatusChoices.AWAITING_PAYMENT
                self.is_paid = False
            else:
                self.status = self.StatusChoices.PENDING
                self.is_paid = True
            
            self.collector_earnings = self.calculate_collector_earnings()
        else:
            # If actual weight was provided and verified, calculate extra weight penalty (2x rate)
            if self.actual_weight_kg is not None and self.actual_weight_kg > self.weight_kg:
                extra_weight = Decimal(str(self.actual_weight_kg)) - Decimal(str(self.weight_kg))
                # 2x of regular category rate per kg for extra weight
                self.extra_fee = extra_weight * Decimal(str(self.category.fee_per_kg)) * Decimal("2.00")
                base_fee = Decimal(str(self.weight_kg)) * Decimal(str(self.category.fee_per_kg))
                self.fee = base_fee + self.extra_fee
            
            # Recalculate collector earnings based on final total fee and distance
            self.collector_earnings = self.calculate_collector_earnings()

            # Check status and collector transitions
            orig = PickupRequest.objects.get(pk=self.pk)
            
            # Check if collector was assigned
            if orig.collector != self.collector and self.collector is not None:
                from .notifications import send_pickup_assigned_notification
                send_pickup_assigned_notification(self, collector=self.collector)

            # Check if status has transitioned to CANCELLED
            if orig.status != self.StatusChoices.CANCELLED and self.status == self.StatusChoices.CANCELLED:
                from .notifications import send_pickup_cancelled_notification
                send_pickup_cancelled_notification(self)

            # Check if status has transitioned to COMPLETED
            if orig.status != self.StatusChoices.COMPLETED and self.status == self.StatusChoices.COMPLETED:
                # 1. Credit Citizen Recycling Points & Log to Wallet History
                if self.points_earned > 0:
                    from trashport.payments.services import WalletService
                    cat_name = self.category.name if self.category else "Waste"
                    WalletService.adjust_points(
                        user=self.citizen,
                        points_delta=self.points_earned,
                        reason=f"Recycling reward: {self.weight_kg}kg {cat_name} (Pickup #{self.display_id})"
                    )
                else:
                    self.citizen.wallet_points += self.points_earned
                    self.citizen.save(update_fields=["wallet_points"])

                # 2. Credit Collector Wallet Earnings: 35% fee + Rs. 0.25/km
                if self.collector:
                    current_balance = Decimal(str(self.collector.wallet_balance or "0.00"))
                    self.collector.wallet_balance = current_balance + self.collector_earnings
                    self.collector.save()

        super().save(*args, **kwargs)

        if is_new:
            # Send notification to citizen that pickup request has been booked/confirmed
            from .notifications import send_pickup_requested_notification
            send_pickup_requested_notification(self)

    def __str__(self):
        return f"Pickup #{self.display_id} ({self.status}) for {self.citizen.email}"


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
