# ==============================================================================
# TrashPort - Notification Serializer
# ==============================================================================
# Serializes Notification model instances into JSON representations for the REST API.
# ==============================================================================

from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    ModelSerializer that converts Notification instances to JSON and validates inputs.
    Includes all model fields while enforcing read-only constraints on immutable attributes.
    """
    class Meta:
        model = Notification
        # Expose all model fields in JSON output (id, user, title, message, notification_type, is_read, created_at)
        fields = "__all__"
        # Protect system-generated fields from being modified by client API requests
        read_only_fields = ("id", "user", "created_at")
