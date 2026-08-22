from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseChatAction(ABC):
    @abstractmethod
    def execute(self, user, text: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes action logic and returns dictionary with 'reply', 'action', and optional payload.
        """
        pass
