from .base import BaseChatAction
from typing import Dict, Any
from trashport.core.waste_management.models import PickupRequest


class ChangeScheduleAction(BaseChatAction):
    def execute(self, user, text: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        pickup_id = slots.get("pickup_id")
        if not user or not user.is_authenticated:
            return {"reply": "Please sign in to reschedule your pickups."}

        if pickup_id:
            pickup = PickupRequest.objects.filter(id=pickup_id, user=user).first()
            if pickup:
                return {
                    "reply": f"Pickup #{pickup_id} is currently scheduled. Please visit the detail page to modify date/time.",
                    "action": "NAVIGATE",
                    "url": f"/pickups/{pickup_id}/",
                }

        latest = PickupRequest.objects.filter(user=user, status__in=["PENDING", "ASSIGNED"]).first()
        if latest:
            return {
                "reply": f"Your next upcoming pickup is #{latest.id}. Click to change schedule.",
                "action": "NAVIGATE",
                "url": f"/pickups/{latest.id}/",
            }

        return {"reply": "You don't have any active pending pickups to reschedule right now."}
