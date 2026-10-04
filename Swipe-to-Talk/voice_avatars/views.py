"""API for the swipe-to-talk voice-avatar feature."""

import logging

from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ConversationSession
from .permissions import IsVoiceAgentRequest
from .personas import PERSONAS, public_view

logger = logging.getLogger(__name__)


def can_start(user) -> bool:
    """Whether the user may start another avatar call.

    Free for the first ``VOICE_FREE_INTERACTIONS`` ended calls, then gated.

    :param user: The requesting user.
    :return: True if the user may start another call.
    """
    free = getattr(settings, "VOICE_FREE_INTERACTIONS", 100)
    ended = ConversationSession.objects.filter(
        user=user, status=ConversationSession.Status.ENDED
    ).count()
    if ended < free:
        return True
    return False


class VoiceAvatarViewSet(viewsets.ViewSet):
    """Swipe deck + match + call lifecycle for AI avatar personas."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="avatars")
    def avatars(self, request):
        """Return the public avatar catalogue for the swipe deck."""
        return Response({"avatars": [public_view(p) for p in PERSONAS.values()]})

    @action(detail=False, methods=["post"], url_path="match")
    def match(self, request):
        """Right-swipe: gate, create a session, return bot connection info."""
        avatar_id = str(request.data.get("avatar_id", ""))
        if avatar_id not in PERSONAS:
            return Response({"error": "unknown_avatar"}, status=status.HTTP_400_BAD_REQUEST)
        if not can_start(request.user):
            return Response(
                {"error": "locked", "reason": "min_spend"},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        session = ConversationSession.objects.create(user=request.user, avatar_id=avatar_id)
        logger.info(
            "voice_avatar_match_created",
            extra={"session_id": str(session.id), "avatar_id": avatar_id},
        )
        return Response(
            {
                "session_id": str(session.id),
                "avatar": public_view(PERSONAS[avatar_id]),
                "bot_url": settings.VOICE_BOT_URL,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="end")
    def end(self, request, pk=None):
        """Hang-up: mark the session ended and record its duration."""
        try:
            session = ConversationSession.objects.get(id=pk, user=request.user)
        except ConversationSession.DoesNotExist:
            return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

        session.status = ConversationSession.Status.ENDED
        session.duration_seconds = int(request.data.get("duration_seconds") or 0)
        session.ended_at = timezone.now()
        session.save(update_fields=["status", "duration_seconds", "ended_at", "updated_on"])
        return Response(
            {
                "duration_seconds": session.duration_seconds,
                "next_locked": not can_start(request.user),
            }
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="internal",
        authentication_classes=[],
        permission_classes=[IsVoiceAgentRequest],
    )
    def internal(self, request, pk=None):
        """Voice-agent only: return the private persona (prompt + voice) for a session."""
        try:
            session = ConversationSession.objects.get(id=pk)
        except ConversationSession.DoesNotExist:
            return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

        persona = PERSONAS.get(session.avatar_id)
        if not persona:
            return Response({"error": "unknown_avatar"}, status=status.HTTP_404_NOT_FOUND)

        if session.status == ConversationSession.Status.PENDING:
            session.status = ConversationSession.Status.ACTIVE
            session.started_at = timezone.now()
            session.save(update_fields=["status", "started_at", "updated_on"])

        return Response(
            {key: persona[key] for key in ("system_prompt", "voice_id", "first_message", "lang")}
        )
