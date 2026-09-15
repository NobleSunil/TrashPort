import logging
from django.contrib.auth import get_user_model
from waste_management.models import PickupRequest
from .models import DispatchBatch
from .algorithms import (
    NearestCollectorDispatch,
    LeastBusyCollectorDispatch,
    ZoneBasedDispatch,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class DispatchScheduler:
    @staticmethod
    def run_auto_dispatch(algorithm: str = "NEAREST", user=None) -> DispatchBatch:
        """
        Gathers unassigned pickups and runs the chosen dispatch algorithm.
        """
        unassigned_pickups = list(PickupRequest.objects.filter(collector__isnull=True, status="PENDING"))
        active_collectors = list(User.objects.filter(role=User.Roles.COLLECTOR, is_active=True))

        if algorithm == "LEAST_BUSY":
            assigned, unassigned = LeastBusyCollectorDispatch.assign_pickups(unassigned_pickups, active_collectors)
        elif algorithm == "ZONE_BASED":
            assigned, unassigned = ZoneBasedDispatch.assign_pickups(unassigned_pickups, active_collectors)
        else:
            algorithm = "NEAREST"
            assigned, unassigned = NearestCollectorDispatch.assign_pickups(unassigned_pickups, active_collectors)

        batch = DispatchBatch.objects.create(
            algorithm_used=algorithm,
            assigned_count=len(assigned),
            unassigned_count=len(unassigned),
            executed_by=user if getattr(user, "is_authenticated", False) else None,
            details={
                "assigned_pickups": [p.id for p, _ in assigned],
                "unassigned_pickups": [p.id for p in unassigned],
            }
        )

        logger.info(f"Auto-dispatch batch #{batch.id} executed with {algorithm}: {len(assigned)} assigned.")
        return batch
