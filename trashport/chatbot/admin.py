from django.contrib import admin
from .models import ChatSession, ChatMessage, FAQ, ChatFeedback, ChatLog


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "created_at", "updated_at")
    search_fields = ("session_key", "user__email")
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "sender", "intent", "created_at")
    list_filter = ("sender", "intent", "created_at")
    search_fields = ("text",)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ["question", "category", "is_active", "created_at"]
    list_filter = ["category", "is_active"]
    search_fields = ["question", "answer"]
    list_editable = ["is_active"]
    ordering = ["category", "question"]


@admin.register(ChatFeedback)
class ChatFeedbackAdmin(admin.ModelAdmin):
    list_display = ["user", "rating", "user_message", "bot_message", "created_at"]
    list_filter = ["rating"]
    search_fields = ["user__email", "user_message", "bot_message"]
    readonly_fields = [
        "user", "user_message", "bot_message", "rating",
        "session_key", "created_at",
    ]
    ordering = ["-created_at"]


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ["user", "was_valid", "action_taken", "created_at"]
    list_filter = ["was_valid", "action_taken"]
    search_fields = ["user__email", "user_message", "raw_llm_output"]
    readonly_fields = [
        "user", "user_message", "raw_llm_output", "parsed_output",
        "was_valid", "action_taken", "error_message", "created_at",
    ]
    ordering = ["-created_at"]
