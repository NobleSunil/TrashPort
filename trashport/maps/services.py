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
    def get_road_route_osrm(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> Dict:
        """
        Queries OSRM public demo routing service to get actual road coordinates, 
        distance, and travel duration following real turn-by-turn driving paths.
        Falls back to straight line if service is unavailable.
        """
        import requests
        url = f"https://router.project-osrm.org/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson"
        try:
            resp = requests.get(url, timeout=5)
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
                    
                    return {
                        "coordinates": leaflet_coords,
                        "distance_km": distance_km,
                        "duration_mins": duration_mins,
                        "provider": "osrm",
                    }
        except Exception as exc:
            pass

        # Fallback to straight line
        dist = GeoService.haversine_distance(start_lat, start_lng, end_lat, end_lng)
        duration = max(1, round((dist / 25.0) * 60))
        return {
            "coordinates": [[start_lat, start_lng], [end_lat, end_lng]],
            "distance_km": dist,
            "duration_mins": duration,
            "provider": "haversine_fallback",
        }
