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
from trashport.core.waste_management.models import PickupRequest


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
    """Updates live GPS coordinates for the authenticated collector and aligns nearest Hub."""
    serializer = UpdateLocationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    lat = float(serializer.validated_data["latitude"])
    lng = float(serializer.validated_data["longitude"])

    loc, created = CollectorLocation.objects.update_or_create(
        collector=request.user,
        defaults={
            "latitude": lat,
            "longitude": lng,
            "speed": serializer.validated_data.get("speed", 0.0),
            "heading": serializer.validated_data.get("heading", 0.0),
        }
    )

    # If the user is a collector, dynamically align their active hub to the nearest hub within 25 km
    if getattr(request.user, "role", None) == "COLLECTOR":
        from trashport.core.waste_management.models import Hub
        from trashport.core.maps.services import GeoService
        hubs = list(Hub.objects.filter(is_active=True))
        if hubs:
            nearest_hub = min(
                hubs,
                key=lambda h: GeoService.haversine_distance(lat, lng, float(h.latitude), float(h.longitude))
            )
            dist_to_hub = GeoService.haversine_distance(lat, lng, float(nearest_hub.latitude), float(nearest_hub.longitude))
            if dist_to_hub <= 25.0 and request.user.hub != nearest_hub:
                request.user.hub = nearest_hub
                request.user.save()

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
        lat = p.effective_latitude
        lng = p.effective_longitude
        pickups_data.append({
            "id": p.id,
            "status": p.status,
            "category": p.category.name if p.category else "Waste",
            "citizen_name": p.citizen.name or p.citizen.email,
            "citizen_email": p.citizen.email,
            "collector_id": p.collector.id if p.collector else None,
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
        # Find active pickups assigned to this specific collector
        assigned_jobs = [p for p in pickups_qs if p.collector_id == c.collector.id]
        is_assigned = len(assigned_jobs) > 0

        assigned_pickups_list = []
        for job in assigned_jobs:
            assigned_pickups_list.append({
                "id": job.id,
                "category": job.category.name if job.category else "Waste",
                "citizen_name": job.citizen.name or job.citizen.email,
                "address": f"{job.address.address_line1}, {job.address.city}" if job.address else "",
                "latitude": job.effective_latitude,
                "longitude": job.effective_longitude,
                "status": job.status,
                "weight_kg": float(job.weight_kg),
            })

        collectors_data.append({
            "collector_id": c.collector.id,
            "name": c.collector.name or c.collector.email,
            "email": c.collector.email,
            "latitude": float(c.latitude),
            "longitude": float(c.longitude),
            "speed": c.speed,
            "heading": c.heading,
            "is_assigned": is_assigned,
            "active_task_count": len(assigned_jobs),
            "assigned_pickups": assigned_pickups_list,
            "updated_at": c.updated_at.strftime("%H:%M:%S"),
        })

    from trashport.core.waste_management.models import Hub
    hubs_qs = Hub.objects.filter(is_active=True).select_related("city")
    hubs_data = []
    for h in hubs_qs:
        hubs_data.append({
            "id": h.id,
            "name": h.name,
            "city": h.city.name,
            "latitude": float(h.latitude),
            "longitude": float(h.longitude),
            "address": h.address,
            "vehicle_count": h.vehicles.count(),
        })

    return Response({
        "pickups": pickups_data,
        "collectors": collectors_data,
        "hubs": hubs_data,
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
    pickup_lat = pickup.effective_latitude
    pickup_lng = pickup.effective_longitude

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


@api_view(["GET"])
@permission_classes([AllowAny])
def calculate_road_route_view(request):
    """
    Returns actual turn-by-turn road route coordinates between start and end locations.
    Query params: start_lat, start_lng, end_lat, end_lng
    """
    try:
        start_lat = float(request.GET.get("start_lat", 0))
        start_lng = float(request.GET.get("start_lng", 0))
        end_lat = float(request.GET.get("end_lat", 0))
        end_lng = float(request.GET.get("end_lng", 0))
    except (ValueError, TypeError):
        return Response({"error": "Invalid coordinates provided"}, status=status.HTTP_400_BAD_REQUEST)

    route_info = GeoService.get_road_route_osrm(start_lat, start_lng, end_lat, end_lng)
    return Response(route_info, status=status.HTTP_200_OK)
