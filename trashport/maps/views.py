from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ServiceZone, CollectorLocation
from .serializers import (
    ServiceZoneSerializer,
    CollectorLocationSerializer,
    UpdateLocationSerializer,
)
from .services import GeoService
from waste_management.models import PickupRequest


class ServiceZoneListView(generics.ListCreateAPIView):
    queryset = ServiceZone.objects.filter(is_active=True)
    serializer_class = ServiceZoneSerializer
    permission_classes = [AllowAny]


class CollectorLocationListView(generics.ListAPIView):
    queryset = CollectorLocation.objects.all()
    serializer_class = CollectorLocationSerializer
    permission_classes = [IsAuthenticated]


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_collector_location_view(request):
    """Updates live GPS coordinates for the authenticated collector."""
    serializer = UpdateLocationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    loc, created = CollectorLocation.objects.update_or_create(
        collector=request.user,
        defaults={
            "latitude": serializer.validated_data["latitude"],
            "longitude": serializer.validated_data["longitude"],
            "speed": serializer.validated_data.get("speed", 0.0),
            "heading": serializer.validated_data.get("heading", 0.0),
        }
    )
    return Response(CollectorLocationSerializer(loc).data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def live_map_data_view(request):
    """
    Returns active pickup request coordinates and active collector live GPS coordinates
    for admin monitoring and fleet overview.
    """
    # Active pickups: PENDING, ASSIGNED, IN_TRANSIT
    active_statuses = [
        PickupRequest.StatusChoices.PENDING,
        PickupRequest.StatusChoices.ASSIGNED,
        PickupRequest.StatusChoices.IN_TRANSIT,
    ]
    pickups_qs = PickupRequest.objects.filter(status__in=active_statuses).select_related(
        "citizen", "collector", "address", "category"
    )

    pickups_data = []
    for p in pickups_qs:
        lat = float(p.latitude or (p.address.latitude if p.address else None) or 12.9716)
        lng = float(p.longitude or (p.address.longitude if p.address else None) or 77.5946)
        pickups_data.append({
            "id": p.id,
            "status": p.status,
            "category": p.category.name if p.category else "Waste",
            "citizen_name": p.citizen.name or p.citizen.email,
            "citizen_email": p.citizen.email,
            "collector_name": (p.collector.name or p.collector.email) if p.collector else None,
            "address": f"{p.address.address_line1}, {p.address.city}" if p.address else "",
            "latitude": lat,
            "longitude": lng,
            "weight_kg": float(p.weight_kg),
            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    collectors_qs = CollectorLocation.objects.all().select_related("collector")
    collectors_data = []
    for c in collectors_qs:
        collectors_data.append({
            "collector_id": c.collector.id,
            "name": c.collector.name or c.collector.email,
            "email": c.collector.email,
            "latitude": float(c.latitude),
            "longitude": float(c.longitude),
            "speed": c.speed,
            "heading": c.heading,
            "updated_at": c.updated_at.strftime("%H:%M:%S"),
        })

    return Response({
        "pickups": pickups_data,
        "collectors": collectors_data,
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pickup_live_tracking_view(request, pickup_id):
    """
    Returns live tracking info for a specific pickup request:
    - User pickup coordinates
    - Collector live coordinates
    - Distance (km)
    - ETA (mins)
    """
    pickup = get_object_or_404(PickupRequest, id=pickup_id)

    # Pickup lat/lng
    pickup_lat = float(pickup.latitude or (pickup.address.latitude if pickup.address else None) or 12.9716)
    pickup_lng = float(pickup.longitude or (pickup.address.longitude if pickup.address else None) or 77.5946)

    collector_loc = None
    distance_km = float(pickup.distance_km or 0)
    eta_mins = None

    if pickup.collector:
        try:
            c_loc = CollectorLocation.objects.get(collector=pickup.collector)
            collector_lat = float(c_loc.latitude)
            collector_lng = float(c_loc.longitude)
            
            # Compute live distance
            distance_km = GeoService.haversine_distance(
                collector_lat, collector_lng, pickup_lat, pickup_lng
            )
            # Estimate ETA: assume speed of 25 km/h if stopped or speed not reported
            speed = c_loc.speed if c_loc.speed > 5 else 25.0
            eta_mins = max(1, int((distance_km / speed) * 60))

            collector_loc = {
                "name": pickup.collector.name or pickup.collector.email,
                "latitude": collector_lat,
                "longitude": collector_lng,
                "speed": c_loc.speed,
                "heading": c_loc.heading,
                "updated_at": c_loc.updated_at.strftime("%H:%M:%S"),
            }
        except CollectorLocation.DoesNotExist:
            pass

    return Response({
        "pickup_id": pickup.id,
        "status": pickup.status,
        "pickup_location": {
            "latitude": pickup_lat,
            "longitude": pickup_lng,
            "address": f"{pickup.address.address_line1}, {pickup.address.city}" if pickup.address else "",
        },
        "collector_location": collector_loc,
        "distance_km": distance_km,
        "eta_mins": eta_mins,
    }, status=status.HTTP_200_OK)
