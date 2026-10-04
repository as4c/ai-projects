"""
Twilio Media Stream Handler
Handles WebSocket connections from Twilio Media Streams
"""
import json
import base64
import struct
from typing import Dict, Optional
from django.conf import settings
from .elevenlabs_client import ElevenLabsConversationalAI


class MediaStreamHandler:
    """
    Handles Twilio Media Stream WebSocket messages
    Processes audio and integrates with ElevenLabs
    """

    def __init__(self, call_sid: str):
        self.call_sid = call_sid
        self.elevenlabs_client = ElevenLabsConversationalAI()
        self.conversation_id = None
        self.audio_buffer = b""

    def handle_message(self, message: Dict) -> Optional[Dict]:
        """
        Handle incoming WebSocket message from Twilio

        Args:
            message: Parsed JSON message from Twilio

        Returns:
            Response message dict or None
        """
        event_type = message.get("event")

        if event_type == "connected":
            # Initialize ElevenLabs conversation when stream connects
            result = self.elevenlabs_client.start_conversation()
            if "conversation_id" in result:
                self.conversation_id = result["conversation_id"]
                print(f"Started ElevenLabs conversation: {self.conversation_id}")
            return {"event": "connected"}

        elif event_type == "start":
            # Stream started
            return {"event": "start"}

        elif event_type == "media":
            # Audio data received
            return self._handle_media(message)

        elif event_type == "stop":
            # Stream ended
            if self.conversation_id:
                self.elevenlabs_client.end_conversation(self.conversation_id)
            return {"event": "stop"}

        return None

    def _handle_media(self, message: Dict) -> Optional[Dict]:
        """
        Process incoming audio media

        Args:
            message: Media message from Twilio

        Returns:
            Response message with audio to send back
        """
        payload = message.get("media", {}).get("payload", "")

        if not payload or not self.conversation_id:
            return None

        try:
            # Decode base64 audio
            audio_data = base64.b64decode(payload)

            # Convert mu-law to PCM if needed (Twilio sends mu-law)
            # For now, send directly - ElevenLabs may handle conversion
            # You may need to convert mu-law to PCM depending on ElevenLabs requirements

            # Send to ElevenLabs and get response
            response_audio = self.elevenlabs_client.send_audio_chunk(
                audio_data,
                self.conversation_id
            )

            if response_audio:
                # Encode response audio to base64
                encoded_audio = base64.b64encode(response_audio).decode('utf-8')

                # Return media message to send back to Twilio
                return {
                    "event": "media",
                    "streamSid": message.get("streamSid"),
                    "media": {
                        "payload": encoded_audio
                    }
                }
        except Exception as e:
            print(f"Error handling media: {e}")

        return None

    def send_text_response(self, text: str) -> Optional[bytes]:
        """
        Send a text message and get audio response

        Args:
            text: Text message to send

        Returns:
            Audio bytes to play
        """
        if not self.conversation_id:
            return None

        return self.elevenlabs_client.send_text(text, self.conversation_id)

