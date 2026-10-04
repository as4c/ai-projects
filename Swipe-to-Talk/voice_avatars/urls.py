from django.urls import include, re_path
from rest_framework import routers

from .views import VoiceAvatarViewSet

router = routers.DefaultRouter()
router.register(prefix=r"", viewset=VoiceAvatarViewSet, basename="voice-avatars")

urlpatterns = [re_path(r"^", include(router.urls))]
