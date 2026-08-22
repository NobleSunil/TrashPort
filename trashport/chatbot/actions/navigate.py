from .base import BaseChatAction
from typing import Dict, Any


class NavigateAction(BaseChatAction):
    def execute(self, user, text: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        lowered = text.lower()
        if "complaint" in lowered:
            return {"reply": "Opening Complaints page...", "action": "NAVIGATE", "url": "/complaints/"}
        elif "address" in lowered:
            return {"reply": "Opening Saved Addresses...", "action": "NAVIGATE", "url": "/addresses/"}
        elif "history" in lowered or "pickup" in lowered:
            return {"reply": "Opening Pickup History...", "action": "NAVIGATE", "url": "/dashboard/"}
        elif "tier" in lowered or "subscription" in lowered:
            return {"reply": "Opening Subscriptions...", "action": "NAVIGATE", "url": "/manage/tiers/"}
        
        return {"reply": "Taking you to your main dashboard...", "action": "NAVIGATE", "url": "/dashboard/"}
