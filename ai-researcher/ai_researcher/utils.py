# utils/voice.py
from elevenlabs import ElevenLabs
from django.conf import settings
import uuid
from typing import Optional, List

# Initialize ElevenLabs client
_elevenlabs_client = None


def get_elevenlabs_client():
    """Get or create ElevenLabs client instance"""
    global _elevenlabs_client
    if _elevenlabs_client is None:
        # Detect data residency and set correct base URL
        api_key = settings.ELEVENLABS_API_KEY
        if api_key.endswith('_residency_in'):
            # India data residency endpoint
            base_url = "https://api.in.residency.elevenlabs.io"
            _elevenlabs_client = ElevenLabs(api_key=api_key, base_url=base_url)
        elif api_key.endswith('_residency_eu'):
            # EU data residency endpoint
            base_url = "https://api.eu.residency.elevenlabs.io"
            _elevenlabs_client = ElevenLabs(api_key=api_key, base_url=base_url)
        else:
            # Global endpoint
            _elevenlabs_client = ElevenLabs(api_key=api_key)
    return _elevenlabs_client


def generate_voice(text, language="en"):
    """
    Generate voice audio using ElevenLabs TTS

    Args:
        text: Text to convert to speech
        language: Language code (en, hi, ta)

    Returns:
        Tuple of (file_path, filename)
    """
    voice_map = {
        "en": "Rachel",
        "hi": "Ananya",
        "ta": "Kumar",
    }

    client = get_elevenlabs_client()

    # Use the text-to-speech API
    audio_generator = client.text_to_speech.convert(
        voice_id=voice_map.get(language, "Rachel"),
        text=text,
        model_id="eleven_multilingual_v2"
    )

    # Collect audio bytes
    audio_bytes = b""
    for chunk in audio_generator:
        audio_bytes += chunk

    filename = f"audio_{uuid.uuid4()}.mp3"
    path = f"/tmp/{filename}"

    with open(path, "wb") as f:
        f.write(audio_bytes)

    return path, filename


def analyze_user_response_and_generate_followup(user_response: str, conversation_history: Optional[List[str]] = None) -> str:
    """
    Analyze user response and generate an intelligent follow-up question

    Args:
        user_response: The user's speech input
        conversation_history: Optional list of previous conversation turns

    Returns:
        Follow-up question text in English
    """
    # Try OpenAI first
    try:
        from openai import OpenAI

        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if api_key:
            client = OpenAI(api_key=api_key)

            # Build conversation context
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant conducting a phone conversation. "
                               "Your task is to analyze what the user said and ask a relevant, "
                               "engaging follow-up question in English. Keep your response concise "
                               "and natural, as if speaking in a phone call. Respond only with the "
                               "follow-up question, no additional commentary."
                }
            ]

            # Add conversation history if available
            if conversation_history:
                for i, turn in enumerate(conversation_history):
                    if i % 2 == 0:
                        messages.append({"role": "user", "content": turn})
                    else:
                        messages.append({"role": "assistant", "content": turn})

            # Add current user response
            messages.append({
                "role": "user",
                "content": f"User said: {user_response}\n\nGenerate a relevant follow-up question in English:"
            })

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )

            followup = response.choices[0].message.content.strip()
            if followup:
                return followup
    except (ImportError, Exception) as e:
        print(f"OpenAI analysis failed: {e}")

    # Fallback to Gemini
    try:
        try:
            from google import genai
            from google.genai import types
            use_new_package = True
        except ImportError:
            try:
                import google.generativeai as genai
                use_new_package = False
            except ImportError:
                raise ImportError("No LLM library available")

        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError("No API key available")

        prompt = (
            f"Analyze this user response and generate a relevant follow-up question in English. "
            f"Keep it concise and natural for a phone conversation.\n\n"
            f"User said: {user_response}\n\n"
            f"Generate only the follow-up question, nothing else:"
        )

        if use_new_package:
            client = genai.Client(api_key=api_key)
            # Use gemini-2.5-flash for fast response generation
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            followup = response.text.strip() if hasattr(response, 'text') and response.text else None
        else:
            genai.configure(api_key=api_key)
            # Use gemini-2.5-flash for fast response generation
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            followup = response.text.strip() if hasattr(response, 'text') else None

        if followup:
            return followup
    except Exception as e:
        print(f"Gemini analysis failed: {e}")

    # Final fallback: Simple template-based response
    return f"That's interesting! Can you tell me more about {user_response.lower()}?"
