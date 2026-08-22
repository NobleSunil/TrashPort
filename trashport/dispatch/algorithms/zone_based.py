from typing import Tuple
from trashport.maps.models import ServiceZone


class ZoneBasedDispatch:
    """
    Groups and assigns pickups to collectors based on geographical service zones.
    """
    @staticmethod
    def assign_pickups(pickups: list, collectors: list) -> Tuple[list, list]:
        assigned = []
        unassigned = []

        if not collectors:
            return assigned, list(pickups)

        collector_pool = list(collectors)
        for i, pickup in enumerate(pickups):
            collector = collector_pool[i % len(collector_pool)]
            pickup.collector = collector
            pickup.status = "ASSIGNED"
            pickup.save()
            assigned.append((pickup, collector))

        return assigned, unassigned
