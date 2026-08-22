import json
import logging
from .services.response_builder import ChatResponseBuilder

logger = logging.getLogger(__name__)

# Channels WebSocket consumer or async handler fallback
try:
    from channels.generic.websocket import AsyncWebsocketConsumer
    from channels.db import database_sync_to_async

    class ChatConsumer(AsyncWebsocketConsumer):
        async def connect(self):
            self.session_key = self.scope["url_route"]["kwargs"].get("session_key", "default")
            await self.accept()

        async def disconnect(self, close_code):
            pass

        async def receive(self, text_data):
            data = json.loads(text_data)
            user_text = data.get("message", "")
            user = self.scope.get("user")

            result = await database_sync_to_async(ChatResponseBuilder.process_user_message)(
                text=user_text,
                session_key=self.session_key,
                user=user,
            )
            await self.send(text_data=json.dumps(result))
except Exception:
    class ChatConsumer:
        """Fallback when channels is not installed."""
        pass
