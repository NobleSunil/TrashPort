"""
trashport/maps/models.py — Geospatial Data Models
==================================================

PURPOSE:
  Provides two models for spatial awareness:
    ServiceZone      : Defines geographic service areas (admin-configurable).
    CollectorLocation: Stores live GPS position of collectors (updated in real-time).

CONNECTION MAP:
  - trashport/collectors/views.py  → reads CollectorLocation for dashboard map center
  - trashport/maps/views.py        → reads/writes CollectorLocation via API
  - trashport/maps/urls.py         → exposes /api/maps/location/ update endpoint
  - trashport/admins/views.py      → reads CollectorLocation for live-map display

IMPACT:
  - CollectorLocation is OneToOne with User — each collector has exactly one row.
    Update it via the maps API (/api/maps/location/) on GPS position change.
  - ServiceZone is informational only — not currently used for automatic
    zone-based dispatch (that's handled by the dispatch app).
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ServiceZone(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    center_latitude = models.DecimalField(max_digits=9, decimal_places=6, default=9.9312)
    center_longitude = models.DecimalField(max_digits=9, decimal_places=6, default=76.2673)
    radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=25.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class CollectorLocation(models.Model):
    collector = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="live_location",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    speed = models.FloatField(default=0.0, help_text="Speed in km/h")
    heading = models.FloatField(default=0.0, help_text="Compass heading in degrees")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.collector} @ ({self.latitude}, {self.longitude})"
