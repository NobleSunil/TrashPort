"""
trashport/maps/services.py — Geospatial Calculation and Routing Service
========================================================================

PURPOSE:
  Provides geospatial utilities for distance calculation and route generation.
  Used by the collector dashboard map to show pickup locations and by the
  admin live-map to display collector and pickup positions.

CONNECTION MAP:
  - trashport/collectors/views.py → GeoService.haversine_distance() to sort
                                    unassigned pickups by proximity to collector
  - trashport/maps/views.py       → get_road_route_osrm() for route line drawing
                                    on the Leaflet interactive map
  - trashport/maps/urls.py        → exposes /api/maps/road-route/ endpoint

THREE LEVELS OF ROUTING (in fallback order):
  1. OSRM (openstreetmap.de) : Real road-following routes via HTTP API.
                                Results cached 15 minutes in Django cache.
  2. Alternative OSRM server : router.project-osrm.org as second attempt.
  3. Street grid fallback     : generate_curved_road_waypoints() produces
                                realistic multi-turn city road paths locally
                                when both OSRM servers are unreachable.

IMPACT:
  - haversine_distance() is a straight-line estimate, NOT road distance.
    It is used for sorting only. Actual route distances come from OSRM.
  - If OSRM endpoints change, update the URL strings in get_road_route_osrm().
  - Cache TTL (900 seconds = 15 minutes) can be adjusted in get_road_route_osrm().
"""

import math
from typing import Tuple, List, Dict


class GeoService:
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculates the straight-line (great-circle) distance between two GPS points.

        Uses the Haversine formula which accounts for Earth's spherical shape.
        This gives the shortest distance over the earth's surface ("as the crow flies"),
        NOT the road driving distance.

        Used by: collectors/views.py to sort unassigned pickups by proximity.

        Args:
            lat1, lon1 : GPS coordinates of point A (e.g., collector position).
            lat2, lon2 : GPS coordinates of point B (e.g., pickup location).

        Returns:
            float: Distance in kilometers, rounded to 2 decimal places.

        Example:
            dist = GeoService.haversine_distance(9.9312, 76.2673, 10.0104, 76.3530)
            # Returns approximately 10.31 km
        """
        R = 6371.0  # Earth's radius in kilometers
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)

    @staticmethod
    def get_optimized_route(start: Tuple[float, float], waypoints: List[Tuple[float, float]]) -> List[Dict]:
        """
        Greedy nearest-neighbor path optimizer for collection vehicles.

        Orders a list of pickup waypoints to minimize total travel distance,
        starting from the collector's current position. Uses a greedy algorithm:
        always go to the nearest unvisited pickup next.

        Used by: Admin live-map and batch dispatch to suggest efficient routes.

        Args:
            start     : (lat, lon) tuple — starting position (collector's location).
            waypoints : List of (lat, lon) tuples — pickup locations to visit.

        Returns:
            List of dicts: [{"latitude": ..., "longitude": ..., "distance_from_prev_km": ...}, ...]
            Ordered from nearest to farthest in the greedy sequence.

        NOTE: This is O(n²) — not suitable for very large waypoint lists.
              For > 100 waypoints, consider a proper TSP solver.
        """
        if not waypoints:
            return []

        unvisited = list(waypoints)
        current = start
        route = []

        while unvisited:
            nearest = min(
                unvisited,
                key=lambda pt: GeoService.haversine_distance(current[0], current[1], pt[0], pt[1])
            )
            dist = GeoService.haversine_distance(current[0], current[1], nearest[0], nearest[1])
            route.append({
                "latitude": nearest[0],
                "longitude": nearest[1],
                "distance_from_prev_km": dist,
            })
            current = nearest
            unvisited.remove(nearest)

        return route

    @staticmethod
    def generate_curved_road_waypoints(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> List[List[float]]:
        """
        OFFLINE FALLBACK: Generates realistic multi-turn road-like waypoints
        without requiring any external API.

        When OSRM servers are unreachable, this function simulates a city street
        grid path using an L-shaped or S-shaped multi-leg route:
          Leg 1: Start → Street Turn 1    (60% of the way, offset laterally)
          Leg 2: Turn 1 → Street Turn 2   (85% of the way, offset back)
          Leg 3: Turn 2 → End             (final stretch)

        Micro-wobbles (sinusoidal offsets) are added along each leg to simulate
        real road curvature blocks instead of perfectly straight diagonal lines.

        Used by: get_road_route_osrm() as the 3rd-level fallback.

        IMPACT: The turn point offsets (0.60, 0.20, 0.12) control the shape of
                the simulated route. Adjust for more or fewer bends.
        """
        points = []
        dlat = end_lat - start_lat
        dlng = end_lng - start_lng
        dist_km = GeoService.haversine_distance(start_lat, start_lng, end_lat, end_lng)

        # Determine number of intermediate road turns based on distance
        num_segments = max(16, int(dist_km * 5))

        # Calculate primary street corner turn points (simulating L-shaped & S-shaped city road grid)
        # Point A -> Street Turn 1 -> Street Turn 2 -> Point B
        turn1_lat = start_lat + dlat * 0.60 + (dlng * 0.12)
        turn1_lng = start_lng + dlng * 0.20 - (dlat * 0.12)

        turn2_lat = start_lat + dlat * 0.85 - (dlng * 0.08)
        turn2_lng = start_lng + dlng * 0.75 + (dlat * 0.08)

        # Generate smooth multi-turn street road coordinates
        for i in range(num_segments + 1):
            t = i / float(num_segments)
            if t < 0.5:
                # First leg of road (Start to Turn 1)
                sub_t = t * 2.0
                lat = (1 - sub_t) * start_lat + sub_t * turn1_lat
                lng = (1 - sub_t) * start_lng + sub_t * turn1_lng
            elif t < 0.85:
                # Main city turn leg (Turn 1 to Turn 2)
                sub_t = (t - 0.5) / 0.35
                lat = (1 - sub_t) * turn1_lat + sub_t * turn2_lat
                lng = (1 - sub_t) * turn1_lng + sub_t * turn2_lng
            else:
                # Final street stretch (Turn 2 to End)
                sub_t = (t - 0.85) / 0.15
                lat = (1 - sub_t) * turn2_lat + sub_t * end_lat
                lng = (1 - sub_t) * turn2_lng + sub_t * end_lng

            # Add micro road curvature wobbles matching real street blocks
            wobble_lat = math.sin(t * math.pi * 4) * (dlat * 0.02)
            wobble_lng = math.cos(t * math.pi * 4) * (dlng * 0.02)

            points.append([round(lat + wobble_lat, 6), round(lng + wobble_lng, 6)])

        return points

    @staticmethod
    def get_road_route_osrm(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> Dict:
        """
        Gets real road-following route coordinates between two GPS points.

        FALLBACK CHAIN (tried in order):
          1. Django cache check: returns cached result if available (15 min TTL).
          2. router.project-osrm.org: Public OSRM demo server.
          3. routing.openstreetmap.de: Alternative routing server.
          4. generate_curved_road_waypoints(): Local offline fallback.

        Returns a dict:
          {
            "coordinates": [[lat, lon], [lat, lon], ...],  # Leaflet [lat, lon] format
            "distance_km": float,   # Road distance in km
            "duration_mins": int,   # Estimated travel time in minutes
            "provider": str,        # "osrm" or "street_grid_fallback"
          }

        Cache:
          Key format: osrm_route_{start_lat}_{start_lng}_{end_lat}_{end_lng}
          TTL: 900 seconds (15 minutes)

        IMPACT:
          - If OSRM server URLs change, update the endpoints list below.
          - Speed assumption for fallback duration: 25 km/h average city speed.
          - Coordinate format: OSRM returns [lon, lat] (GeoJSON) which is
            converted to Leaflet's [lat, lon] format in the response.
        """
        cache_key = f"osrm_route_{round(start_lat, 4)}_{round(start_lng, 4)}_{round(end_lat, 4)}_{round(end_lng, 4)}"
        try:
            from django.core.cache import cache
            cached_route = cache.get(cache_key)
            if cached_route and len(cached_route.get("coordinates", [])) > 2:
                return cached_route
        except Exception:
            cache = None

        import requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TrashPort/2.0",
            "Accept": "application/json"
        }

        endpoints = [
            f"https://router.project-osrm.org/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson",
            f"https://routing.openstreetmap.de/routed-car/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson",
        ]

        result = None
        for url in endpoints:
            try:
                resp = requests.get(url, headers=headers, timeout=2.5)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("routes") and len(data["routes"]) > 0:
                        first_route = data["routes"][0]
                        geojson_geometry = first_route.get("geometry", {})
                        raw_coords = geojson_geometry.get("coordinates", [])
                        # GeoJSON is [lon, lat] -> convert to Leaflet [lat, lon]
                        leaflet_coords = [[pt[1], pt[0]] for pt in raw_coords]
                        distance_km = round(first_route.get("distance", 0) / 1000.0, 2)
                        duration_mins = max(1, round(first_route.get("duration", 0) / 60.0))

                        if len(leaflet_coords) >= 2:
                            result = {
                                "coordinates": leaflet_coords,
                                "distance_km": distance_km,
                                "duration_mins": duration_mins,
                                "provider": "osrm",
                            }
                            break
            except Exception:
                continue

        if not result or len(result.get("coordinates", [])) <= 2:
            # Fallback to realistic multi-segment street road curve
            curved_waypoints = GeoService.generate_curved_road_waypoints(start_lat, start_lng, end_lat, end_lng)
            dist = GeoService.haversine_distance(start_lat, start_lng, end_lat, end_lng)
            duration = max(1, round((dist / 25.0) * 60))
            result = {
                "coordinates": curved_waypoints,
                "distance_km": dist,
                "duration_mins": duration,
                "provider": "street_grid_fallback",
            }

        try:
            if cache:
                cache.set(cache_key, result, 900)  # 15 minutes TTL
        except Exception:
            pass

        return result

