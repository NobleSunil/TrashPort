from rest_framework import serializers
from .models import DispatchBatch


class DispatchBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispatchBatch
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class TriggerDispatchSerializer(serializers.Serializer):
    algorithm = serializers.ChoiceField(
        choices=["NEAREST", "LEAST_BUSY", "ZONE_BASED"],
        default="NEAREST"
    )
