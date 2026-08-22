from rest_framework import serializers
from waste_management.models import PickupRequest


class CollectorJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupRequest
        fields = "__all__"
