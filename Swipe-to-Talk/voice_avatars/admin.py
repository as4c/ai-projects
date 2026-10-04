from django.contrib import admin

from .models import ConversationSession


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "avatar_id", "status", "duration_seconds", "created_on")
    list_filter = ("status", "avatar_id")
    search_fields = ("id", "user__id", "user__username")
    readonly_fields = ("id", "created_on", "updated_on", "started_at", "ended_at")
    ordering = ("-created_on",)
