"""
waste_management/serializers.py — DRF Serializers for Core Models
===================================================================

PURPOSE:
  Defines Django REST Framework serializers that convert model instances
  to/from JSON for the REST API endpoints registered in config/api_router.py.

SERIALIZERS:
  UserShortSerializer     : Minimal user data (id, name, email, role) used as
                            nested read-only fields in other serializers.
  AddressSerializer       : Full address model serialization (all fields).
  WasteCategorySerializer : Full category serialization (all fields).
  PickupRequestSerializer : Full pickup serialization with nested citizen,
                            collector, address, and category detail objects.
                            Validates schedule_date is at least 3 hours in future.
  ComplaintSerializer     : Full complaint serialization with nested citizen
                            and pickup_request details.

CONNECTION MAP:
  - config/api_router.py          → registers ViewSets that use these serializers
  - waste_management/views.py     → AddressViewSet, WasteCategoryViewSet, etc.
  - trashport/admins/serializers.py → (DELETED — duplicates removed in cleanup)

IMPACT:
  - Adding a field to a serializer exposes it in the JSON API response.
  - Removing a field hides it from API consumers without a migration.
  - The schedule_date validation in PickupRequestSerializer (min 3 hours ahead)
    applies to API requests only — not to admin-created pickups via the view layer.
"""

from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Address, WasteCategory, PickupRequest, Complaint
User = get_user_model()

class UserShortSerializer(serializers.ModelSerializer):
    """
    Lightweight user serializer for nested API payloads.

    Exposes only non-sensitive identifiers: user ID, display name, email, and role.
    """
    class Meta:
        model = User
        fields = ["id", "name", "email", "role"]


class AddressSerializer(serializers.ModelSerializer):
    """
    Serializer for citizen residential and commercial pickup addresses.

    Handles geolocation coordinates (latitude, longitude) and postal details.
    """
    class Meta:
        model = Address
        fields = "__all__"


class WasteCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for waste categories and recycling material types.

    Includes pricing metrics (fee_per_kg), reward multiplier (points_per_kg),
    and maximum allowable weight constraints.
    """
    class Meta:
        model = WasteCategory
        fields = "__all__"


class PickupRequestSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for waste pickup requests.

    Embeds nested read-only details for citizen, assigned collector, address,
    and waste category. Calculates pricing, earnings, and reward point projections.
    """
    citizen_details = UserShortSerializer(source="citizen", read_only=True)
    collector_details = UserShortSerializer(source="collector", read_only=True)
    address_details = AddressSerializer(source="address", read_only=True)
    category_details = WasteCategorySerializer(source="category", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = PickupRequest
        fields = [
            "id", "citizen", "citizen_details", "collector", "collector_details",
            "address", "address_details", "latitude", "longitude", "category", "category_name", "category_details",
            "weight_kg", "quantity_estimate", "actual_weight_kg", "extra_fee", "distance_km",
            "fee", "collector_earnings", "points_earned", "is_paid",
            "schedule_date", "status", "feedback_rating", "feedback_comments",
            "created_at", "updated_at"
        ]

    def validate_schedule_date(self, value):
        """
        Validate that scheduled pickup time is at least 3 hours into the future.
        Prevents instant-demand overload and allows collectors adequate transit time.
        """
        min_allowed_time = timezone.now() + timedelta(hours=3)
        if value < min_allowed_time:
            raise serializers.ValidationError("Pickup must be scheduled at least 3 hours in advance from the current time.")
        return value


class ComplaintSerializer(serializers.ModelSerializer):
    """
    Serializer for citizen complaint tickets and disputes.

    Embeds citizen user details and associated pickup request reference.
    """
    citizen_details = UserShortSerializer(source="citizen", read_only=True)
    pickup_request_details = PickupRequestSerializer(source="pickup_request", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id", "citizen", "citizen_details", "pickup_request", "pickup_request_details",
            "title", "description", "status", "created_at", "updated_at"
        ]
