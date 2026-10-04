"""Permissions for the voice-avatar feature."""

import hmac

from django.conf import settings
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

BOT_KEY_HEADER = "x-voice-bot-key"


class IsVoiceAgentRequest(permissions.BasePermission):
    """Authorizes the voice agent's internal persona lookup via a shared-key header.

    The agent sends ``x-voice-bot-key`` which is compared against
    ``settings.VOICE_BOT_AUTH_KEY`` using a constant-time comparison.
    """

    def has_permission(self, request, view) -> bool:
        api_key = request.headers.get(BOT_KEY_HEADER)
        expected_key = getattr(settings, "VOICE_BOT_AUTH_KEY", None)
        if not (api_key and expected_key and hmac.compare_digest(api_key, expected_key)):
            raise PermissionDenied("Invalid or missing voice bot key")
        return True
