import uuid
from ..models import ChatSession, ChatMessage


class ChatSessionManager:
    @staticmethod
    def get_or_create_session(session_key: str = None, user=None) -> ChatSession:
        if not session_key:
            session_key = uuid.uuid4().hex

        session, _ = ChatSession.objects.get_or_create(
            session_key=session_key,
            defaults={"user": user if getattr(user, "is_authenticated", False) else None}
        )
        if user and getattr(user, "is_authenticated", False) and not session.user:
            session.user = user
            session.save(update_fields=["user"])
        return session

    @staticmethod
    def log_message(session: ChatSession, sender: str, text: str, intent: str = "", action_data: dict = None) -> ChatMessage:
        return ChatMessage.objects.create(
            session=session,
            sender=sender,
            text=text,
            intent=intent,
            action_data=action_data or {},
        )
