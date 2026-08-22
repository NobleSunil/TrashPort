import re
from typing import Dict, Any


class SlotExtractor:
    """Extracts entities and slots like pickup ID, category, or numbers."""
    
    CATEGORIES = ["plastic", "organic", "wet", "dry", "e-waste", "ewaste", "paper", "metal", "glass", "hazardous"]

    @classmethod
    def extract_slots(cls, text: str) -> Dict[str, Any]:
        slots = {}
        lowered = text.lower()

        # Extract explicit pickup id (e.g. #123 or pickup 123)
        id_match = re.search(r"(?:#|pickup\s*#?)\s*(\d{1,6})", text, re.IGNORECASE)
        if id_match:
            slots["pickup_id"] = int(id_match.group(1))

        # Extract category match
        for cat in cls.CATEGORIES:
            if cat in lowered:
                slots["category"] = cat.capitalize()
                break

        return slots
