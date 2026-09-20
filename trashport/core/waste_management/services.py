"""
trashport/core/waste_management/services.py
============================================

PURPOSE:
  Core business domain service layer for waste management operations, including
  city-aware eligibility checks, hub-based 20 km coverage boundary validation,
  fleet vehicle capacity capping (max 5 pickups per trip), and atomic route assignments.

MODULE ARCHITECTURE & CONNECTIONS:
  - Models used:
      * City, Hub, Vehicle, Route, RoutePickup, PickupRequest (from .models)
  - Map / Geodesic service:
      * GeoService (from trashport.core.maps.services) for haversine distance calculations
  - Consumers of this service:
      * trashport/citizens/forms.py (citizen pickup booking eligibility validation)
      * trashport/core/waste_management/serializers.py (REST API pickup request creation validation)
      * trashport/admins/views.py (admin route creation, vehicle assignment, pickup hold)
      * trashport/core/waste_management/views.py (role dispatch views)
      * trashport/tests/ (automated route & hub validation test suites)

BUSINESS RULES ENFORCED:
  1. City without active Hub:
     "Pickup service is currently unavailable in this city because no active hub is registered."
  2. City with Hub but without registered collectors:
     "Pickup service is currently unavailable in your city. It will be available soon as collectors are registered in this area."
  3. 20 km Hub Service Radius:
     "Pickup service is unavailable at this location. The pickup address is outside the 20 km service area of the nearest active hub."
  4. Vehicle Maximum 5 Pickups Per Trip:
     "This vehicle has reached its maximum capacity of 5 pickups."
  5. Route starts at Hub and terminates at Hub.
  6. Atomic concurrency locking with select_for_update() during route assignment.
"""

import sys
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from trashport.core.maps.services import GeoService
from trashport.core.waste_management.models import (
    City,
    Hub,
    PickupRequest,
    Route,
    RoutePickup,
    Vehicle,
)


class RouteService:
    """Service encapsulating Hub, Vehicle, and Route lifecycle operations."""

    MAX_PICKUPS_PER_ROUTE = 5
    HUB_SERVICE_RADIUS_KM = 20.0

    @classmethod
    def validate_pickup_eligibility(
        cls,
        city: City,
        latitude: float,
        longitude: float,
    ) -> Tuple[bool, Hub, float]:
        """
        Validates whether a pickup request is eligible for service based on geographic and facility constraints.

        Execution validation order:
          1. City active check.
          2. Active hub registered in city check.
          3. Active collectors registered in city check.
          4. Coordinates within 20 km radial distance of active Hub.

        Returns:
          (is_eligible: bool, hub: Hub, distance_km: float)
        Raises:
          ValidationError with exact required message if any check fails.
        """
        if not city or not city.is_active:
            raise ValidationError("Pickup service is currently unavailable in this selected city.")

        # Check 1: Active hub exists
        active_hub = city.active_hub
        if not active_hub:
            raise ValidationError(
                "Pickup service is currently unavailable in this city because no active hub is registered."
            )

        # Check 2: Registered/active collectors in city
        has_collectors = (
            city.has_active_collectors()
            if callable(getattr(city, "has_active_collectors", None))
            else city.has_active_collectors
        )
        if not has_collectors:
            raise ValidationError(
                "Pickup service is currently unavailable in your city. "
                "It will be available soon as collectors are registered in this area."
            )

        # Check 3: Distance from Hub <= 20 km
        dist = GeoService.haversine_distance(
            float(active_hub.latitude),
            float(active_hub.longitude),
            float(latitude),
            float(longitude),
        )
        if dist > cls.HUB_SERVICE_RADIUS_KM:
            raise ValidationError(
                "Pickup service is unavailable at this location. "
                "The pickup address is outside the 20 km service area of the nearest active hub."
            )

        return True, active_hub, dist

    @classmethod
    def create_route(cls, vehicle_id: int, start_time: Optional[timezone.datetime] = None) -> Route:
        """
        Creates a new planned trip route starting and ending at the vehicle's designated hub.

        Args:
          vehicle_id: Primary key of the fleet vehicle.
          start_time: Scheduled trip commencement time (defaults to now).

        Returns:
          Newly initialized Route record in PLANNED status.
        """
        vehicle = Vehicle.objects.select_related("hub").get(pk=vehicle_id)
        route = Route.objects.create(
            vehicle=vehicle,
            hub=vehicle.hub,
            start_time=start_time or timezone.now(),
            status=Route.StatusChoices.PLANNED,
            total_distance_km=Decimal("0.00"),
        )
        return route

    @classmethod
    def assign_pickup_to_route(
        cls,
        route_id: int,
        pickup_id: int,
        preferred_sequence: Optional[int] = None,
    ) -> RoutePickup:
        """
        Atomically assigns a pickup to a vehicle route with strict capacity and boundary enforcement.

        Concurrency & business safety:
          - Uses select_for_update() on Route, Vehicle, and PickupRequest.
          - Rejects assignment if route already has max_capacity (5) pickups.
          - Rejects assignment if pickup is > 20 km from route's Hub.
        """
        with transaction.atomic():
            route = (
                Route.objects.select_for_update()
                .select_related("vehicle", "hub", "hub__city")
                .get(pk=route_id)
            )
            vehicle = (
                Vehicle.objects.select_for_update()
                .get(pk=route.vehicle_id)
            )
            pickup = (
                PickupRequest.objects.select_for_update()
                .select_related("address")
                .get(pk=pickup_id)
            )

            # Capacity guard
            current_assigned_count = route.route_pickups.filter(
                status__in=[
                    RoutePickup.StatusChoices.PENDING,
                    RoutePickup.StatusChoices.ON_ROUTE,
                    RoutePickup.StatusChoices.PICKED_UP,
                ]
            ).count()

            max_cap = vehicle.max_capacity or cls.MAX_PICKUPS_PER_ROUTE
            if current_assigned_count >= max_cap:
                raise ValidationError("This vehicle has reached its maximum capacity of 5 pickups.")

            # Hub service radius guard (<= 20 km)
            dist_from_hub = GeoService.haversine_distance(
                float(route.hub.latitude),
                float(route.hub.longitude),
                float(pickup.effective_latitude),
                float(pickup.effective_longitude),
            )
            if dist_from_hub > cls.HUB_SERVICE_RADIUS_KM:
                raise ValidationError("This pickup location is more than 20 km from the service hub.")

            # Determine sequence number
            next_seq = (
                preferred_sequence
                if preferred_sequence is not None
                else current_assigned_count + 1
            )

            # Create or update RoutePickup
            route_pickup, created = RoutePickup.objects.get_or_create(
                route=route,
                pickup_request=pickup,
                defaults={
                    "sequence": next_seq,
                    "status": RoutePickup.StatusChoices.PENDING,
                },
            )
            if not created:
                route_pickup.sequence = next_seq
                route_pickup.status = RoutePickup.StatusChoices.PENDING
                route_pickup.save(update_fields=["sequence", "status"])

            # Synchronize PickupRequest
            pickup.status = PickupRequest.StatusChoices.ASSIGNED
            pickup.hub = route.hub
            pickup.city = route.hub.city
            pickup.distance_km = Decimal(str(dist_from_hub))
            if vehicle.driver:
                pickup.collector = vehicle.driver
            pickup.save()

            # Recalculate route total distance
            route.calculate_total_distance()
            route.save(update_fields=["total_distance_km"])

            # Update vehicle status if full
            new_count = current_assigned_count + 1
            if new_count >= max_cap:
                vehicle.status = Vehicle.StatusChoices.FULL
            else:
                vehicle.status = Vehicle.StatusChoices.ASSIGNED
            vehicle.save(update_fields=["status"])

            return route_pickup

    @classmethod
    def evaluate_route_suitability(cls, route: Route, pickup: PickupRequest) -> Dict[str, Any]:
        """
        Calculates whether a pickup request can suitably be inserted into an existing route.
        Evaluates capacity, hub radius, and incremental detour distance.
        """
        vehicle = route.vehicle
        current_stops = list(route.get_ordered_stops())
        current_count = len(current_stops)

        # 1. Capacity check
        max_cap = vehicle.max_capacity or cls.MAX_PICKUPS_PER_ROUTE
        if current_count >= max_cap:
            return {
                "suitable": False,
                "reason": "This vehicle has reached its maximum capacity of 5 pickups.",
                "detour_km": 0.0,
                "best_sequence": None,
            }

        # 2. Hub radius check
        dist_from_hub = GeoService.haversine_distance(
            float(route.hub.latitude),
            float(route.hub.longitude),
            float(pickup.effective_latitude),
            float(pickup.effective_longitude),
        )
        if dist_from_hub > cls.HUB_SERVICE_RADIUS_KM:
            return {
                "suitable": False,
                "reason": "This pickup location is more than 20 km from the service hub.",
                "detour_km": 0.0,
                "best_sequence": None,
            }

        # 3. Insertion detour calculation
        # Route waypoints: Hub -> Stop 1 -> Stop 2 -> ... -> Hub
        p_lat = float(pickup.effective_latitude)
        p_lng = float(pickup.effective_longitude)

        waypoints = [
            (float(route.hub.latitude), float(route.hub.longitude))
        ] + [
            (float(s.pickup_request.effective_latitude), float(s.pickup_request.effective_longitude))
            for s in current_stops
        ] + [
            (float(route.hub.latitude), float(route.hub.longitude))
        ]

        best_detour = float("inf")
        best_pos = 1

        for i in range(len(waypoints) - 1):
            w_prev = waypoints[i]
            w_next = waypoints[i + 1]
            orig_leg = GeoService.haversine_distance(w_prev[0], w_prev[1], w_next[0], w_next[1])
            new_leg = (
                GeoService.haversine_distance(w_prev[0], w_prev[1], p_lat, p_lng)
                + GeoService.haversine_distance(p_lat, p_lng, w_next[0], w_next[1])
            )
            detour = new_leg - orig_leg
            if detour < best_detour:
                best_detour = detour
                best_pos = i + 1

        # Check route corridor threshold (max acceptable detour: 20 km)
        is_suitable = best_detour <= 20.0
        return {
            "suitable": is_suitable,
            "reason": (
                "Pickup can be added to route."
                if is_suitable
                else "This pickup cannot be added to the current route because it is outside the permitted route area."
            ),
            "detour_km": round(best_detour, 2),
            "best_sequence": best_pos,
            "dist_from_hub_km": round(dist_from_hub, 2),
        }

    @classmethod
    def hold_pickup_request(cls, pickup_id: int, reason: Optional[str] = None) -> PickupRequest:
        """Places a pickup request into HELD status when no vehicle is available."""
        pickup = PickupRequest.objects.get(pk=pickup_id)
        pickup.status = PickupRequest.StatusChoices.HELD
        if reason:
            pickup.cancellation_reason = f"Held: {reason}"
        pickup.save()
        return pickup


# Backward-compatibility alias for legacy imports:
# from trashport.core.waste_management.services.route_service import RouteService
sys.modules["trashport.core.waste_management.services.route_service"] = sys.modules[__name__]
