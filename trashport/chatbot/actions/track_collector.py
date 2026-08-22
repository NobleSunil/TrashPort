from .base import BaseChatAction
from typing import Dict, Any
from waste_management.models import PickupRequest


class TrackCollectorAction(BaseChatAction):
    def execute(self, user, text: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        if not user or not user.is_authenticated:
            return {"reply": "Please sign in to view live collector tracking."}

        active_pickup = PickupRequest.objects.filter(
            user=user,
            status__in=["ASSIGNED", "IN_PROGRESS"],
            collector__isnull=False
        ).first()

        if active_pickup and active_pickup.collector:
            c_name = active_pickup.collector.name or "Collector"
            return {
                "reply": f"Your collector {c_name} is assigned to pickup #{active_pickup.id}. You can track live progress on the map.",
                "action": "TRACK_MAP",
                "pickup_id": active_pickup.id,
                "collector_id": active_pickup.collector.id,
            }

        return {"reply": "You don't currently have an assigned collection in progress."}
