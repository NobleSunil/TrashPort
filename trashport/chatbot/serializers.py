from rest_framework import serializers
from .models import ChatSession, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = "__all__"


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = ("id", "session_key", "created_at", "updated_at", "messages")


class SendMessageSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)
    session_key = serializers.CharField(required=False, allow_blank=True)
