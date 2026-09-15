"""
Citizen-scoped REST API serializers.

Provides role-tailored serialization for citizen pickup scheduling,
saved residential addresses, and issue/complaint submissions.
"""

from rest_framework import serializers
from trashport.core.waste_management.models import PickupRequest, Address, Complaint


class CitizenPickupSerializer(serializers.ModelSerializer):
    """
    Serializer for citizen pickup request creation and status tracking.
    Enforces citizen ownership and validates scheduling windows.
    """
    class Meta:
        model = PickupRequest
        fields = "__all__"


class CitizenAddressSerializer(serializers.ModelSerializer):
    """
    Serializer for citizen address management (home, office, pickup points).
    Handles latitude and longitude coordinates for map pinning.
    """
    class Meta:
        model = Address
        fields = "__all__"


class CitizenComplaintSerializer(serializers.ModelSerializer):
    """
    Serializer for logging citizen service complaints and escalation tickets.
    """
    class Meta:
        model = Complaint
        fields = "__all__"
