"""
Django administration configuration for Maps models.

Registers ServiceZone and CollectorLocation models in the Django admin dashboard.
"""

from django.contrib import admin
from .models import ServiceZone, CollectorLocation


@admin.register(ServiceZone)
class ServiceZoneAdmin(admin.ModelAdmin):
    """
    Admin configuration for operational service zones.

    Allows administrators to configure municipal service boundaries,
    center coordinates, coverage radius, and active status.
    """
    list_display = ("name", "code", "center_latitude", "center_longitude", "radius_km", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(CollectorLocation)
class CollectorLocationAdmin(admin.ModelAdmin):
    """
    Admin configuration for collector live GPS records.

    Enables inspection of real-time collector coordinates, telemetry speeds,
    and timestamps directly from the admin panel.
    """
    list_display = ("collector", "latitude", "longitude", "speed", "heading", "updated_at")
    search_fields = ("collector__email", "collector__name")
