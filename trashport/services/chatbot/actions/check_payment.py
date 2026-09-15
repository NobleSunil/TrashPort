from .base import BaseChatAction
from typing import Dict, Any


class CheckPaymentAction(BaseChatAction):
    def execute(self, user, text: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        if not user or not user.is_authenticated:
            return {"reply": "Please sign in to check your wallet points and payment history."}

        points = getattr(user, "wallet_points", 0)
        return {
            "reply": f"You currently have {points} green reward points in your wallet! Points can be redeemed on your next subscription renewal.",
            "points": points,
            "action": "NAVIGATE",
            "url": "/dashboard/",
        }
