"""
Questionnaire Translator - Translates questionnaires to multiple languages using LLM
"""
from typing import Dict, List, Optional
from django.conf import settings
from .llm_providers import LLMProviderFactory


def translate_questionnaire(text: str, target_language: str, source_language: str = 'en', provider: str = None) -> Optional[str]:
    """
    Translate questionnaire text to target language using LLM

    Args:
        text: Text to translate
        target_language: Target language code (e.g., 'hi', 'en')
        source_language: Source language code (default: 'en')
        provider: LLM provider to use (default: from settings)

    Returns:
        Translated text or None if translation fails
    """
    try:
        # Get LLM provider - use translation-specific provider if available
        if not provider:
            provider = getattr(settings, 'DEFAULT_TRANSLATION_PROVIDER', None)
            # Fallback to DEFAULT_LLM_PROVIDER if translation provider not set
            if not provider:
                provider = getattr(settings, 'DEFAULT_LLM_PROVIDER', 'gemini')

        llm_provider = LLMProviderFactory.create_provider(provider)
        if not llm_provider:
            print(f"Could not create LLM provider: {provider}")
            return None

        # Build translation prompt
        language_names = {
            'hi': 'Hindi',
            'en': 'English',
            'hinglish': 'Hinglish (Hindi-English mix)'
        }

        target_lang_name = language_names.get(target_language.lower(), target_language)
        source_lang_name = language_names.get(source_language.lower(), source_language)

        # For Hindi, use Hinglish style (mix of Hindi and English)
        if target_language.lower() in ['hi', 'hin', 'hinglish']:
            target_display = "Hinglish (Hindi-English mix)"
            style_instruction = "Use natural Hinglish style - mix Hindi and English words naturally. Use Hindi for common words and English for technical terms, app names (like GyanTV), and modern concepts. Use Hindi script (Devanagari) for Hindi words."
        else:
            target_display = target_lang_name
            style_instruction = f"Translate accurately to {target_lang_name}."

        prompt = f"""Translate the following questionnaire text from {source_lang_name} to {target_display}.

IMPORTANT INSTRUCTIONS:
- Keep the structure and format exactly the same
- Preserve all question keys, labels, and special markers
- Maintain the conversational tone
- {style_instruction}
- Preserve any placeholders like {{name}}, {{age}}, etc.
- Return ONLY the translated text, no explanations or labels

SOURCE TEXT ({source_lang_name}):
{text}"""

        # Use LLM to translate - try translate_text method first, fallback to generate_insights
        if hasattr(llm_provider, 'translate_text'):
            translated = llm_provider.translate_text(text, target_language, source_language)
        else:
            # Fallback: use generate_insights with translation prompt
            translated = llm_provider.generate_insights(prompt, user_responses=None)

        if translated:
            # Clean up the response - remove any extra commentary
            translated = translated.strip()
            # Sometimes LLM adds extra text, try to extract just the translation
            # Look for the translated text after any labels
            if "TRANSLATED TEXT" in translated or "translated" in translated.lower():
                # Try to extract the actual translation
                lines = translated.split('\n')
                # Find the translation part
                translation_start = False
                translation_lines = []
                for line in lines:
                    if "TRANSLATED TEXT" in line or ("translated" in line.lower() and "text" in line.lower()):
                        translation_start = True
                        continue
                    if translation_start and line.strip():
                        translation_lines.append(line)

                if translation_lines:
                    translated = '\n'.join(translation_lines).strip()

            return translated

        return None

    except Exception as e:
        print(f"Error translating questionnaire: {e}")
        import traceback
        traceback.print_exc()
        return None


def translate_questionnaire_to_all_languages(text: str, source_language: str = 'en', provider: str = None) -> Dict[str, str]:
    """
    Translate questionnaire to all supported languages

    Args:
        text: Source questionnaire text
        source_language: Source language code (default: 'en')
        provider: LLM provider to use (default: from settings)

    Returns:
        Dictionary mapping language codes to translated text
        Example: {'en': '...', 'hi': '...'}
    """
    supported_languages = getattr(settings, 'SUPPORTED_LANGUAGES', ['en', 'hi'])

    translations = {}

    # Add source language as-is
    translations[source_language] = text

    # If provider not specified, use translation-specific provider
    if not provider:
        provider = getattr(settings, 'DEFAULT_TRANSLATION_PROVIDER', None)
        if not provider:
            provider = getattr(settings, 'DEFAULT_LLM_PROVIDER', 'gemini')

    # Translate to other languages
    for lang in supported_languages:
        if lang == source_language:
            continue

        print(f"Translating questionnaire to {lang} using {provider}...")
        translated = translate_questionnaire(text, lang, source_language, provider)

        if translated and translated.strip() and translated != text:
            # Only use translation if it's different from original and not empty
            translations[lang] = translated
            print(f"✓ Successfully translated to {lang}")
        else:
            print(f"✗ Failed to translate to {lang} (translation was empty or same as original)")
            # Try fallback providers if current one failed
            fallback_providers = []
            if provider == 'gemini':
                # If Gemini fails, try AssemblyAI (if available)
                fallback_providers = ['assemblyai']
            elif provider == 'assemblyai':
                # If AssemblyAI fails, try Gemini
                fallback_providers = ['gemini']
            # Note: OpenAI fallback removed since user doesn't have API key

            translated_with_fallback = None
            for fallback_provider in fallback_providers:
                print(f"  Trying fallback provider: {fallback_provider}...")
                fallback_translated = translate_questionnaire(text, lang, source_language, fallback_provider)
                if fallback_translated and fallback_translated.strip() and fallback_translated != text:
                    translated_with_fallback = fallback_translated
                    print(f"✓ Successfully translated to {lang} using {fallback_provider} fallback")
                    break

            if translated_with_fallback:
                translations[lang] = translated_with_fallback
            else:
                print(f"✗ All providers failed, keeping original text")
                translations[lang] = text

    return translations

