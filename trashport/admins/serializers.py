from rest_framework import serializers
from waste_management.models import WasteCategory


class WasteCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteCategory
        fields = "__all__"

