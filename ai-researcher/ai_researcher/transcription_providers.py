"""
Transcription Provider Factory/Strategy Pattern
Supports multiple transcription providers: AssemblyAI, Gemini, OpenAI Whisper
"""
from abc import ABC, abstractmethod
from typing import Optional
from django.conf import settings


class TranscriptionProvider(ABC):
    """Base class for transcription providers"""

    @abstractmethod
    def transcribe(self, audio_file_path: str) -> Optional[str]:
        """
        Transcribe audio file to text

        Args:
            audio_file_path: Path to audio file

        Returns:
            Transcribed text or None if transcription fails
        """
        pass


class AssemblyAIProvider(TranscriptionProvider):
    """AssemblyAI transcription provider"""

    def transcribe(self, audio_file_path: str) -> Optional[str]:
        """Transcribe audio using AssemblyAI"""
        try:
            import assemblyai as aai

            api_key = getattr(settings, 'ASSEMBLYAI_API_KEY', None)
            if not api_key:
                print("AssemblyAI API key not found, skipping transcription")
                return None

            aai.settings.api_key = api_key
            config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.best)
            transcript = aai.Transcriber(config=config).transcribe(audio_file_path)

            if transcript.status == aai.TranscriptStatus.completed and transcript.text:
                return transcript.text

            return None

        except ImportError:
            print("AssemblyAI library not installed. Install with: pip install assemblyai")
            return None
        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg or 'quota' in error_msg.lower():
                print(f"AssemblyAI quota exceeded - transcription failed (non-critical)")
            elif '401' in error_msg or 'invalid' in error_msg.lower() or 'authentication' in error_msg.lower():
                print(f"AssemblyAI API key issue - transcription failed (non-critical)")
            else:
                print(f"AssemblyAI transcription error (non-critical): {e}")

            if '429' not in error_msg and 'quota' not in error_msg.lower() and '401' not in error_msg:
                import traceback
                traceback.print_exc()

            return None


class GeminiProvider(TranscriptionProvider):
    """Google Gemini transcription provider"""

    def transcribe(self, audio_file_path: str) -> Optional[str]:
        """Transcribe audio using Google Gemini API"""
        try:
            # Try new google.genai package first
            try:
                from google import genai
                from google.genai import types
                use_new_package = True
            except ImportError:
                # Fallback to old package
                try:
                    import google.generativeai as genai
                    use_new_package = False
                except ImportError:
                    print("Google GenAI library not installed. Install with: pip install google-genai")
                    return None

            api_key = getattr(settings, 'GEMINI_API_KEY', None)
            if not api_key:
                print("Gemini API key not found, skipping transcription")
                return None

            with open(audio_file_path, 'rb') as f:
                audio_bytes = f.read()

            import mimetypes
            mime_type, _ = mimetypes.guess_type(audio_file_path)
            if not mime_type:
                mime_type = "audio/mpeg"

            prompt_text = "Please transcribe the speech from this audio file. Return only the transcribed text without any additional commentary, timestamps, or formatting."

            if use_new_package:
                client = genai.Client(api_key=api_key)

                # Create parts for transcription
                try:
                    audio_part = types.Part(
                        inline_data=types.Blob(
                            mime_type=mime_type,
                            data=audio_bytes
                        )
                    )
                    text_part = types.Part(text=prompt_text)
                    parts = [audio_part, text_part]
                except Exception as e1:
                    print(f"Error creating parts with new package: {e1}")
                    return None

                # Use gemini-2.5-flash for transcription (fast and cost-efficient)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=parts
                )
                transcript_text = response.text.strip()
            else:
                genai.configure(api_key=api_key)
                # Use gemini-2.5-flash for transcription (fast and cost-efficient)
                model = genai.GenerativeModel('gemini-2.5-flash')

                # Upload audio file
                audio_file = genai.upload_file(path=audio_file_path, mime_type=mime_type)

                response = model.generate_content([prompt_text, audio_file])
                transcript_text = response.text.strip()

            return transcript_text

        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg or 'quota' in error_msg.lower():
                print(f"Gemini quota exceeded - transcription failed (non-critical)")
            elif '401' in error_msg or 'invalid' in error_msg.lower() or 'authentication' in error_msg.lower():
                print(f"Gemini API key issue - transcription failed (non-critical)")
            else:
                print(f"Gemini transcription error (non-critical): {e}")

            if '429' not in error_msg and 'quota' not in error_msg.lower() and '401' not in error_msg:
                import traceback
                traceback.print_exc()

            return None


class OpenAIWhisperProvider(TranscriptionProvider):
    """OpenAI Whisper transcription provider"""

    def transcribe(self, audio_file_path: str) -> Optional[str]:
        """Transcribe audio using OpenAI Whisper API"""
        try:
            from openai import OpenAI

            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not api_key:
                print("OpenAI API key not found, skipping transcription")
                return None

            client = OpenAI(api_key=api_key)

            with open(audio_file_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="hi"  # Hindi, can be made configurable
                )

            return transcript.text.strip()

        except ImportError:
            print("OpenAI library not installed. Install with: pip install openai")
            return None
        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg or 'quota' in error_msg.lower() or 'insufficient_quota' in error_msg.lower():
                print(f"OpenAI quota exceeded - transcription failed (non-critical)")
            elif '401' in error_msg or 'invalid' in error_msg.lower() or 'authentication' in error_msg.lower():
                print(f"OpenAI API key issue - transcription failed (non-critical)")
            else:
                print(f"OpenAI Whisper transcription error (non-critical): {e}")

            if '429' not in error_msg and 'quota' not in error_msg.lower() and '401' not in error_msg:
                import traceback
                traceback.print_exc()

            return None


class TranscriptionProviderFactory:
    """Factory to create transcription provider instances"""

    PROVIDERS = {
        'assemblyai': AssemblyAIProvider,
        'assembly': AssemblyAIProvider,  # Alias
        'aai': AssemblyAIProvider,  # Alias
        'gemini': GeminiProvider,
        'openai': OpenAIWhisperProvider,
        'whisper': OpenAIWhisperProvider,  # Alias
    }

    @staticmethod
    def create_provider(provider_name: str = None) -> Optional[TranscriptionProvider]:
        """
        Create a transcription provider instance

        Args:
            provider_name: Name of provider ('assemblyai', 'gemini', 'openai', 'whisper')
                          If None, uses default from settings or 'assemblyai'

        Returns:
            TranscriptionProvider instance or None if provider not found
        """
        # If no provider specified, check settings or use default
        if not provider_name:
            provider_name = getattr(settings, 'DEFAULT_TRANSCRIPTION_PROVIDER', 'gemini')

        provider_name = provider_name.lower().strip()

        # Check if provider class exists
        provider_class = TranscriptionProviderFactory.PROVIDERS.get(provider_name)
        if not provider_class:
            print(f"Unknown transcription provider: {provider_name}. Available: {list(TranscriptionProviderFactory.PROVIDERS.keys())}")
            # Fallback to assemblyai
            provider_class = AssemblyAIProvider

        try:
            return provider_class()
        except Exception as e:
            print(f"Error creating transcription provider {provider_name}: {e}")
            return None

    @staticmethod
    def get_available_providers() -> list:
        """Get list of available provider names"""
        return list(TranscriptionProviderFactory.PROVIDERS.keys())


# Convenience function
def transcribe_audio(audio_file_path: str, provider: str = None) -> Optional[str]:
    """
    Transcribe audio using specified provider

    Args:
        audio_file_path: Path to audio file
        provider: Transcription provider name ('assemblyai', 'gemini', 'openai', 'whisper')
                 If None, uses default from settings

    Returns:
        Transcribed text or None if transcription fails
    """
    transcription_provider = TranscriptionProviderFactory.create_provider(provider)
    if not transcription_provider:
        return None

    return transcription_provider.transcribe(audio_file_path)

