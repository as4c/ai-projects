"""
URL configuration for ai_researcher project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from .views import (
    serve_audio,
    twilio_voice,
    incoming_call,
    call_with_gather,
    process_speech,
    make_outbound_call,
    trigger_call_with_questionnaire,
    receive_event,
    twilio_recording_webhook,
    simple_test_call
)

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("audio/<str:filename>/", serve_audio),
    path("twilio/voice/", twilio_voice),
    path("twilio/call/", call_with_gather, name="twilio_call"),
    path("twilio/test-call/", simple_test_call, name="simple_test_call"),
    path("twilio/incoming/", incoming_call, name="twilio_incoming"),
    path("twilio/process-speech/", process_speech, name="process_speech"),
    path("twilio/make-call/", make_outbound_call, name="make_call"),
    path("api/trigger-call/", trigger_call_with_questionnaire, name="trigger_call"),
    path("api/events/", receive_event, name="receive_event"),
    path("twilio/recording-webhook/", twilio_recording_webhook,
         name="twilio_recording_webhook"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
