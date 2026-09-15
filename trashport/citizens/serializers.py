from rest_framework import serializers
from trashport.core.waste_management.models import PickupRequest, Address, Complaint


class CitizenPickupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupRequest
        fields = "__all__"


class CitizenAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"


class CitizenComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = "__all__"
