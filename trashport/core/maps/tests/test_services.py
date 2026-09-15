from trashport.core.maps.services import GeoService


class TestGeoService:
    def test_haversine_distance(self):
        # Distance between Bangalore coordinates
        lat1, lon1 = 12.9716, 77.5946
        lat2, lon2 = 12.9352, 77.6245
        dist = GeoService.haversine_distance(lat1, lon1, lat2, lon2)
        assert dist > 0
        assert dist < 10  # ~5.2 km

    def test_optimized_route(self):
        start = (12.9716, 77.5946)
        waypoints = [
            (12.9352, 77.6245),
            (12.9750, 77.6000),
            (13.0000, 77.5800),
        ]
        route = GeoService.get_optimized_route(start, waypoints)
        assert len(route) == 3
        assert "latitude" in route[0]
        assert "distance_from_prev_km" in route[0]
