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
