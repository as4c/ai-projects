"""
ElevenLabs Conversational AI Client
Handles real-time conversation with ElevenLabs API
"""
import os
import json
import requests
from django.conf import settings
from typing import Optional, Dict, Any


class ElevenLabsConversationalAI:
    """
    Client for ElevenLabs Conversational AI API
    Handles speech-to-text, LLM, and text-to-speech in one flow
    """

    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        # Detect data residency from API key and set correct endpoint
        if self.api_key.endswith('_residency_in'):
            # India data residency - use India endpoint
            self.base_url = "https://api.in.residency.elevenlabs.io/v1"
        elif self.api_key.endswith('_residency_eu'):
            # EU data residency - use EU endpoint
            self.base_url = "https://api.eu.residency.elevenlabs.io/v1"
        else:
            # Global endpoint
            self.base_url = "https://api.elevenlabs.io/v1"
        self.conversation_id = None

    def start_conversation(
        self,
        agent_id: Optional[str] = None,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Rachel voice
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Start a new conversation with ElevenLabs Conversational AI

        Args:
            agent_id: Optional agent ID (uses default if not provided)
            voice_id: Voice ID for TTS
            language: Language code

        Returns:
            Dictionary with conversation details
        """
        url = f"{self.base_url}/convai/conversation"

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "agent_id": agent_id,
            "voice_id": voice_id,
            "language": language
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.conversation_id = data.get("conversation_id")
            return data
        except requests.exceptions.RequestException as e:
            print(f"Error starting conversation: {e}")
            return {"error": str(e)}

    def send_audio_chunk(self, audio_data: bytes, conversation_id: str) -> Optional[bytes]:
        """
        Send audio chunk to conversation and get response audio

        Args:
            audio_data: Raw audio bytes (PCM, mu-law, or A-law)
            conversation_id: The conversation ID

        Returns:
            Response audio bytes or None
        """
        url = f"{self.base_url}/convai/conversation/{conversation_id}/audio"

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "audio/pcm"
        }

        try:
            response = requests.post(url, data=audio_data, headers=headers)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            print(f"Error sending audio: {e}")
            return None

    def send_text(self, text: str, conversation_id: str) -> Optional[bytes]:
        """
        Send text message and get audio response

        Args:
            text: Text message
            conversation_id: The conversation ID

        Returns:
            Response audio bytes or None
        """
        url = f"{self.base_url}/convai/conversation/{conversation_id}/text"

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "text": text
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            print(f"Error sending text: {e}")
            return None

    def end_conversation(self, conversation_id: str) -> bool:
        """
        End a conversation

        Args:
            conversation_id: The conversation ID

        Returns:
            True if successful
        """
        url = f"{self.base_url}/convai/conversation/{conversation_id}"

        headers = {
            "xi-api-key": self.api_key
        }

        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error ending conversation: {e}")
            return False


# Alternative: Simple TTS generation (fallback if Conversational AI not available)
def generate_voice_response(text: str, voice_id: str = None) -> Optional[bytes]:
    """
    Generate voice audio from text using ElevenLabs TTS
    Uses official SDK pattern from ElevenLabs docs

    Args:
        text: Text to convert to speech
        voice_id: Voice ID to use (default: from settings)

    Returns:
        Audio bytes or None
    """
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import VoiceSettings

        # Use voice_id from settings if not provided
        if voice_id is None:
            voice_id = settings.ELEVENLABS_VOICE_ID

        # Detect data residency and set correct base URL
        api_key = settings.ELEVENLABS_API_KEY
        if api_key.endswith('_residency_in'):
            # India data residency endpoint
            base_url = "https://api.in.residency.elevenlabs.io"
        elif api_key.endswith('_residency_eu'):
            # EU data residency endpoint
            base_url = "https://api.eu.residency.elevenlabs.io"
        else:
            # Global endpoint
            base_url = None  # SDK will use default global endpoint

        # Initialize client with appropriate base URL
        if base_url:
            elevenlabs = ElevenLabs(api_key=api_key, base_url=base_url)
        else:
            elevenlabs = ElevenLabs(api_key=api_key)

        # Call text_to_speech conversion API with optimized settings for low latency
        # Using faster settings: optimized voice settings (output format must be valid)
        response = elevenlabs.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_22050_32",  # Valid format - good balance of quality and speed
            text=text,
            model_id=settings.ELEVENLABS_MODEL_ID,  # Turbo model for low latency (good for calls)
            # Optimized voice settings for speed
            voice_settings=VoiceSettings(
                stability=0.0,  # Lower stability = faster generation
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,  # Disable speaker boost for faster processing
                speed=1.0,
            ),
        )

        # Collect audio bytes from streaming response
        audio_bytes = b""
        for chunk in response:
            if chunk:
                audio_bytes += chunk

        return audio_bytes

    except ImportError:
        # SDK not available, fallback to REST API
        print("ElevenLabs SDK not available, using REST API fallback")
        base_url = "https://api.elevenlabs.io"
        url = f"{base_url}/v1/text-to-speech/{voice_id}"

        headers = {
            "xi-api-key": settings.ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "text": text,
            "model_id": settings.ELEVENLABS_MODEL_ID,
            "output_format": "mp3_22050_32",  # Valid format - good balance of quality and speed
            "voice_settings": {
                "stability": 0.0,  # Lower stability = faster generation
                "similarity_boost": 1.0,
                "style": 0.0,
                "use_speaker_boost": False,  # Disable for faster processing
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            print(f"Error generating voice: {e}")
            return None

    except Exception as e:
        print(f"Error generating voice with SDK: {e}")
        import traceback
        traceback.print_exc()
        return None

