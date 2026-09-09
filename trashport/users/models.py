from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField
from django.db.models import EmailField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for TrashPort.
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

    is_verified = models.BooleanField(
        _("Is Verified"),
        default=False,
        help_text=_("Designates whether this collector is verified and approved by an administrator."),
    )
    verification_status = CharField(
        _("Verification Status"),
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )

    wallet_points = models.IntegerField(
        _("Wallet Points"),
        default=0,
        help_text=_("Recycling reward points for citizens."),
    )
    wallet_balance = models.DecimalField(
        _("Wallet Balance (Rs.)"),
        max_digits=10,
        decimal_places=2,
        default=0.00,
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

    def save(self, *args, **kwargs):
        is_new = not self.pk
        if is_new:
            if self.role in [self.Roles.CITIZEN, self.Roles.ADMIN]:
                self.is_verified = True
                self.verification_status = self.VerificationStatus.APPROVED
            elif self.role == self.Roles.COLLECTOR:
                if not self.verification_status:
                    self.verification_status = self.VerificationStatus.PENDING
                self.is_verified = (self.verification_status == self.VerificationStatus.APPROVED)
        else:
            if self.verification_status == self.VerificationStatus.APPROVED:
                self.is_verified = True
            elif self.verification_status in [self.VerificationStatus.PENDING, self.VerificationStatus.REJECTED]:
                if self.role == self.Roles.COLLECTOR:
                    self.is_verified = False
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("users:detail")
