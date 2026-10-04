"""
Transcription Helper Functions
Uses factory pattern to support multiple providers
"""
from .transcription_providers import transcribe_audio as transcribe_with_provider


def transcribe_audio(audio_file_path: str, provider: str = None) -> str:
    """
    Main transcription function - uses factory pattern

    Args:
        audio_file_path: Path to audio file
        provider: Transcription provider name ('assemblyai', 'gemini', 'openai', 'whisper')
                 If None, uses default from settings

    Returns:
        Transcribed text or None if failed
    """
    return transcribe_with_provider(audio_file_path, provider)
