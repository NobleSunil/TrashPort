from ..intent.classifier import IntentClassifier
from ..intent.slot_extractor import SlotExtractor
from ..actions import ACTION_ROUTER
from .session_manager import ChatSessionManager


class ChatResponseBuilder:
    @classmethod
    def process_user_message(cls, text: str, session_key: str = None, user=None) -> dict:
        session = ChatSessionManager.get_or_create_session(session_key, user)
        
        # Log user message
        ChatSessionManager.log_message(session, "USER", text)

        # Classify intent & extract slots
        intent = IntentClassifier.classify(text)
        slots = SlotExtractor.extract_slots(text)

        # Route action
        action_handler = ACTION_ROUTER.get(intent)
        if action_handler:
            result = action_handler.execute(user=user, text=text, slots=slots)
        else:
            result = {"reply": "I'm not sure how to assist with that yet. Can I help you book a pickup?"}

        reply_text = result.get("reply", "")
        ChatSessionManager.log_message(
            session=session,
            sender="BOT",
            text=reply_text,
            intent=str(intent),
            action_data=result,
        )

        return {
            "session_key": session.session_key,
            "intent": str(intent),
            "slots": slots,
            "reply": reply_text,
            "action_data": result,
        }
