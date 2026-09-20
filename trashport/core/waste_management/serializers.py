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
from .models import (
    Address, WasteCategory, PickupRequest, Complaint,
    City, Hub, Vehicle, Route, RoutePickup
)
from trashport.core.waste_management.services.route_service import RouteService
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


class CitySerializer(serializers.ModelSerializer):
    """
    Serializer for operational cities.
    Includes active hub status and collector readiness indicator.
    """
    has_active_collectors = serializers.BooleanField(read_only=True)
    active_hub_name = serializers.CharField(source="active_hub.name", read_only=True)

    class Meta:
        model = City
        fields = [
            "id", "name", "state", "is_active", "active_hub", "active_hub_name",
            "has_active_collectors", "created_at", "updated_at"
        ]


class HubSerializer(serializers.ModelSerializer):
    """
    Serializer for base operation hubs.
    Coordinates define the origin/terminus for vehicle routes and the 20 km radial zone.
    """
    city_name = serializers.CharField(source="city.name", read_only=True)
    vehicle_count = serializers.IntegerField(source="vehicles.count", read_only=True)

    class Meta:
        model = Hub
        fields = [
            "id", "name", "city", "city_name", "latitude", "longitude",
            "address", "is_active", "vehicle_count", "created_at", "updated_at"
        ]


class VehicleSerializer(serializers.ModelSerializer):
    """
    Serializer for fleet collection vehicles.
    Enforces maximum capacity of 5 pickups per trip.
    """
    hub_name = serializers.CharField(source="hub.name", read_only=True)
    city_name = serializers.CharField(source="hub.city.name", read_only=True)
    driver_name = serializers.CharField(source="driver.name", read_only=True)
    driver_email = serializers.CharField(source="driver.email", read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            "id", "vehicle_number", "hub", "hub_name", "city_name",
            "driver", "driver_name", "driver_email",
            "max_capacity", "status", "created_at", "updated_at"
        ]


class RoutePickupSerializer(serializers.ModelSerializer):
    """
    Serializer for intermediate waypoint stops along a collection route.
    """
    pickup_display_id = serializers.CharField(source="pickup_request.display_id", read_only=True)
    citizen_name = serializers.CharField(source="pickup_request.citizen.name", read_only=True)
    address_display = serializers.CharField(source="pickup_request.address.address_line1", read_only=True)
    weight_kg = serializers.DecimalField(source="pickup_request.weight_kg", max_digits=6, decimal_places=2, read_only=True)
    category_name = serializers.CharField(source="pickup_request.category.name", read_only=True)

    class Meta:
        model = RoutePickup
        fields = [
            "id", "route", "pickup_request", "pickup_display_id",
            "citizen_name", "address_display", "weight_kg", "category_name",
            "sequence", "status", "created_at"
        ]


class RouteSerializer(serializers.ModelSerializer):
    """
    Serializer for collection trip routes.
    Includes waypoints originating at the Hub and terminating back at the Hub.
    """
    vehicle_number = serializers.CharField(source="vehicle.vehicle_number", read_only=True)
    driver_name = serializers.CharField(source="vehicle.driver.name", read_only=True)
    hub_name = serializers.CharField(source="hub.name", read_only=True)
    city_name = serializers.CharField(source="hub.city.name", read_only=True)
    stops = RoutePickupSerializer(source="route_pickups", many=True, read_only=True)
    pickup_count = serializers.IntegerField(source="route_pickups.count", read_only=True)
    waypoints = serializers.ListField(source="get_waypoints", read_only=True)

    class Meta:
        model = Route
        fields = [
            "id", "vehicle", "vehicle_number", "driver_name",
            "hub", "hub_name", "city_name", "start_time", "end_time",
            "status", "total_distance_km", "pickup_count", "stops", "waypoints",
            "created_at", "updated_at"
        ]


class PickupRequestSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for waste pickup requests.

    Embeds nested read-only details for citizen, assigned collector, address,
    city, hub, and waste category. Enforces 20 km radial zone and collector availability.
    """
    citizen_details = UserShortSerializer(source="citizen", read_only=True)
    collector_details = UserShortSerializer(source="collector", read_only=True)
    address_details = AddressSerializer(source="address", read_only=True)
    category_details = WasteCategorySerializer(source="category", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    hub_name = serializers.CharField(source="hub.name", read_only=True)

    class Meta:
        model = PickupRequest
        fields = [
            "id", "citizen", "citizen_details", "collector", "collector_details",
            "city", "city_name", "hub", "hub_name",
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

    def validate(self, attrs):
        city = attrs.get("city")
        lat = attrs.get("latitude")
        lng = attrs.get("longitude")
        address = attrs.get("address")

        if address and (lat is None or lng is None):
            lat = float(address.latitude) if address.latitude else None
            lng = float(address.longitude) if address.longitude else None

        if city and lat is not None and lng is not None:
            from django.core.exceptions import ValidationError as DjangoValidationError
            try:
                eligible, hub, dist = RouteService.validate_pickup_eligibility(city, float(lat), float(lng))
                attrs["hub"] = hub
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"non_field_errors": [exc.message if hasattr(exc, "message") else str(exc)]})

        return super().validate(attrs)


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
