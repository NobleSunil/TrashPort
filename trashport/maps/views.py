from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import ServiceZone, CollectorLocation
from .serializers import (
    ServiceZoneSerializer,
    CollectorLocationSerializer,
    UpdateLocationSerializer,
)


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
