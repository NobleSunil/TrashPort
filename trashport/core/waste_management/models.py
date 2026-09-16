"""
waste_management/models.py — Core Domain Models
=================================================

PURPOSE:
  This is the heart of the TrashPort data layer. It defines every database
  table related to the waste collection workflow. All other apps (citizens,
  collectors, admins) read from and write to these models.

CONNECTION MAP (who uses what):
  - trashport/citizens/views.py       â†’ Address, PickupRequest, Complaint, WasteCategory
  - trashport/collectors/views.py     â†’ PickupRequest, CollectorPayoutSetting
  - trashport/admins/views.py         â†’ All models
  - waste_management/serializers.py   â†’ All models (for DRF JSON API)
  - waste_management/views.py         â†’ All models (via DRF ViewSets)
  - waste_management/notifications.py â†’ PickupRequest (triggers email/in-app alerts)
  - trashport/payments/services.py    â†’ PickupRequest (marks is_paid, updates status)

DATA FLOW OVERVIEW:
  1. Citizen books pickup â†’ PickupRequest.save() calculates fee and sets status
  2. Fee > 0 â†’ status = AWAITING_PAYMENT â†’ citizen pays â†’ status = PENDING
  3. Fee = 0 â†’ status = PENDING immediately
  4. Collector claims â†’ status = ASSIGNED
  5. Collector marks in transit â†’ status = IN_TRANSIT
  6. Collector completes (with actual weight) â†’ status = COMPLETED â†’
       • Extra fee calculated if actual_weight > estimated weight
       • Collector wallet credited with collector_earnings
       • Citizen wallet credited with recycling points (if category gives points)
       • Email/in-app notifications sent

IMPACT WARNINGS:
  - Modifying PickupRequest.save() affects the ENTIRE pickup lifecycle.
  - Modifying WasteCategory.fee_per_kg affects all new pickup fee calculations.
  - CollectorPayoutSetting.get_settings() is called at EVERY earnings calculation.
    If the database has no settings row, defaults are auto-created.
  - The Address.save() override auto-clears the 'is_default' flag on all
    other addresses when a new default is set.
"""

from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


# ==============================================================================
# Address Model
# ==============================================================================
# Stores citizen pickup addresses. Supports multiple addresses per user with
# one 'default' address. Uses soft-delete (is_hidden) so deleted addresses
# remain in the database for historical pickup record integrity.
#
# CONNECTION: Used by citizens to select a pickup location.
#             PickupRequest.address â†’ FK to this model.
#             GPS coordinates (latitude/longitude) are used by the maps system
#             (trashport/maps/services.py) for distance calculations.
#
# IMPACT: Deleting the Address table breaks pickup history and GPS routing.
# ==============================================================================

class Address(models.Model):
    """
    Citizen's saved pickup address.

    Fields:
      - user         : The citizen who owns this address.
      - address_line1: Primary street address.
      - address_line2: Optional secondary line (apartment, suite, etc.).
      - city, state  : Location identifiers used for region-based reporting.
      - postal_code  : Used for address validation and display.
      - latitude / longitude : GPS coordinates synced to/from pickup requests.
                               Used for haversine distance calculations in maps.
      - is_default   : True for the citizen's primary address. Only one address
                       can be default at a time (enforced in save() override).
      - is_hidden    : Soft-delete flag. Hidden from citizen UI but kept in DB
                       so historical pickups still have a valid address reference.

    save() override behaviour:
      When is_default=True is set on save(), ALL other non-hidden addresses
      of the same user are automatically set to is_default=False. This ensures
      only one default address exists at any time.
    """

    # The citizen (user) who owns this address
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

    # GPS coordinates — populated from citizen's map pin or device location.
    # These flow INTO PickupRequest when a pickup is created at this address.
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Control flags
    is_default = models.BooleanField(default=False)
    is_hidden = models.BooleanField(
        default=False,
        help_text="Soft-delete flag — hidden from citizen view but retained in the database."
    )

    # Auto-managed timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        Override: When this address is set as default, automatically
        demote all other visible (non-hidden) addresses of the same user.

        IMPACT: If you bypass save() with bulk_update(), this default-switching
        logic will NOT run. Always use instance.save() for default changes.
        """
        if self.is_default:
            # Clear the is_default flag on all other visible addresses for this user
            Address.objects.filter(user=self.user, is_hidden=False).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.address_line1}, {self.city} ({self.user.email})"


# ==============================================================================
# WasteCategory Model
# ==============================================================================
# Defines the types of waste the system can handle (e.g., E-Waste, Metal,
# Organic). Admins configure these in the admin panel. Each category has:
#   - A collection fee rate (Rs. per kg) charged to citizens
#   - A points reward rate (points per kg) credited to citizens as recycling reward
#   - A maximum weight cap per booking
#
# CONNECTION: PickupRequest.category â†’ FK to WasteCategory.
#             Citizens see all categories in the pickup booking form.
#             Admins manage categories via waste_management/manage/categories/.
#
# IMPACT: Changing fee_per_kg affects ALL FUTURE pickup fee calculations.
#         Changing points_per_kg affects ALL FUTURE recycling point rewards.
#         Existing (already-created) PickupRequests are NOT retroactively updated.
# ==============================================================================

class WasteCategory(models.Model):
    """
    A waste classification type with collection pricing and recycling incentives.

    Fields:
      - name        : Unique category name shown in the citizen booking form.
      - description : Optional display text for UI.
      - fee_per_kg  : Collection fee per kilogram charged to the citizen.
                      Set to 0.00 for free-to-collect categories (e.g., recyclables
                      that generate revenue for the platform).
      - points_per_kg: Green wallet points awarded per kg recycled.
                      Set to 0 for categories with no recycling value.
      - max_weight_kg: Maximum booking weight for this category. Prevents citizens
                      from booking unrealistically large quantities.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    # Fee charged to citizen: pickup.fee = weight_kg × fee_per_kg
    fee_per_kg = models.DecimalField(
        max_digits=6, decimal_places=2, default=0.00,
        help_text="Collection fee per kg"
    )

    # Recycling reward points: pickup.points_earned = weight_kg × points_per_kg
    points_per_kg = models.IntegerField(
        default=0,
        help_text="Points rewarded per kg for recycling valuable metals (Copper, Aluminum, Steel)"
    )

    # Maximum weight limit per booking (configurable by admin)
    max_weight_kg = models.DecimalField(
        max_digits=6, decimal_places=2, default=100.00,
        validators=[MinValueValidator(0.01)],
        help_text="Maximum allowed weight in kg for user bookings (configurable by admin, default 100 kg)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# ==============================================================================
# CollectorPayoutSetting Model
# ==============================================================================
# A singleton-style settings table that Admins use to configure the formula
# for calculating collector earnings per completed pickup.
#
# FORMULA:
#   earnings = max(base_min_payout,
#                  base_min_payout + (distance_km × rate_per_km)
#                                  + (extra_fee × extra_weight_commission_percent / 100))
#
# CONNECTION: PickupRequest.calculate_collector_earnings() calls get_settings().
#             Admins update these values via waste_management/manage/payout-settings/.
#             The CollectorPayoutSettingUpdateView in admins/views.py handles saves.
#
# IMPACT: Changing these values affects earnings for ALL FUTURE completed pickups.
#         Already-completed pickups have their earnings stored in collector_earnings
#         and are NOT retroactively recalculated.
# ==============================================================================

class CollectorPayoutSetting(models.Model):
    """
    Configurable payout formula parameters for collector earnings.
    Only ONE row should ever exist in this table (use get_settings()).

    Fields:
      - base_min_payout                : Guaranteed minimum payout per job (default Rs. 25).
      - rate_per_km                    : Extra pay per km of pickup distance (default Rs. 2/km).
      - extra_weight_commission_percent: % of excess weight penalty given to collector (default 20%).
    """
    base_min_payout = models.DecimalField(
        max_digits=8, decimal_places=2, default=25.00,
        validators=[MinValueValidator(0.00)],
        help_text="Minimum guaranteed payout for a completed collection (Rs.)"
    )
    rate_per_km = models.DecimalField(
        max_digits=6, decimal_places=2, default=2.00,
        validators=[MinValueValidator(0.00)],
        help_text="Amount paid per kilometer travelled (Rs./km)"
    )
    extra_weight_commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=20.00,
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
        """
        Returns the active payout settings row, creating it with defaults if
        it doesn't exist yet.

        Always use this method — never call .objects.first() directly, as that
        would return None on a fresh database and cause AttributeError crashes.

        IMPACT: The first call on a fresh DB creates a default row automatically.
        """
        settings_obj = cls.objects.first()
        if not settings_obj:
            settings_obj = cls.objects.create(
                base_min_payout=Decimal("25.00"),
                rate_per_km=Decimal("2.00"),
                extra_weight_commission_percent=Decimal("20.00")
            )
        return settings_obj


# ==============================================================================
# PickupRequest Model
# ==============================================================================
# The central transactional model. Represents a single waste collection job,
# from citizen booking through payment, collector assignment, and completion.
#
# LIFECYCLE (status flow):
#   NEW â†’ AWAITING_PAYMENT (if fee > 0) â†’ PENDING â†’ ASSIGNED â†’ IN_TRANSIT â†’ COMPLETED
#      ↘ PENDING (if fee = 0, auto-paid)                                    ↘ CANCELLED
#
# KEY AUTOMATED BEHAVIORS (in save() override):
#   On CREATE:
#     • Assigns sequential user_pickup_number (per citizen, starts from 1)
#     • Calculates fee = weight_kg × category.fee_per_kg
#     • Calculates points_earned = weight_kg × category.points_per_kg
#     • Sets status: AWAITING_PAYMENT (fee > 0) or PENDING (fee = 0)
#     • Calculates initial collector_earnings estimate
#     • Syncs GPS coordinates between PickupRequest and its Address
#     • Sends "pickup requested" notification to citizen
#   On UPDATE:
#     • Recalculates extra_fee if actual_weight > estimated weight (2× rate)
#     • Recalculates collector_earnings based on final distance and extra_fee
#     • On COMPLETED transition: credits citizen points + collector wallet balance
#     • On ASSIGNED transition: sends "collector assigned" notification
#     • On CANCELLED transition: sends "pickup cancelled" notification
#
# CONNECTIONS:
#   - trashport/citizens/views.py  â†’ citizen creates, pays, cancels, rates pickups
#   - trashport/collectors/views.py â†’ collector claims, marks transit, completes pickups
#   - trashport/admins/views.py     â†’ admin assigns, cancels, views all pickups
#   - trashport/payments/services.py â†’ PaymentGatewayService._mark_pickup_paid()
#   - waste_management/notifications.py â†’ sends email/in-app alerts on transitions
#
# IMPACT:
#   - Changing fee calculation in save() affects all new bookings.
#   - Changing collector_earnings calculation affects all collector payouts.
#   - Changing GPS sync logic affects map display and distance calculations.
# ==============================================================================

class PickupRequest(models.Model):
    """
    Represents a single waste collection request from booking to completion.

    Status Choices:
      PENDING          : Created and ready for collector to claim.
      AWAITING_PAYMENT : Created but fee unpaid — waiting for citizen payment.
      ASSIGNED         : A collector has claimed this job.
      IN_TRANSIT       : Collector is on the way to pick up the waste.
      COMPLETED        : Waste collected, weight verified, earnings credited.
      CANCELLED        : Request cancelled by citizen or admin.
    """

    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", "Pending"
        AWAITING_PAYMENT = "AWAITING_PAYMENT", "Awaiting Payment"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    # -------------------------------------------------------------------------
    # Relationships — who is involved in this pickup?
    # -------------------------------------------------------------------------
    citizen = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pickup_requests"     # citizen.pickup_requests.all()
    )
    collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,             # null = not yet assigned
        related_name="assigned_pickups"    # collector.assigned_pickups.all()
    )
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True
    )
    category = models.ForeignKey(
        WasteCategory, on_delete=models.PROTECT  # PROTECT prevents deletion of a category that has pickups
    )

    # -------------------------------------------------------------------------
    # Location — GPS coordinates
    # latitude/longitude can come from:
    #   1. The citizen's map pin (overrides address coordinates)
    #   2. The linked Address object (synced in save())
    #   3. Default Kerala fallback (9.9312, 76.2673) if neither is available
    #
    # Use effective_latitude / effective_longitude properties for display/maps.
    # NEVER use raw latitude/longitude directly — they may be the Kerala default.
    # -------------------------------------------------------------------------
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # -------------------------------------------------------------------------
    # Weight fields
    #   weight_kg      : Citizen's estimated weight at booking time
    #   actual_weight_kg: Collector-verified weight at completion time
    #   is_weight_verified: True once collector enters actual weight
    #
    # If actual_weight_kg > weight_kg:
    #   extra_fee = (actual_weight_kg - weight_kg) × fee_per_kg × 2 (2x penalty)
    # -------------------------------------------------------------------------
    weight_kg = models.DecimalField(
        max_digits=6, decimal_places=2, default=1.00,
        validators=[MinValueValidator(0.01)],
        help_text="Estimated weight in kg"
    )
    quantity_estimate = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Additional quantity estimate (e.g. 2 bags, 3 boxes)"
    )
    actual_weight_kg = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Actual measured weight verified by collector"
    )
    is_weight_verified = models.BooleanField(
        default=False,
        help_text="Set to True once collector measures and verifies waste weight"
    )

    # -------------------------------------------------------------------------
    # Financial fields
    #   fee             : Amount citizen owes (weight_kg × fee_per_kg + extra_fee)
    #   extra_fee       : Surcharge for excess weight (2x rate per kg over estimate)
    #   collector_earnings: What collector is paid on completion
    #   points_earned   : Green wallet points awarded to citizen on completion
    #
    # IMPACT: These are calculated automatically in save(). Do NOT set them
    #         manually in views — the save() hook will overwrite them.
    # -------------------------------------------------------------------------
    fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Calculated collection fee"
    )
    extra_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Additional surcharge for excess weight (2x rate)"
    )
    distance_km = models.DecimalField(
        max_digits=6, decimal_places=2, default=5.00,
        help_text="Estimated collection distance in kilometers"
    )
    collector_earnings = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Earnings calculated for collector: base_min + rate/km + extra_weight_commission"
    )
    points_earned = models.IntegerField(
        default=0,
        help_text="Points earned for recycling valuable metals"
    )

    # -------------------------------------------------------------------------
    # Payment & Status
    # -------------------------------------------------------------------------
    is_paid = models.BooleanField(default=False)
    schedule_date = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices,
        default=StatusChoices.PENDING
    )

    # -------------------------------------------------------------------------
    # Post-completion fields
    # -------------------------------------------------------------------------
    feedback_rating = models.IntegerField(
        blank=True, null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    feedback_comments = models.TextField(blank=True, null=True)
    cancellation_reason = models.TextField(
        blank=True, null=True,
        help_text="Reason provided by user upon cancellation"
    )
    cancelled_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Timestamp when pickup was cancelled"
    )

    # Sequential pickup number per citizen (starts at 1 for each citizen)
    # Used for user-facing display ID (e.g., "Pickup #3" instead of DB ID)
    user_pickup_number = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Sequential pickup number for this user starting from 1"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def display_id(self) -> int:
        """
        User-facing pickup number. Uses user_pickup_number (e.g., #3)
        instead of the raw database ID. Falls back to database ID if
        user_pickup_number was not set (legacy records).
        """
        return self.user_pickup_number or self.id

    @property
    def effective_latitude(self) -> float:
        """
        Returns the best available latitude for map display.
        Priority: pickup-specific GPS pin â†’ linked address GPS â†’ Kerala default.

        IMPACT: If you change the Kerala default coordinates (9.9312), also
        update the matching check in save() and in collectors/views.py.
        """
        # Use pickup's own coordinates if they differ from the Kerala default
        if self.latitude is not None and abs(float(self.latitude) - 9.9312) > 0.0001:
            return float(self.latitude)
        # Fall back to address coordinates
        if self.address and self.address.latitude is not None:
            return float(self.address.latitude)
        return float(self.latitude) if self.latitude is not None else 9.9312

    @property
    def effective_longitude(self) -> float:
        """
        Returns the best available longitude for map display.
        Priority: pickup-specific GPS pin â†’ linked address GPS â†’ Kerala default.
        """
        if self.longitude is not None and abs(float(self.longitude) - 76.2673) > 0.0001:
            return float(self.longitude)
        if self.address and self.address.longitude is not None:
            return float(self.address.longitude)
        return float(self.longitude) if self.longitude is not None else 76.2673

    def calculate_collector_earnings(self) -> Decimal:
        """
        Calculates what the collector earns for completing this pickup.

        FORMULA (using current CollectorPayoutSetting values):
          earnings = base_min_payout
                   + (distance_km × rate_per_km)
                   + (extra_fee × extra_weight_commission_percent / 100)

          Result is clamped to at least base_min_payout.

        CONNECTION: Called in save() on both CREATE and UPDATE.
                    Also called by collectors/views.py for preview display.
        IMPACT: To change payout formula, modify CollectorPayoutSetting or
                this method. Changing this method changes earnings for ALL
                future completions immediately.
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
        """
        Override: The core of the PickupRequest business logic.

        =====================================================================
        ON CREATE (is_new = True):
        =====================================================================
        1. GPS SYNC: If the linked address has GPS but the pickup doesn't,
           copy the address GPS to the pickup. If the pickup has GPS but the
           address doesn't, copy the pickup GPS to the address record.

        2. SEQUENTIAL ID: Assign user_pickup_number as the next number in
           sequence for this citizen (1, 2, 3, ... per citizen).

        3. FEE CALCULATION: fee = weight_kg × category.fee_per_kg

        4. POINTS CALCULATION: points_earned = weight_kg × category.points_per_kg

        5. STATUS & PAYMENT:
           - fee > 0 â†’ status = AWAITING_PAYMENT, is_paid = False
           - fee = 0 â†’ status = PENDING, is_paid = True (auto-approved)

        6. INITIAL EARNINGS ESTIMATE: collector_earnings = calculate_collector_earnings()

        7. NOTIFICATION: Sends pickup confirmation notification to citizen.

        =====================================================================
        ON UPDATE (is_new = False):
        =====================================================================
        1. EXTRA WEIGHT: If actual_weight_kg > weight_kg:
             extra_fee = (actual - estimated) × fee_per_kg × 2  (2x penalty rate)
             fee = (weight_kg × fee_per_kg) + extra_fee

        2. RECALCULATE EARNINGS: collector_earnings = calculate_collector_earnings()
           (now includes the extra_fee commission)

        3. COLLECTOR ASSIGNED: If collector changed â†’ send assignment notification.

        4. CANCELLED: If status changed to CANCELLED â†’ send cancellation notification.

        5. COMPLETED: If status changed to COMPLETED:
             a. Credit citizen recycling points via WalletService.adjust_points()
             b. Credit collector wallet_balance by collector_earnings amount
             c. (The collector wallet is updated directly on user.wallet_balance)

        IMPACT WARNING:
          - This method does multiple DB reads (checking orig = PickupRequest.objects.get(pk=self.pk))
            on every UPDATE. This is intentional for change detection but means
            every pickup.save() on an existing record costs 2 DB queries minimum.
          - NEVER call pickup.save() in a tight loop without considering this cost.
        """
        is_new = not self.pk

        # ----- GPS coordinate sync between PickupRequest and its Address -----
        if self.address:
            address_has_coords = self.address.latitude is not None and self.address.longitude is not None
            # Detect if the pickup's lat/lng is a "default" placeholder (Kerala coords or None)
            self_has_default_coords = (
                self.latitude is None or
                abs(float(self.latitude or 0) - 9.9312) < 0.0001 or
                abs(float(self.latitude or 0) - 12.9716) < 0.0001  # Bangalore fallback
            )
            if address_has_coords and self_has_default_coords:
                # Address has real GPS â†’ copy to pickup
                self.latitude = self.address.latitude
                self.longitude = self.address.longitude
            elif not address_has_coords and self.latitude is not None and abs(float(self.latitude) - 9.9312) > 0.0001 and abs(float(self.latitude) - 12.9716) > 0.0001:
                # Pickup has real GPS but address doesn't â†’ update the address record
                self.address.latitude = self.latitude
                self.address.longitude = self.longitude
                self.address.save(update_fields=["latitude", "longitude"])

        if is_new:
            # ----- Sequential pickup number assignment -----
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

            # ----- Fee and points calculation -----
            self.fee = Decimal(str(self.weight_kg)) * Decimal(str(self.category.fee_per_kg))
            self.points_earned = int(Decimal(str(self.weight_kg)) * Decimal(str(self.category.points_per_kg)))

            # ----- Payment status determination -----
            if self.fee > 0:
                # Citizen must pay before the pickup enters the active queue
                self.status = self.StatusChoices.AWAITING_PAYMENT
                self.is_paid = False
            else:
                # Free pickup (e.g., recyclables) — immediately PENDING for collectors to claim
                self.status = self.StatusChoices.PENDING
                self.is_paid = True

            # ----- Initial earnings estimate -----
            self.collector_earnings = self.calculate_collector_earnings()

        else:
            # ----- UPDATE path: extra weight penalty calculation -----
            if self.actual_weight_kg is not None and self.actual_weight_kg > self.weight_kg:
                extra_weight = Decimal(str(self.actual_weight_kg)) - Decimal(str(self.weight_kg))
                # 2x rate applied to excess weight as a penalty surcharge
                self.extra_fee = extra_weight * Decimal(str(self.category.fee_per_kg)) * Decimal("2.00")
                base_fee = Decimal(str(self.weight_kg)) * Decimal(str(self.category.fee_per_kg))
                self.fee = base_fee + self.extra_fee

            # ----- Recalculate collector earnings with final extra_fee -----
            self.collector_earnings = self.calculate_collector_earnings()

            # ----- Change detection: read original record to compare -----
            orig = PickupRequest.objects.get(pk=self.pk)

            # --- TRIGGER: Collector newly assigned ---
            if orig.collector != self.collector and self.collector is not None:
                from .notifications import send_pickup_assigned_notification
                send_pickup_assigned_notification(self, collector=self.collector)

            # --- TRIGGER: Status changed to CANCELLED ---
            if orig.status != self.StatusChoices.CANCELLED and self.status == self.StatusChoices.CANCELLED:
                from .notifications import send_pickup_cancelled_notification
                send_pickup_cancelled_notification(self)

            # --- TRIGGER: Status changed to COMPLETED ---
            if orig.status != self.StatusChoices.COMPLETED and self.status == self.StatusChoices.COMPLETED:
                # 1. Credit citizen recycling points (only if category awards points)
                if self.points_earned > 0:
                    from trashport.services.payments.services import WalletService
                    cat_name = self.category.name if self.category else "Waste"
                    WalletService.adjust_points(
                        user=self.citizen,
                        points_delta=self.points_earned,
                        reason=f"Recycling reward: {self.weight_kg}kg {cat_name} (Pickup #{self.display_id})"
                    )
                else:
                    # Even if points_earned = 0, ensure wallet_points field is consistent
                    # (No-op when points_earned = 0, but keeps the field in sync)
                    self.citizen.wallet_points += self.points_earned
                    self.citizen.save(update_fields=["wallet_points"])

                # 2. Credit collector wallet with their earnings
                if self.collector:
                    current_balance = Decimal(str(self.collector.wallet_balance or "0.00"))
                    self.collector.wallet_balance = current_balance + self.collector_earnings
                    self.collector.save()

        # ----- Persist to database -----
        super().save(*args, **kwargs)

        # ----- Post-save: Send booking confirmation notification -----
        if is_new:
            # Must be after super().save() so pickup.pk exists for the notification
            from .notifications import send_pickup_requested_notification
            send_pickup_requested_notification(self)

    def __str__(self):
        return f"Pickup #{self.display_id} ({self.status}) for {self.citizen.email}"


# ==============================================================================
# Complaint Model
# ==============================================================================
# Allows citizens to file formal complaints against pickup requests.
# Admins review and resolve complaints from the admin dashboard.
#
# CONNECTION: Citizens create complaints via CitizenComplaintCreateView.
#             Admins view/resolve via AdminComplaintListView, AdminComplaintDetailView.
#             The complaint is optionally linked to a PickupRequest.
#
# IMPACT: Modifying StatusChoices affects complaint resolution workflow.
# ==============================================================================

class Complaint(models.Model):
    """
    A citizen's formal complaint, optionally linked to a PickupRequest.

    Statuses:
      PENDING  : Complaint filed, awaiting admin review.
      RESOLVED : Admin has reviewed and marked as resolved.
    """

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
        on_delete=models.SET_NULL,  # Complaint persists even if the pickup is deleted
        blank=True, null=True,
        related_name="complaints"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices,
        default=StatusChoices.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Complaint #{self.id}: {self.title} ({self.status})"


# ==============================================================================
# AnonymousFeedback Model
# ==============================================================================
# Allows any visitor or citizen (without login) to submit feedback, bug reports,
# or suggestions directly to the admin team. Designed for trust-building and
# issue discovery from non-authenticated users.
#
# CONNECTION: Submitted via SubmitAnonymousFeedbackView in citizens/views.py.
#             Admins view/manage via AdminAnonymousFeedbackListView in admins/views.py.
#             The submission endpoint is publicly accessible (no login required).
#
# IMPACT: No personal data is stored (anonymous by design).
#         Admins can mark feedback as reviewed or delete it.
# ==============================================================================

class AnonymousFeedback(models.Model):
    """
    Anonymous feedback submitted by visitors or citizens without requiring login.
    Used for suggestions, bug reports, and service issue reports.
    """

    class CategoryChoices(models.TextChoices):
        SUGGESTION = "SUGGESTION", "Suggestion / Improvement"
        COLLECTION_ISSUE = "COLLECTION_ISSUE", "Collection / Service Issue"
        WEBSITE_BUG = "WEBSITE_BUG", "Website / App Bug"
        GENERAL = "GENERAL", "General Feedback"

    category = models.CharField(
        max_length=50, choices=CategoryChoices.choices,
        default=CategoryChoices.GENERAL,
        help_text="Feedback category"
    )
    subject = models.CharField(max_length=200, blank=True, null=True)
    message = models.TextField(help_text="Anonymous feedback message sent to admin")
    is_reviewed = models.BooleanField(default=False)  # Admin marks as reviewed
    admin_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Anonymous Feedback"
        verbose_name_plural = "Anonymous Feedbacks"

    def __str__(self):
        return f"Anonymous Feedback #{self.id} [{self.category}] - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
