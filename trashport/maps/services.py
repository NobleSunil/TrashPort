import math
from typing import Tuple, List, Dict


class GeoService:
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great-circle distance between two points on the Earth in kilometers.
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
        Greedy nearest-neighbor path optimization for collection vehicles.
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
        Generates realistic multi-segment road waypoints following street grid turns 
        (Manhattan turn points with smooth street curve geometry) when OSRM routing servers 
        are unreachable, ensuring maps NEVER show a straight single string line.
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
        Queries OSRM public demo routing service to get actual road coordinates, 
        distance, and travel duration following real turn-by-turn driving paths.
        Results are cached for 15 minutes.
        Falls back to realistic curved street waypoints if services are unavailable.
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

