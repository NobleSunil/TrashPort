from typing import Tuple
from trashport.core.waste_management.models import PickupRequest


class LeastBusyCollectorDispatch:
    """
    Assigns pickups to the collector currently holding the fewest active assigned pickups.
    """
    @staticmethod
    def assign_pickups(pickups: list, collectors: list) -> Tuple[list, list]:
        assigned = []
        unassigned = []

        if not collectors:
            return assigned, list(pickups)

        # Build load map
        load_map = {
            c.id: PickupRequest.objects.filter(collector=c, status__in=["PENDING", "ASSIGNED"]).count()
            for c in collectors
        }

        for pickup in pickups:
            least_busy_collector_id = min(load_map, key=load_map.get)
            selected_collector = next(c for c in collectors if c.id == least_busy_collector_id)

            pickup.collector = selected_collector
            pickup.status = "ASSIGNED"
            pickup.save()

            load_map[least_busy_collector_id] += 1
            assigned.append((pickup, selected_collector))

        return assigned, unassigned
