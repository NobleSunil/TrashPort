import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client for LLM APIs (Gemini / OpenAI) with rule-based fallback.
    """
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

    def generate_response(self, prompt: str, user_text: str) -> Optional[str]:
        """Calls external LLM if configured; otherwise returns None for fallback."""
        if not self.gemini_key and not self.openai_key:
            return None
        # Stub for external LLM API
        return None
