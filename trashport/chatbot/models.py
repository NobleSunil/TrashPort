from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ChatSession {self.session_key} ({self.user})"


class ChatMessage(models.Model):
    class Senders(models.TextChoices):
        USER = "USER", "User"
        BOT = "BOT", "Bot"
        SYSTEM = "SYSTEM", "System"

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.CharField(max_length=10, choices=Senders.choices)
    text = models.TextField()
    intent = models.CharField(max_length=100, blank=True)
    action_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.sender}] {self.text[:40]}"
