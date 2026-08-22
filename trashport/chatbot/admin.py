from django.contrib import admin
from .models import ChatSession, ChatMessage


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
