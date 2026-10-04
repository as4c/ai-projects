"""
Simple script to make a Twilio call
All configuration is in settings.py

Usage:
    From ai_researcher directory:
    python -m ai_researcher.twillio

    Or:
    cd ai_researcher && python twillio.py
"""
import os
import sys
import django

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_researcher.settings')
django.setup()

from twilio.rest import Client
from django.conf import settings

# Initialize Twilio client using settings
client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

# Destination number (must be verified on trial)
to_number = "+917491073491"

# Make call with recording enabled
# Use /twilio/call/ for GyanTV questionnaire flow
call = client.calls.create(
    to=to_number,
    from_=settings.TWILIO_PHONE_NUMBER,
    url=f"{settings.BASE_URL}/twilio/call/",  # GyanTV questionnaire endpoint
    # url=f"{settings.BASE_URL}/twilio/test-call/",  # Simple test endpoint (no questionnaire)
    method='POST',
    # Enable recording
    record=True,
    # Configure recording webhook
    recording_status_callback=f"{settings.BASE_URL}/twilio/recording-webhook/",
    recording_status_callback_method='POST',
    # Optional: Recording settings
    recording_channels='dual',  # or 'mono' for single channel
    recording_status_callback_event=['completed']  # Only completed events
)

print("Call initiated!")
print("Call SID:", call.sid)
print("Recording enabled: Yes")
print("Recording webhook:", f"{settings.BASE_URL}/twilio/recording-webhook/")
print("\nThe recording will be automatically saved when the call ends.")
