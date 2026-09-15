from .base import BaseChatAction
from typing import Dict, Any
from django.urls import reverse


class SchedulePickupAction(BaseChatAction):
    def execute(self, user, text: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        category = slots.get("category", "Recyclables")
        reply = (
            f"I can help you book a {category} pickup! "
            f"Click below to choose your preferred time slot and address."
        )
        return {
            "reply": reply,
            "action": "NAVIGATE",
            "url": reverse("waste_management:pickup_create"),
            "button_text": "Book Pickup Now",
        }
