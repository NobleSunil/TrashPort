from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Address, SubscriptionTier, Subscription, WasteCategory, PickupRequest, Complaint

User = get_user_model()

class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "role"]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"


class SubscriptionTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionTier
        fields = "__all__"


class SubscriptionSerializer(serializers.ModelSerializer):
    tier_details = SubscriptionTierSerializer(source="tier", read_only=True)
    user_details = UserShortSerializer(source="user", read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id", "user", "user_details", "tier", "tier_details", 
            "start_date", "end_date", "is_active", "created_at", "updated_at"
        ]


class WasteCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteCategory
        fields = "__all__"


class PickupRequestSerializer(serializers.ModelSerializer):
    citizen_details = UserShortSerializer(source="citizen", read_only=True)
    collector_details = UserShortSerializer(source="collector", read_only=True)
    address_details = AddressSerializer(source="address", read_only=True)
    category_details = WasteCategorySerializer(source="category", read_only=True)

    class Meta:
        model = PickupRequest
        fields = [
            "id", "citizen", "citizen_details", "collector", "collector_details",
            "address", "address_details", "category", "category_details",
            "weight_kg", "quantity_estimate", "fee", "points_earned", "is_paid",
            "schedule_date", "status", "feedback_rating", "feedback_comments",
            "created_at", "updated_at"
        ]


class ComplaintSerializer(serializers.ModelSerializer):
    citizen_details = UserShortSerializer(source="citizen", read_only=True)
    pickup_request_details = PickupRequestSerializer(source="pickup_request", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id", "citizen", "citizen_details", "pickup_request", "pickup_request_details",
            "title", "description", "status", "created_at", "updated_at"
        ]
