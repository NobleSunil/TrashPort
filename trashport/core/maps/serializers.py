from rest_framework import serializers
from .models import ServiceZone, CollectorLocation


class ServiceZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceZone
        fields = "__all__"


class CollectorLocationSerializer(serializers.ModelSerializer):
    collector_name = serializers.CharField(source="collector.name", read_only=True)
    collector_email = serializers.CharField(source="collector.email", read_only=True)

    class Meta:
        model = CollectorLocation
        fields = ("id", "collector", "collector_name", "collector_email", "latitude", "longitude", "speed", "heading", "updated_at")
        read_only_fields = ("id", "collector", "updated_at")


class UpdateLocationSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    speed = serializers.FloatField(required=False, default=0.0)
    heading = serializers.FloatField(required=False, default=0.0)
