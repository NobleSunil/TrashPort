from .base import BaseChatAction
from typing import Dict, Any


class GeneralAnswerAction(BaseChatAction):
    def execute(self, user, text: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        lowered = text.lower()
        if any(w in lowered for w in ["hi", "hello", "hey", "help"]):
            return {
                "reply": "Hello! I am your TrashPort AI assistant. I can help you schedule a pickup, check waste categories, track collectors, or answer recycling questions."
            }
        elif "recycle" in lowered or "segregate" in lowered or "dry" in lowered or "wet" in lowered:
            return {
                "reply": "Waste Segregation Tip: Keep Dry waste (paper, plastic, glass) separate from Wet organic waste (food scraps). E-waste and batteries should be booked for hazardous collection."
            }
        
        return {
            "reply": "I'm here to assist with all your TrashPort waste logistics needs. Would you like to schedule a pickup or view available services?"
        }
