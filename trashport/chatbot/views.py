from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .serializers import SendMessageSerializer
from .services.response_builder import ChatResponseBuilder


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
