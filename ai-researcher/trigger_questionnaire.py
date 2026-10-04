#!/usr/bin/env python
"""
Quick script to trigger the GyanTV questionnaire call
Usage: python trigger_questionnaire.py [phone_number]
"""
import sys
from twilio.rest import Client
from django.conf import settings
import os
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_researcher.settings')
django.setup()

from ai_researcher.settings import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_PHONE_NUMBER,
    BASE_URL
)

# Get phone number from command line or use default
to_number = "+917491073491"  # Default number

# Initialize Twilio client using settings
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

print(f"Making call to: {to_number}")
print(f"Using endpoint: {BASE_URL}/twilio/call/")
print("-" * 50)

try:
    call = client.calls.create(
        to=to_number,
        from_=TWILIO_PHONE_NUMBER,
        url=f"{BASE_URL}/twilio/call/",  # Questionnaire endpoint
        method='POST',
        record=True,
        recording_status_callback=f"{BASE_URL}/twilio/recording-webhook/",
        recording_status_callback_method='POST',
        recording_channels='dual',
        recording_status_callback_event=['completed']
    )

    print("✅ Call initiated successfully!")
    print(f"Call SID: {call.sid}")
    print(f"Status: {call.status}")
    print(f"Recording: Enabled")
    print(f"\nThe questionnaire will start when the call is answered.")
    print(f"Recording will be saved automatically when the call ends.")

except Exception as e:
    print(f"❌ Error making call: {e}")
    sys.exit(1)

