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
    max_weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(0.01)],
        help_text="Maximum allowed weight in kg for user bookings (configurable by admin, default 100 kg)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CollectorPayoutSetting(models.Model):
    """
    Configurable parameters for collector payment calculations managed by Administrators.
    Allows adjusting:
    - Minimum base payout amount (default Rs. 25.00)
    - Rate per kilometer (default Rs. 2.00/km)
    - Extra weight commission percentage (default 20.00%)
    """
    base_min_payout = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=25.00,
        validators=[MinValueValidator(0.00)],
        help_text="Minimum guaranteed payout for a completed collection (Rs.)"
    )
    rate_per_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=2.00,
        validators=[MinValueValidator(0.00)],
        help_text="Amount paid per kilometer travelled (Rs./km)"
    )
    extra_weight_commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.00,
        validators=[MinValueValidator(0.00), MaxValueValidator(100.00)],
        help_text="Percentage commission granted to collector on excess weight surcharges (%)"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Collector Payout Setting"
        verbose_name_plural = "Collector Payout Settings"

    def __str__(self):
        return f"Payout Rules: Base Rs. {self.base_min_payout}, Rs. {self.rate_per_km}/km, {self.extra_weight_commission_percent}% excess commission"

    @classmethod
    def get_settings(cls):
        """Returns the active settings instance, creating default if not existing."""
        settings_obj = cls.objects.first()
        if not settings_obj:
            settings_obj = cls.objects.create(
                base_min_payout=Decimal("25.00"),
                rate_per_km=Decimal("2.00"),
                extra_weight_commission_percent=Decimal("20.00")
            )
        return settings_obj



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
        help_text="Earnings calculated for collector: Rs. 25 base min + Rs. 2.00/km + 20% commission on extra weight"
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
    cancellation_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason provided by user upon cancellation"
    )
    cancelled_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when pickup was cancelled"
    )
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
        # Default Kerala fallback: 9.9312 (Kochi/Central Kerala)
        if self.latitude is not None and abs(float(self.latitude) - 9.9312) > 0.0001:
            return float(self.latitude)
        if self.address and self.address.latitude is not None:
            return float(self.address.latitude)
        return float(self.latitude) if self.latitude is not None else 9.9312

    @property
    def effective_longitude(self) -> float:
        # Default Kerala fallback: 76.2673 (Kochi/Central Kerala)
        if self.longitude is not None and abs(float(self.longitude) - 76.2673) > 0.0001:
            return float(self.longitude)
        if self.address and self.address.longitude is not None:
            return float(self.address.longitude)
        return float(self.longitude) if self.longitude is not None else 76.2673

    def calculate_collector_earnings(self) -> Decimal:
        """
        Calculates collector earnings dynamically based on Admin Collector Payout Settings:
        - base_min_payout (guaranteed base minimum)
        - rate_per_km (rate per kilometer)
        - extra_weight_commission_percent (commission on excess weight surcharges)
        """
        settings_obj = CollectorPayoutSetting.get_settings()
        base_min = Decimal(str(settings_obj.base_min_payout))
        rate_km = Decimal(str(settings_obj.rate_per_km))
        comm_pct = Decimal(str(settings_obj.extra_weight_commission_percent)) / Decimal("100.00")

        distance_part = Decimal(str(self.distance_km or 0)) * rate_km
        extra_commission = Decimal(str(self.extra_fee or 0)) * comm_pct
        total = base_min + distance_part + extra_commission
        return round(max(base_min, total), 2)

    def save(self, *args, **kwargs):
        is_new = not self.pk
        if self.address:
            # Sync coordinates: prioritize exact address coordinates if self.latitude is missing or default
            address_has_coords = self.address.latitude is not None and self.address.longitude is not None
            self_has_default_coords = (
                self.latitude is None or 
                abs(float(self.latitude or 0) - 9.9312) < 0.0001 or
                abs(float(self.latitude or 0) - 12.9716) < 0.0001
            )
            if address_has_coords and self_has_default_coords:
                self.latitude = self.address.latitude
                self.longitude = self.address.longitude
            elif not address_has_coords and self.latitude is not None and abs(float(self.latitude) - 9.9312) > 0.0001 and abs(float(self.latitude) - 12.9716) > 0.0001:
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

            # Calculate collection fee based on category rate
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


class AnonymousFeedback(models.Model):
    """
    Public / Citizen anonymous feedback submitted directly to system administrators.
    Allows citizens or visitors to report issues, suggestions, or feedback without revealing identity.
    """
    class CategoryChoices(models.TextChoices):
        SUGGESTION = "SUGGESTION", "Suggestion / Improvement"
        COLLECTION_ISSUE = "COLLECTION_ISSUE", "Collection / Service Issue"
        WEBSITE_BUG = "WEBSITE_BUG", "Website / App Bug"
        GENERAL = "GENERAL", "General Feedback"

    category = models.CharField(
        max_length=50,
        choices=CategoryChoices.choices,
        default=CategoryChoices.GENERAL,
        help_text="Feedback category"
    )
    subject = models.CharField(max_length=200, blank=True, null=True)
    message = models.TextField(help_text="Anonymous feedback message sent to admin")
    is_reviewed = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Anonymous Feedback"
        verbose_name_plural = "Anonymous Feedbacks"

    def __str__(self):
        return f"Anonymous Feedback #{self.id} [{self.category}] - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

