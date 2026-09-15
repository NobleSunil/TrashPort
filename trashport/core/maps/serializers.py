"""
Serializers for the Maps and Geo-tracking module.

Handles serialization and deserialization of service zones,
collector GPS positions, and live telemetry updates from mobile collectors.
"""

from rest_framework import serializers
from .models import ServiceZone, CollectorLocation


class ServiceZoneSerializer(serializers.ModelSerializer):
    """
    Serializer for municipal/operational service zones.

    Maps defined operational boundaries and service pricing/coverage areas.
    """
    class Meta:
        model = ServiceZone
        fields = "__all__"


class CollectorLocationSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying live and recorded collector GPS coordinates.

    Includes read-only identity metadata (name and email) for live map pins.
    """
    collector_name = serializers.CharField(source="collector.name", read_only=True)
    collector_email = serializers.CharField(source="collector.email", read_only=True)

    class Meta:
        model = CollectorLocation
        fields = (
            "id",
            "collector",
            "collector_name",
            "collector_email",
            "latitude",
            "longitude",
            "speed",
            "heading",
            "updated_at",
        )
        read_only_fields = ("id", "collector", "updated_at")


class UpdateLocationSerializer(serializers.Serializer):
    """
    Validation serializer for collector GPS telemetry pings.

    Used by collectors posting frequent location updates (latitude, longitude,
    speed in km/h, and compass heading in degrees).
    """
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Collector latitude (-90.0 to 90.0)",
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Collector longitude (-180.0 to 180.0)",
    )
    speed = serializers.FloatField(
        required=False,
        default=0.0,
        help_text="Current speed in km/h",
    )
    heading = serializers.FloatField(
        required=False,
        default=0.0,
        help_text="Heading in degrees (0 - 360)",
    )
