import json
import logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

from trashport.firebase.utils import verify_firebase_id_token
from trashport.firebase.exceptions import FirebaseAuthenticationError
from waste_management.models import PickupRequest

from .system_prompt import build_system_prompt
from .services.groq_service import chat, log_interaction
from .services.intent_parser import parse_response
from .services.action_handler import execute_action
from .models import FAQ
from trashport.chatbot.rate_limiter import ChatbotRateLimiter

logger = logging.getLogger(__name__)
User = get_user_model()

# Known fallback messages produced by parse_response when parsing fails
FALLBACK_MESSAGES = {
    "Something went wrong. Try again.",
    "I can only help with TrashPort-related questions.",
}

def _get_user_by_uid(uid):
    user = User.objects.filter(firebase_uid=uid).first()
    if not user:
        user = User.objects.filter(email__iexact=uid).first()
    return user

def _get_active_pickups(user):
    return list(PickupRequest.objects.filter(citizen=user).exclude(status="CANCELLED"))

class ChatbotConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that handles Firebase-authenticated waste management chat sessions.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rate_limiter = ChatbotRateLimiter()

    async def connect(self):
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token_list = params.get("token", [])
        token = token_list[0] if token_list else None

        if not token:
            logger.warning("WebSocket connection rejected: token missing from query parameters.")
            await self.close(code=4001)
            return

        try:
            decoded_token = verify_firebase_id_token(token)
            uid = decoded_token.get("uid")
            if not uid:
                raise FirebaseAuthenticationError("Decoded token is missing uid.")

            user = await sync_to_async(_get_user_by_uid)(uid)
            if not user:
                logger.warning(f"WebSocket connection rejected: User with uid {uid} does not exist.")
                await self.close(code=4001)
                return

            self.user = user
            await self.accept()

            name = user.name or user.email
            await self.send(json.dumps({
                "type": "text",
                "message": f"Hi {name}! How can I help you today?"
            }))

        except Exception as e:
            logger.error(f"Authentication failure during WebSocket connect: {e}")
            await self.close(code=4001)

    async def disconnect(self, code):
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get("message", "")
            history = data.get("history", [])

            # Check rate limits
            uid = self.user.firebase_uid or str(self.user.id)
            allowed, remaining = await sync_to_async(self.rate_limiter.is_allowed)(uid)

            if not allowed:
                retry_after = await sync_to_async(self.rate_limiter.get_retry_after)(uid)
                await self.send(json.dumps({
                    "type": "error",
                    "code": "RATE_LIMITED",
                    "message": f"Too many messages. Try again in {retry_after} seconds.",
                    "retry_after": retry_after,
                }))
                return

            # Load user pickups
            pickups = await sync_to_async(_get_active_pickups)(self.user)

            # Load active FAQs
            faqs = await sync_to_async(
                lambda: list(FAQ.objects.filter(is_active=True))
            )()

            # Build LLM context window
            system_content = await sync_to_async(build_system_prompt)(self.user, pickups, faqs)
            messages = [{"role": "system", "content": system_content}]
            
            # Avoid duplicating the current message if it's already at the end of history
            clean_history = list(history[-10:])
            if clean_history and clean_history[-1].get("content") == message and clean_history[-1].get("role") == "user":
                messages.extend(clean_history)
            else:
                messages.extend(clean_history)
                messages.append({"role": "user", "content": message})

            # Call Groq completion
            raw = await chat(messages)

            # Parse response intent
            parsed = parse_response(raw)

            # Determine validity — fallback messages indicate a parse failure
            was_valid = parsed.get("message") not in FALLBACK_MESSAGES

            # Execute action if matching action intent
            if parsed.get("type") == "action":
                parsed = await execute_action(self.user, parsed)

            # Determine action taken for logging
            action_taken = parsed.get("action", "") if parsed.get("type") == "action" else ""

            # Log the interaction
            await log_interaction(
                user=self.user,
                user_message=message,
                raw=raw,
                parsed=parsed,
                was_valid=was_valid,
                action_taken=action_taken,
            )

            await self.send(json.dumps(parsed))

        except Exception as e:
            logger.error(f"Error handling message receive: {e}", exc_info=True)
            await self.send(json.dumps({
                "type": "text",
                "message": "Something went wrong. Try again."
            }))
