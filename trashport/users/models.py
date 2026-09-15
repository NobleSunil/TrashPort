"""
trashport/users/models.py — Custom User Model and Role System
==============================================================

PURPOSE:
  Defines the central User model that all three roles (CITIZEN, COLLECTOR, ADMIN)
  share. Uses Django's AbstractUser for authentication, extending it with
  role-specific fields grouped by purpose:
    - Role & Verification : role, is_verified, verification_status
    - Contact & Profile   : name, phone, profile_picture
    - Citizen Wallet      : wallet_points (recycling points, NOT cash)
    - Collector Wallet    : wallet_balance (cash earnings from completed pickups)

3-ROLE ARCHITECTURE:
  A single User table serves all three roles. The user.role field
  determines which dashboard, views, and capabilities a user has access to.

  CITIZEN  : Books pickups, pays fees, earns recycling points.
  COLLECTOR: Claims and completes pickup jobs, earns cash wallet_balance.
  ADMIN    : Manages users, categories, dispatches, and views reports.

CONNECTION MAP:
  - waste_management/views.py      → checks user.role to dispatch to correct view
  - waste_management/models.py     → PickupRequest.citizen, .collector FK to User
  - trashport/payments/services.py → WalletService.adjust_points() modifies wallet_points
  - trashport/collectors/views.py  → reads/writes wallet_balance for collector earnings
  - trashport/collectors/models.py → CollectorAadhaarProfile OneToOne to User
  - trashport/notifications/models.py → Notification.user FK to User
  - config/api_router.py           → UserViewSet exposes users via REST API

WALLET TYPES (two separate fields, one per role):
  wallet_points  (int)     : CITIZEN recycling reward points (1 pt = Rs. 0.10)
                             Earned by completing pickups with recyclable waste.
                             Spent by redeeming coupons (100 pts = Rs. 10 off).
  wallet_balance (Decimal) : COLLECTOR cash earnings in INR.
                             Credited when a pickup is marked COMPLETED.
                             Withdrawn to UPI via CollectorRedeemUPIView.

IMPACT:
  - Changing Roles choices affects the role dispatch system in waste_management/views.py.
  - wallet_points and wallet_balance are separate by design — never conflate them.
  - is_verified is set True by admin approval or auto-set by Aadhaar verification sync.
  - Changing AUTH_USER_MODEL in settings after first migration is very difficult —
    this model should not be replaced without a full database migration plan.
"""

from typing import ClassVar
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField
from django.db.models import EmailField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for TrashPort (Normalized to 3NF).
    Base entity containing core credentials and authentication identity.
    Role-specific attributes are normalized into CitizenProfile and CollectorProfile.
    """
    class Roles(models.TextChoices):
        CITIZEN = "CITIZEN", "Citizen"
        COLLECTOR = "COLLECTOR", "Collector"
        ADMIN = "ADMIN", "Admin"

    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending Verification")
        APPROVED = "APPROVED", _("Approved / Verified")
        REJECTED = "REJECTED", _("Rejected")

    role = CharField(
        _("Role"),
        max_length=20,
        choices=Roles.choices,
        default=Roles.CITIZEN,
    )

    verification_status = CharField(
        _("Verification Status"),
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )

    firebase_uid = CharField(
        _("Firebase UID"),
        max_length=255,
        unique=True,
        blank=True,
        null=True,
    )
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    phone_number = CharField(_("Phone Number"), max_length=20, blank=True, null=True)
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    @property
    def is_verified(self) -> bool:
        """
        3NF Computed Property: Check if collector is verified.
        Derived directly from verification_status == APPROVED to eliminate DB column redundancy.
        """
        return self.verification_status == self.VerificationStatus.APPROVED

    @is_verified.setter
    def is_verified(self, value: bool):
        """Update verification_status based on boolean assignment."""
        if value:
            self.verification_status = self.VerificationStatus.APPROVED
        elif self.verification_status == self.VerificationStatus.APPROVED:
            self.verification_status = self.VerificationStatus.PENDING

    # -------------------------------------------------------------------------
    # Profile Access Helpers (DRY pattern to avoid duplicate get_or_create)
    # -------------------------------------------------------------------------

    def _get_citizen_profile(self) -> "CitizenProfile":
        """Retrieve or initialize the CitizenProfile instance for this user."""
        profile, _ = CitizenProfile.objects.get_or_create(user=self)
        return profile

    def _get_collector_profile(self) -> "CollectorProfile":
        """Retrieve or initialize the CollectorProfile instance for this user."""
        profile, _ = CollectorProfile.objects.get_or_create(user=self)
        return profile

    # -------------------------------------------------------------------------
    # Role-Specific 3NF Property Accessors
    # Provides seamless attribute access while persisting data in separate 3NF profile tables.
    # -------------------------------------------------------------------------

    @property
    def wallet_points(self) -> int:
        """Get recycling reward points from CitizenProfile."""
        if hasattr(self, "_pending_wallet_points"):
            return self._pending_wallet_points
        try:
            return self.citizen_profile.wallet_points
        except (AttributeError, CitizenProfile.DoesNotExist):
            return 0

    @wallet_points.setter
    def wallet_points(self, value: int):
        """Set recycling reward points in CitizenProfile."""
        if not self.pk:
            self._pending_wallet_points = value
            return
        profile = self._get_citizen_profile()
        profile.wallet_points = value
        profile.save()
        self.citizen_profile = profile

    @property
    def wallet_balance(self) -> Decimal:
        """Get cash earnings balance (Rs.) from CollectorProfile."""
        if hasattr(self, "_pending_wallet_balance"):
            return self._pending_wallet_balance
        if hasattr(self, "collector_profile"):
            return self.collector_profile.wallet_balance
        return Decimal("0.00")

    @wallet_balance.setter
    def wallet_balance(self, value):
        """Set cash earnings balance in CollectorProfile."""
        if not self.pk:
            self._pending_wallet_balance = Decimal(str(value))
            return
        profile = self._get_collector_profile()
        profile.wallet_balance = Decimal(str(value))
        profile.save()

    @property
    def vehicle_number(self):
        """Get vehicle registration number from CollectorProfile."""
        if hasattr(self, "_pending_vehicle_number"):
            return self._pending_vehicle_number
        if hasattr(self, "collector_profile"):
            return self.collector_profile.vehicle_number
        return None

    @vehicle_number.setter
    def vehicle_number(self, value):
        """Set vehicle registration number in CollectorProfile."""
        if not self.pk:
            self._pending_vehicle_number = value
            return
        profile = self._get_collector_profile()
        profile.vehicle_number = value
        profile.save()

    @property
    def license_number(self):
        """Get driver/collector license from CollectorProfile."""
        if hasattr(self, "_pending_license_number"):
            return self._pending_license_number
        if hasattr(self, "collector_profile"):
            return self.collector_profile.license_number
        return None

    @license_number.setter
    def license_number(self, value):
        """Set driver/collector license in CollectorProfile."""
        if not self.pk:
            self._pending_license_number = value
            return
        profile = self._get_collector_profile()
        profile.license_number = value
        profile.save()

    def save(self, *args, **kwargs):
        """
        Custom save method.
        Filters out property names from update_fields and auto-creates appropriate role profiles.
        """
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            valid_fields = [f.name for f in self._meta.fields]
            kwargs["update_fields"] = [f for f in update_fields if f in valid_fields]
            if not kwargs["update_fields"]:
                kwargs.pop("update_fields")

        is_new = not self.pk
        if is_new:
            if self.role in [self.Roles.CITIZEN, self.Roles.ADMIN]:
                self.verification_status = self.VerificationStatus.APPROVED
            elif self.role == self.Roles.COLLECTOR:
                if not self.verification_status:
                    self.verification_status = self.VerificationStatus.PENDING

        super().save(*args, **kwargs)

        if self.role == self.Roles.COLLECTOR:
            collector_profile, _ = CollectorProfile.objects.get_or_create(user=self)
            dirty = False
            if hasattr(self, "_pending_wallet_balance"):
                collector_profile.wallet_balance = self._pending_wallet_balance
                delattr(self, "_pending_wallet_balance")
                dirty = True
            if hasattr(self, "_pending_vehicle_number"):
                collector_profile.vehicle_number = self._pending_vehicle_number
                delattr(self, "_pending_vehicle_number")
                dirty = True
            if hasattr(self, "_pending_license_number"):
                collector_profile.license_number = self._pending_license_number
                delattr(self, "_pending_license_number")
                dirty = True
            if dirty:
                collector_profile.save()
        else:
            citizen_profile, _ = CitizenProfile.objects.get_or_create(user=self)
            if hasattr(self, "_pending_wallet_points"):
                citizen_profile.wallet_points = self._pending_wallet_points
                delattr(self, "_pending_wallet_points")
                citizen_profile.save()

    def get_absolute_url(self) -> str:
        return reverse("users:detail")


class CitizenProfile(models.Model):
    """
    3NF Profile model holding citizen-specific attributes.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="citizen_profile",
    )
    wallet_points = models.IntegerField(
        _("Wallet Points"),
        default=0,
        help_text=_("Recycling reward points for citizens."),
    )

    def __str__(self):
        return f"CitizenProfile({self.user.email}) - {self.wallet_points} pts"


class CollectorProfile(models.Model):
    """
    3NF Profile model holding collector-specific attributes.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collector_profile",
    )
    wallet_balance = models.DecimalField(
        _("Wallet Balance (Rs.)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Cash earnings balance for collectors from completed waste pickups."),
    )
    vehicle_number = CharField(
        _("Vehicle Number"),
        max_length=50,
        blank=True,
        null=True,
    )
    license_number = CharField(
        _("Driver / Collector License"),
        max_length=50,
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"CollectorProfile({self.user.email})"

