"""
Voice Mapper - Maps languages to ElevenLabs voice IDs and Twilio language codes
"""
from typing import Dict, Optional
from django.conf import settings


# Language to ElevenLabs Voice ID mapping
LANGUAGE_VOICE_MAP: Dict[str, str] = {
    # Hindi/Hinglish voices
    'hi': 'EXAVITQu4vr4xnSDxMaL',  # Ananya - Hindi voice
    'hin': 'EXAVITQu4vr4xnSDxMaL',  # Alias for Hindi
    'hinglish': 'EXAVITQu4vr4xnSDxMaL',  # Hinglish

    # English voices
    'en': '21m00Tcm4TlvDq8ikWAM',  # Rachel - English voice
    'eng': '21m00Tcm4TlvDq8ikWAM',  # Alias for English

    # Add more languages as needed
    # 'es': 'voice_id_for_spanish',
    # 'fr': 'voice_id_for_french',
    # etc.
}

# Language to Twilio Gather language code mapping
# Twilio uses BCP 47 language tags for speech recognition
LANGUAGE_TWILIO_MAP: Dict[str, str] = {
    # Hindi/Hinglish
    'hi': 'hi-IN',  # Hindi (India)
    'hin': 'hi-IN',
    'hinglish': 'hi-IN',

    # English
    'en': 'en-US',  # English (United States)
    'eng': 'en-US',
    'en-us': 'en-US',
    'en-gb': 'en-GB',  # English (United Kingdom)

    # Add more languages as needed
    # 'es': 'es-ES',  # Spanish (Spain)
    # 'es-mx': 'es-MX',  # Spanish (Mexico)
    # 'fr': 'fr-FR',  # French (France)
    # 'de': 'de-DE',  # German
    # etc.
}


def get_voice_id_for_language(language: str = None) -> str:
    """
    Get ElevenLabs voice ID for a given language

    Args:
        language: Language code (e.g., 'hi', 'en', 'hinglish')
                 If None, uses default from settings

    Returns:
        ElevenLabs voice ID
    """
    if not language:
        # Use default from settings
        return getattr(settings, 'ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')

    language = language.lower().strip()

    # Check direct mapping
    if language in LANGUAGE_VOICE_MAP:
        return LANGUAGE_VOICE_MAP[language]

    # Check if it's a partial match (e.g., 'hindi' contains 'hi')
    for lang_code, voice_id in LANGUAGE_VOICE_MAP.items():
        if lang_code in language or language in lang_code:
            return voice_id

    # Default fallback
    return getattr(settings, 'ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')


def get_twilio_language_code(language: str = None) -> str:
    """
    Get Twilio Gather language code for a given language

    Args:
        language: Language code (e.g., 'hi', 'en', 'hinglish')
                 If None, uses default 'hi-IN'

    Returns:
        Twilio language code (e.g., 'hi-IN', 'en-US')
    """
    if not language:
        # Default to Hindi
        return 'hi-IN'

    language = language.lower().strip()

    # Check direct mapping
    if language in LANGUAGE_TWILIO_MAP:
        return LANGUAGE_TWILIO_MAP[language]

    # Check if it's a partial match (e.g., 'hindi' contains 'hi')
    for lang_code, twilio_code in LANGUAGE_TWILIO_MAP.items():
        if lang_code in language or language in lang_code:
            return twilio_code

    # Default fallback
    return 'hi-IN'


def get_available_languages() -> list:
    """Get list of available language codes"""
    return list(LANGUAGE_VOICE_MAP.keys())


def get_available_twilio_languages() -> list:
    """Get list of available Twilio language codes"""
    return list(set(LANGUAGE_TWILIO_MAP.values()))

