from .base import BaseChatAction
from typing import Dict, Any
from waste_management.models import PickupRequest


class CancelPickupAction(BaseChatAction):
    def execute(self, user, text: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        if not user or not user.is_authenticated:
            return {"reply": "Please sign in to cancel a collection request."}

        pickup_id = slots.get("pickup_id")
        if pickup_id:
            pickup = PickupRequest.objects.filter(id=pickup_id, user=user).first()
            if pickup:
                if pickup.status in ["PENDING", "ASSIGNED"]:
                    pickup.status = "CANCELLED"
                    pickup.save()
                    return {"reply": f"Pickup #{pickup_id} has been successfully cancelled."}
                return {"reply": f"Pickup #{pickup_id} cannot be cancelled because its status is {pickup.status}."}

        return {"reply": "Please specify the pickup ID you wish to cancel (e.g. 'cancel pickup #12')."}
