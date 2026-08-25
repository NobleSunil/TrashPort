from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import SendMessageSerializer
from .services.response_builder import ChatResponseBuilder
from .models import ChatFeedback


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """SessionAuthentication subclass that skips CSRF enforcement.
    Safe for internal API endpoints called from our own JS widget (same-origin).
    """
    def enforce_csrf(self, request):
        return  # Skip CSRF check


@api_view(["POST"])
@permission_classes([AllowAny])
def send_chat_message_view(request):
    """REST endpoint to interact with TrashPort AI assistant."""
    serializer = SendMessageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    text = serializer.validated_data["message"]
    session_key = serializer.validated_data.get("session_key")

    response_data = ChatResponseBuilder.process_user_message(
        text=text,
        session_key=session_key,
        user=request.user if request.user.is_authenticated else None,
    )
    return Response(response_data, status=status.HTTP_200_OK)


class ChatFeedbackView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_message = request.data.get("user_message")
        bot_message = request.data.get("bot_message")
        rating = request.data.get("rating")
        session_key = request.data.get("session_key", "")

        # Validate required fields
        errors = {}
        if not user_message:
            errors["user_message"] = "This field is required."
        if not bot_message:
            errors["bot_message"] = "This field is required."
        if not rating:
            errors["rating"] = "This field is required."
        elif rating not in ("thumbs_up", "thumbs_down"):
            errors["rating"] = "Must be 'thumbs_up' or 'thumbs_down'."

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        ChatFeedback.objects.create(
            user=request.user,
            user_message=user_message,
            bot_message=bot_message,
            rating=rating,
            session_key=session_key,
        )

        return Response({"status": "ok"}, status=status.HTTP_201_CREATED)
