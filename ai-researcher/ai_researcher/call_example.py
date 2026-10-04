"""
Example script showing how to use Twilio + ElevenLabs integration
"""
from twilio.rest import Client
from django.conf import settings

# Make an outbound call
def make_ai_call(to_number: str):
    """
    Make an outbound call that connects to AI agent

    Args:
        to_number: Phone number to call (E.164 format)
    """
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    call = client.calls.create(
        to=to_number,
        from_=settings.TWILIO_PHONE_NUMBER,
        url=f"{settings.BASE_URL}/twilio/call/",  # This endpoint uses Gather + ElevenLabs
        method='POST'
    )

    print(f"Call initiated! SID: {call.sid}")
    return call


# Example usage:
# make_ai_call("+1234567890")
