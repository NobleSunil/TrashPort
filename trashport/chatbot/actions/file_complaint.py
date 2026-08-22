from .base import BaseChatAction
from typing import Dict, Any


class FileComplaintAction(BaseChatAction):
    def execute(self, user, text: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "reply": "I can help you file a complaint with our resolution team. Click below to submit details.",
            "action": "NAVIGATE",
            "url": "/complaints/new/",
            "button_text": "Submit Complaint",
        }
