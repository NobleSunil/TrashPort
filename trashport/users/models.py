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

    role = CharField(
        _("Role"),
        max_length=20,
        choices=Roles.choices,
        default=Roles.CITIZEN,
    )

    wallet_points = models.IntegerField(
        _("Wallet Points"),
        default=0,
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
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.id})
