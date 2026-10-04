"""Models for the swipe-to-talk voice-avatar feature."""

import uuid

from django.conf import settings
from django.db import models


class ConversationSession(models.Model):
    """One row per right-swipe: a user's voice call with an AI avatar persona."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        ENDED = "ended", "Ended"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Opaque session id shared with the voice agent.",
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="voice_avatar_sessions",
        help_text="Swiper who started the call.",
    )
    avatar_id = models.CharField(
        max_length=64,
        help_text="Persona key from personas.PERSONAS.",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Lifecycle status of the call (pending -> active -> ended).",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the voice agent first connected to this session.",
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the call was hung up.",
    )
    duration_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Reported call duration in seconds.",
    )

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"], name="voice_avatars_user_status_idx"),
        ]

    def __str__(self) -> str:
        return f"ConversationSession<{self.id}:{self.avatar_id}>"
