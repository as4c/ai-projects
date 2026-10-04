"""Demo auth helpers for local testing without gyani JWT."""

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def demo_login(request):
    """Create/fetch a demo user and return a DRF auth token.

    Body (optional)::

        {"username": "demo", "password": "demo"}

    Defaults to username/password ``demo`` / ``demo``.
    """
    username = (request.data.get("username") or "demo").strip() or "demo"
    password = request.data.get("password") or "demo"

    user, created = User.objects.get_or_create(username=username)
    if created or not user.has_usable_password():
        user.set_password(password)
        user.save()

    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "username": user.username})
