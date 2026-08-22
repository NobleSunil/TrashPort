from rest_framework import serializers
from waste_management.models import WasteCategory, SubscriptionTier


class WasteCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteCategory
        fields = "__all__"


class SubscriptionTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionTier
        fields = "__all__"
