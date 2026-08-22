import re
from .intents import IntentType


class IntentClassifier:
    """Rule-based and heuristic intent classifier with LLM fallback support."""
    
    INTENT_KEYWORDS = {
        IntentType.SCHEDULE_PICKUP: ["schedule", "book", "new pickup", "collect trash", "pickup my waste", "request collection"],
        IntentType.CHANGE_SCHEDULE: ["reschedule", "change time", "postpone", "move pickup", "change date"],
        IntentType.CANCEL_PICKUP: ["cancel pickup", "cancel collection", "abort pickup", "don't come"],
        IntentType.TRACK_COLLECTOR: ["track", "where is", "collector location", "eta", "status of collector", "on the way"],
        IntentType.FILE_COMPLAINT: ["complaint", "report issue", "bad service", "missed pickup", "not collected", "problem"],
        IntentType.CHECK_PAYMENT: ["wallet", "points", "balance", "price", "how much", "cost", "payment"],
        IntentType.NAVIGATE: ["go to", "open", "show me", "take me to", "navigate", "dashboard"],
    }

    @classmethod
    def classify(cls, text: str) -> IntentType:
        lowered = text.lower().strip()
        for intent, keywords in cls.INTENT_KEYWORDS.items():
            if any(kw in lowered for kw in keywords):
                return intent
        return IntentType.GENERAL_ANSWER
