from typing import Tuple
from trashport.maps.services import GeoService
from django.contrib.auth import get_user_model

User = get_user_model()


class NearestCollectorDispatch:
    """
    Assigns pending pickup requests to the geographically nearest available collector.
    """
    @staticmethod
    def assign_pickups(pickups: list, collectors: list) -> Tuple[list, list]:
        assigned = []
        unassigned = []

        if not collectors:
            return assigned, list(pickups)

        for pickup in pickups:
            p_lat = getattr(pickup.address, "latitude", None)
            p_lon = getattr(pickup.address, "longitude", None)

            if p_lat is None or p_lon is None:
                # Default assign to first available collector if coordinates missing
                best_collector = collectors[0]
            else:
                best_collector = min(
                    collectors,
                    key=lambda c: (
                        GeoService.haversine_distance(
                            float(getattr(c.live_location, "latitude", p_lat)),
                            float(getattr(c.live_location, "longitude", p_lon)),
                            float(p_lat),
                            float(p_lon)
                        ) if hasattr(c, "live_location") else 9999.0
                    )
                )

            pickup.collector = best_collector
            pickup.status = "ASSIGNED"
            pickup.save()
            assigned.append((pickup, best_collector))

        return assigned, unassigned
