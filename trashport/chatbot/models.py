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


class FAQ(models.Model):
    CATEGORY_CHOICES = [
        ("pickup", "Pickup"),
        ("payment", "Payment"),
        ("account", "Account"),
        ("general", "General"),
    ]
    question = models.CharField(max_length=500)
    answer = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="general")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "question"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return f"[{self.category}] {self.question[:80]}"


class ChatFeedback(models.Model):
    RATING_CHOICES = [
        ("thumbs_up", "👍 Thumbs Up"),
        ("thumbs_down", "👎 Thumbs Down"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    user_message = models.TextField()
    bot_message = models.TextField()
    rating = models.CharField(max_length=20, choices=RATING_CHOICES)
    session_key = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Chat Feedback"
        verbose_name_plural = "Chat Feedback"

    def __str__(self):
        return f"{self.rating} by {self.user} at {self.created_at:%Y-%m-%d %H:%M}"


class ChatLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    user_message = models.TextField()
    raw_llm_output = models.TextField()
    parsed_output = models.JSONField(default=dict)
    was_valid = models.BooleanField(default=True)
    action_taken = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Chat Log"
        verbose_name_plural = "Chat Logs"

    def __str__(self):
        valid = "✓" if self.was_valid else "✗"
        return f"{valid} {self.user} — {self.created_at:%Y-%m-%d %H:%M}"
