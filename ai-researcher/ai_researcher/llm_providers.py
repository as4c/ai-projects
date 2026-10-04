"""
LLM Provider Factory/Strategy Pattern
Supports multiple LLM providers: OpenAI, Gemini, AssemblyAI
"""
from abc import ABC, abstractmethod
from typing import Optional
from django.conf import settings


class LLMProvider(ABC):
    """Base class for LLM providers"""

    @abstractmethod
    def generate_insights(self, transcript: str, user_responses: dict = None) -> Optional[str]:
        """
        Generate insights from transcript

        Args:
            transcript: Full call transcript
            user_responses: Dictionary of user responses (optional)

        Returns:
            Insights text or None if generation fails
        """
        pass

    def translate_text(self, text: str, target_language: str, source_language: str = 'en') -> Optional[str]:
        """
        Translate text to target language (optional method, can be overridden)

        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'hi', 'en')
            source_language: Source language code (default: 'en')

        Returns:
            Translated text or None
        """
        # Default implementation returns None - subclasses should override
        return None


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""

    def translate_text(self, text: str, target_language: str, source_language: str = 'en') -> Optional[str]:
        """Translate text using OpenAI GPT"""
        try:
            from openai import OpenAI

            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not api_key:
                print("OpenAI API key not found, skipping translation")
                return None

            client = OpenAI(api_key=api_key)

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

            prompt = f"""Translate the following text from {source_lang_name} to {target_display}.

IMPORTANT INSTRUCTIONS:
- Keep the structure and format exactly the same
- Preserve all formatting, line breaks, and special characters
- Maintain the conversational tone
- {style_instruction}
- Preserve any placeholders like {{name}}, {{age}}, etc.
- Return ONLY the translated text, no explanations or labels

TEXT TO TRANSLATE:
{text}"""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a professional translator specializing in {target_display}. Translate text from {source_lang_name} to {target_display} accurately while preserving format and structure. Return only the translated text, no explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )

            translated = response.choices[0].message.content.strip()
            # Remove "TRANSLATION:" prefix if present
            if translated.startswith("TRANSLATION:"):
                translated = translated[len("TRANSLATION:"):].strip()

            return translated

        except Exception as e:
            print(f"OpenAI translation error: {e}")
            return None

    def generate_insights(self, transcript: str, user_responses: dict = None) -> Optional[str]:
        """Generate insights using OpenAI GPT"""
        try:
            from openai import OpenAI

            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not api_key:
                print("OpenAI API key not found, skipping insight generation")
                return None

            client = OpenAI(api_key=api_key)

            # Check if transcript is already a detailed prompt (from insight_generator)
            if "## INSTRUCTIONS:" in transcript or "REQUIRED FORMAT:" in transcript:
                # Use the detailed prompt directly
                prompt = transcript
            else:
                # Build basic prompt for raw transcripts
                prompt = f"""Analyze the following call transcript and generate numbered, actionable insights.

TRANSCRIPT:
{transcript}

Generate 5-8 numbered insights in this format:
1. [Category] Specific, actionable insight with evidence from the transcript.

Categories to use: Pain Point, Preference, Suggestion, Observation, Sentiment

Focus on:
- User pain points and frustrations
- Preferences and what they liked
- Specific suggestions for improvement
- Behavioral observations
- Overall sentiment"""

                if user_responses:
                    prompt += f"\n\nUSER RESPONSES BY QUESTION:\n{user_responses}"

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert UX researcher analyzing customer call transcripts. Generate numbered, actionable insights with specific evidence."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=800,
                temperature=0.5
            )

            insights = response.choices[0].message.content.strip()
            return insights

        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg or 'quota' in error_msg.lower() or 'insufficient_quota' in error_msg.lower():
                print(f"OpenAI quota exceeded - skipping insight generation (non-critical)")
            elif '401' in error_msg or 'invalid' in error_msg.lower() or 'authentication' in error_msg.lower():
                print(f"OpenAI API key issue - skipping insight generation (non-critical)")
            elif 'rate_limit' in error_msg.lower():
                print(f"OpenAI rate limit exceeded - skipping insight generation (non-critical)")
            else:
                print(f"OpenAI error generating insights (non-critical): {e}")

            if '429' not in error_msg and 'quota' not in error_msg.lower() and '401' not in error_msg:
                import traceback
                traceback.print_exc()

            return None


class GeminiProvider(LLMProvider):
    """Google Gemini provider"""

    def _translate_via_rest_api(self, text: str, target_language: str, source_language: str, api_key: str) -> Optional[str]:
        """Translate using Gemini REST API directly"""
        import requests
        import json

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

        prompt = f"""Translate the following text from {source_lang_name} to {target_display}.

IMPORTANT INSTRUCTIONS:
- Keep the structure and format exactly the same
- Preserve all formatting, line breaks, and special characters
- Maintain the conversational tone
- {style_instruction}
- Preserve any placeholders like {{name}}, {{age}}, etc.
- Return ONLY the translated text, no explanations or labels

TEXT TO TRANSLATE:
{text}"""

        # Try different model endpoints (using latest stable models)
        models_to_try = [
            'gemini-1.5-flash',      # Fast, cost-efficient (stable)
            'gemini-1.5-pro',        # Most capable model (stable)
            'gemini-2.0-flash-exp'   # Latest experimental model
        ]

        url_template = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

        for model_name in models_to_try:
            try:
                url = url_template.format(model=model_name, key=api_key)
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }]
                }

                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()

                result = response.json()

                # Extract text from response
                if 'candidates' in result and result['candidates']:
                    if 'content' in result['candidates'][0]:
                        if 'parts' in result['candidates'][0]['content']:
                            translated = result['candidates'][0]['content']['parts'][0].get('text', '').strip()
                            if translated and len(translated) > 10:
                                print(f"✓ Successfully translated using {model_name} (REST API)")
                                return translated

                # Try alternative response structure
                if 'text' in result:
                    translated = result['text'].strip()
                    if translated and len(translated) > 10:
                        print(f"✓ Successfully translated using {model_name} (REST API)")
                        return translated

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    print(f"  Model {model_name} not available via REST API, trying next...")
                    continue
                else:
                    print(f"  Model {model_name} REST API error: {str(e)[:100]}")
                    continue
            except Exception as e:
                print(f"  Model {model_name} REST API error: {str(e)[:100]}")
                continue

        raise Exception("All REST API models failed")

    def translate_text(self, text: str, target_language: str, source_language: str = 'en') -> Optional[str]:
        """Translate text using Google Gemini"""
        try:
            api_key = getattr(settings, 'GEMINI_API_KEY', None)
            if not api_key:
                print("Gemini API key not found, skipping translation")
                return None

            # Try using REST API directly (most reliable)
            try:
                return self._translate_via_rest_api(text, target_language, source_language, api_key)
            except Exception as rest_error:
                print(f"  REST API failed: {str(rest_error)[:100]}")
                print(f"  Falling back to SDK...")

            # Fallback to SDK if REST API fails
            try:
                from google import genai
                use_new_package = True
            except ImportError:
                # Fallback to old package (deprecated but might work)
                try:
                    import google.generativeai as genai
                    use_new_package = False
                except ImportError:
                    print("Google GenAI library not installed. Install with: pip install google-genai or google-generativeai")
                    return None

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

            prompt = f"""Translate the following text from {source_lang_name} to {target_display}.

IMPORTANT INSTRUCTIONS:
- Keep the structure and format exactly the same
- Preserve all formatting, line breaks, and special characters
- Maintain the conversational tone
- {style_instruction}
- Preserve any placeholders like {{name}}, {{age}}, etc.
- Return ONLY the translated text, no explanations or labels

TEXT TO TRANSLATE:
{text}"""

            if use_new_package:
                # New google-genai package - use correct API
                # The new package might not be installed, so we'll fallback to old package
                try:
                    client = genai.Client(api_key=api_key)

                    # Try different model identifiers for new package
                    # The new package uses 'models/' prefix format
                    models_to_try = [
                        'models/gemini-1.5-flash',      # Fast, cost-efficient (stable)
                        'models/gemini-1.5-pro',        # Most capable model (stable)
                        'models/gemini-2.0-flash-exp'   # Latest experimental model
                    ]

                    translated = None
                    last_error = None

                    for model_name in models_to_try:
                        try:
                            # New package API - try different approaches
                            try:
                                # Method 1: Direct generate_content call
                                response = client.models.generate_content(
                                    model=model_name,
                                    contents=prompt
                                )
                            except Exception as e1:
                                # Method 2: Try with contents as a list structure
                                try:
                                    response = client.models.generate_content(
                                        model=model_name,
                                        contents=[{"role": "user", "parts": [{"text": prompt}]}]
                                    )
                                except Exception:
                                    raise e1  # Raise original error

                            # Extract text from response - handle different response structures
                            if hasattr(response, 'text'):
                                translated = response.text.strip()
                            elif hasattr(response, 'candidates') and response.candidates:
                                if hasattr(response.candidates[0], 'content'):
                                    if hasattr(response.candidates[0].content, 'parts'):
                                        translated = response.candidates[0].content.parts[0].text.strip()
                                    else:
                                        translated = str(response.candidates[0].content).strip()
                                else:
                                    translated = str(response.candidates[0]).strip()
                            elif isinstance(response, str):
                                translated = response.strip()
                            elif hasattr(response, 'content'):
                                translated = str(response.content).strip()
                            else:
                                # Try to get text from response object
                                translated = str(response).strip()

                            if translated and len(translated) > 10:  # Ensure we got actual content
                                print(f"✓ Successfully translated using {model_name}")
                                return translated
                        except Exception as e:
                            last_error = e
                            error_str = str(e).lower()
                            if '404' in error_str or 'not found' in error_str:
                                print(f"  Model {model_name} not available, trying next...")
                                continue
                            else:
                                print(f"  Model {model_name} error: {str(e)[:100]}")
                                continue

                    if not translated:
                        print(f"✗ All Gemini models failed with new package. Last error: {last_error}")
                        print(f"  Falling back to old package...")
                        use_new_package = False
                except Exception as e:
                    print(f"  New package error: {str(e)[:100]}")
                    print(f"  Falling back to old package...")
                    use_new_package = False
            else:
                # Old google-generativeai package (deprecated)
                genai.configure(api_key=api_key)

                # Try different model names
                models_to_try = [
                    'gemini-1.5-flash',      # Fast, cost-efficient (stable)
                    'gemini-1.5-pro',        # Most capable model (stable)
                    'gemini-2.0-flash-exp'   # Latest experimental model
                ]
                translated = None
                last_error = None

                for model_name in models_to_try:
                    try:
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(prompt)
                        translated = response.text.strip()
                        if translated:
                            print(f"✓ Successfully translated using {model_name}")
                            break
                    except Exception as e:
                        last_error = e
                        error_str = str(e).lower()
                        if '404' in error_str or 'not found' in error_str:
                            print(f"  Model {model_name} not available, trying next...")
                            continue
                        else:
                            print(f"  Model {model_name} error: {str(e)[:100]}")
                            continue

                if not translated:
                    print(f"✗ All Gemini models failed. Last error: {last_error}")
                    return None

            return translated

        except Exception as e:
            print(f"Gemini translation error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_insights(self, transcript: str, user_responses: dict = None) -> Optional[str]:
        """Generate insights using Google Gemini"""
        try:
            # Try new google.genai package first
            try:
                from google import genai
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
                print("Gemini API key not found, skipping insight generation")
                return None

            # Check if transcript is already a detailed prompt (from insight_generator)
            if "## INSTRUCTIONS:" in transcript or "REQUIRED FORMAT:" in transcript:
                # Use the detailed prompt directly
                prompt = transcript
            else:
                # Build structured prompt for raw transcripts
                prompt = f"""You are an expert UX researcher analyzing customer call transcripts.

TRANSCRIPT:
{transcript}

Generate 5-8 numbered, actionable insights in this exact format:
1. [Category] Specific insight with evidence from the transcript.

Use these categories: Pain Point, Preference, Suggestion, Observation, Sentiment

Focus on:
- User pain points and frustrations (specific quotes help)
- Preferences and what they liked
- Specific suggestions for improvement
- Behavioral observations
- Overall sentiment shifts during the call"""

                if user_responses:
                    prompt += f"\n\nUSER RESPONSES BY QUESTION:\n{user_responses}"

            if use_new_package:
                client = genai.Client(api_key=api_key)
                # Try models in order of preference
                models_to_try = [
                    'models/gemini-1.5-pro',
                    'models/gemini-1.5-flash',
                    'models/gemini-2.0-flash-exp'
                ]
                response = None
                last_error = None
                for model_name in models_to_try:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt
                        )
                        break
                    except Exception as e:
                        last_error = e
                        continue
                if response is None:
                    raise last_error if last_error else Exception("All models failed")
                insights = response.text.strip() if hasattr(response, 'text') else str(response)
            else:
                genai.configure(api_key=api_key)
                # Try models in order of preference
                models_to_try = [
                    'gemini-1.5-pro',
                    'gemini-1.5-flash',
                    'gemini-2.0-flash-exp'
                ]
                response = None
                last_error = None
                for model_name in models_to_try:
                    try:
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(prompt)
                        break
                    except Exception as e:
                        last_error = e
                        continue
                if response is None:
                    raise last_error if last_error else Exception("All models failed")
                insights = response.text.strip() if hasattr(response, 'text') else str(response)

            return insights

        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg or 'quota' in error_msg.lower():
                print(f"Gemini quota exceeded - skipping insight generation (non-critical)")
            elif '401' in error_msg or 'invalid' in error_msg.lower() or 'authentication' in error_msg.lower():
                print(f"Gemini API key issue - skipping insight generation (non-critical)")
            elif 'rate_limit' in error_msg.lower():
                print(f"Gemini rate limit exceeded - skipping insight generation (non-critical)")
            else:
                print(f"Gemini error generating insights (non-critical): {e}")

            if '429' not in error_msg and 'quota' not in error_msg.lower() and '401' not in error_msg:
                import traceback
                traceback.print_exc()

            return None


class AssemblyAIProvider(LLMProvider):
    """AssemblyAI LLM provider (using their LeMUR models)"""

    def translate_text(self, text: str, target_language: str, source_language: str = 'en') -> Optional[str]:
        """Translate text using AssemblyAI LeMUR (for general text translation)"""
        try:
            import requests

            api_key = getattr(settings, 'ASSEMBLYAI_API_KEY', None)
            if not api_key:
                print("AssemblyAI API key not found, skipping translation")
                return None

            language_names = {
                'hi': 'Hindi',
                'en': 'English',
                'hinglish': 'Hinglish (Hindi-English mix)'
            }

            target_lang_name = language_names.get(target_language.lower(), target_language)
            source_lang_name = language_names.get(source_language.lower(), source_language)

            # Use LeMUR v3 for translation
            headers = {
                "authorization": api_key,
                "content-type": "application/json"
            }

            # For Hindi, use Hinglish style (mix of Hindi and English)
            if target_language.lower() in ['hi', 'hin', 'hinglish']:
                target_display = "Hinglish (Hindi-English mix)"
                style_instruction = "Use natural Hinglish style - mix Hindi and English words naturally. Use Hindi for common words and English for technical terms, app names, and modern concepts."
            else:
                target_display = target_lang_name
                style_instruction = f"Translate accurately to {target_lang_name}."

            prompt = f"""Translate the following text from {source_lang_name} to {target_display}.

IMPORTANT INSTRUCTIONS:
- Keep the structure and format exactly the same
- Preserve all formatting, line breaks, and special characters
- Maintain the conversational tone
- {style_instruction}
- Keep technical terms, app names (like GyanTV), and modern concepts in English
- Use Hindi script (Devanagari) for Hindi words
- Preserve any placeholders like {{name}}, {{age}}, etc.
- Return ONLY the translated text, no explanations or labels

TEXT TO TRANSLATE:
{text}"""

            body = {
                "model": "lemur-3",
                "input": text,  # Use text as input
                "task": "generate",
                "max_output_tokens": 2000,
                "temperature": 0.3,
                "system_prompt": f"You are a professional translator specializing in {target_display}. Translate text from {source_lang_name} to {target_display} accurately while preserving format and structure. Return only the translated text, no explanations.",
                "prompt": prompt
            }

            response = requests.post(
                "https://api.assemblyai.com/v2/lemur/v3/generate",
                json=body,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                translated = data.get("response", "").strip()
                return translated
            else:
                print(f"AssemblyAI translation error {response.status_code}: {response.text[:200]}")
                return None

        except Exception as e:
            print(f"AssemblyAI translation error: {e}")
            return None

    def generate_insights(self, transcript: str, user_responses: dict = None) -> Optional[str]:
        """Generate insights using AssemblyAI LeMUR"""
        try:
            import assemblyai as aai

            api_key = getattr(settings, 'ASSEMBLYAI_API_KEY', None)
            if not api_key:
                print("AssemblyAI API key not found, skipping insight generation")
                return None

            aai.settings.api_key = api_key

            # Check if transcript is already a detailed prompt (from insight_generator)
            if "## INSTRUCTIONS:" in transcript or "REQUIRED FORMAT:" in transcript:
                # Use the detailed prompt directly
                prompt = transcript
                full_prompt = prompt
                system_prompt = "You are an expert UX researcher. Follow the instructions exactly and generate numbered, actionable insights."
            else:
                # Build structured prompt for raw transcripts
                prompt = """Generate 5-8 numbered, actionable insights from this call transcript.

Use this exact format:
1. [Category] Specific insight with evidence from the transcript.

Categories: Pain Point, Preference, Suggestion, Observation, Sentiment

Focus on user pain points, preferences, suggestions, behavioral patterns, and sentiment."""

                if user_responses:
                    prompt += f"\n\nUSER RESPONSES BY QUESTION:\n{user_responses}"

                full_prompt = f"""{prompt}

TRANSCRIPT:
{transcript}"""
                system_prompt = "You are an expert UX researcher analyzing customer call transcripts. Generate numbered, actionable insights with specific evidence."

            # Use AssemblyAI LeMUR v3 API for LLM tasks
            try:
                import requests

                # Use LeMUR v3 REST API
                headers = {
                    "authorization": api_key,
                    "content-type": "application/json"
                }

                body = {
                    "model": "lemur-3",
                    "input": transcript if "## INSTRUCTIONS:" not in transcript else "",
                    "task": "generate",
                    "max_output_tokens": 1000,
                    "temperature": 0.3,
                    "system_prompt": system_prompt,
                    "prompt": full_prompt
                }

                response = requests.post(
                    "https://api.assemblyai.com/v2/lemur/v3/generate",
                    json=body,
                    headers=headers,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    result_text = data.get("response", "").strip()
                    if result_text:
                        return result_text
                    else:
                        # Fallback: use simple text analysis
                        print("LeMUR returned empty response, using simple analysis")
                        return self._simple_analysis(transcript, user_responses)
                else:
                    # API error, use fallback
                    print(f"AssemblyAI LeMUR API error {response.status_code}: {response.text[:200]}")
                    return self._simple_analysis(transcript, user_responses)

            except ImportError:
                # requests not available, try SDK method
                try:
                    # Create a lemur instance
                    lemur = aai.Lemur()

                    # Build full prompt with transcript
                    full_prompt = f"""{prompt}

TRANSCRIPT:
{transcript}"""

                    # Use LeMUR SDK (if available)
                    result = lemur.task(
                        transcript_text=transcript,
                        prompt=full_prompt,
                        final_model=aai.LemurModel.basic
                    )

                    if result and hasattr(result, 'response'):
                        return result.response.strip()
                    elif isinstance(result, str):
                        return result.strip()
                    elif hasattr(result, 'text'):
                        return result.text.strip()
                    else:
                        return self._simple_analysis(transcript, user_responses)
                except Exception as e:
                    print(f"AssemblyAI LeMUR SDK failed, using simple analysis: {e}")
                    return self._simple_analysis(transcript, user_responses)
            except Exception as e:
                # If LeMUR fails, try simple analysis
                print(f"AssemblyAI LeMUR failed, using simple analysis: {e}")
                return self._simple_analysis(transcript, user_responses)

        except ImportError:
            print("AssemblyAI library not installed. Install with: pip install assemblyai")
            return None
        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg or 'quota' in error_msg.lower():
                print(f"AssemblyAI quota exceeded - skipping insight generation (non-critical)")
            elif '401' in error_msg or 'invalid' in error_msg.lower() or 'authentication' in error_msg.lower():
                print(f"AssemblyAI API key issue - skipping insight generation (non-critical)")
            else:
                print(f"AssemblyAI error generating insights (non-critical): {e}")

            if '429' not in error_msg and 'quota' not in error_msg.lower() and '401' not in error_msg:
                import traceback
                traceback.print_exc()

            return None

    def _simple_analysis(self, transcript: str, user_responses: dict = None) -> str:
        """Simple text-based analysis fallback"""
        # Basic analysis without LLM
        insights = []
        insights.append("Key Takeaways:")
        insights.append("- Conversation completed successfully")

        # Check for sentiment keywords
        positive_words = ['yes', 'good', 'great', 'excellent', 'happy', 'satisfied', 'हाँ', 'अच्छा', 'बढ़िया']
        negative_words = ['no', 'bad', 'poor', 'disappointed', 'not interested', 'नहीं', 'खराब']

        transcript_lower = transcript.lower()
        positive_count = sum(1 for word in positive_words if word in transcript_lower)
        negative_count = sum(1 for word in negative_words if word in transcript_lower)

        if positive_count > negative_count:
            insights.append("- User sentiment: Positive")
        elif negative_count > positive_count:
            insights.append("- User sentiment: Negative")
        else:
            insights.append("- User sentiment: Neutral")

        if user_responses:
            insights.append(f"\nUser provided {len(user_responses)} responses")

        return "\n".join(insights)


class LLMProviderFactory:
    """Factory to create LLM provider instances"""

    PROVIDERS = {
        'openai': OpenAIProvider,
        'gemini': GeminiProvider,
        'assemblyai': AssemblyAIProvider,
        'assembly': AssemblyAIProvider,  # Alias
    }

    @staticmethod
    def create_provider(provider_name: str = None) -> Optional[LLMProvider]:
        """
        Create an LLM provider instance

        Args:
            provider_name: Name of provider ('openai', 'gemini', 'assemblyai')
                          If None, uses default from settings or 'assemblyai'

        Returns:
            LLMProvider instance or None if provider not found
        """
        # If no provider specified, check settings or use default
        if not provider_name:
            provider_name = getattr(settings, 'DEFAULT_LLM_PROVIDER', 'gemini')

        provider_name = provider_name.lower().strip()

        # Check if provider class exists
        provider_class = LLMProviderFactory.PROVIDERS.get(provider_name)
        if not provider_class:
            print(f"Unknown LLM provider: {provider_name}. Available: {list(LLMProviderFactory.PROVIDERS.keys())}")
            # Fallback to assemblyai
            provider_class = AssemblyAIProvider

        try:
            return provider_class()
        except Exception as e:
            print(f"Error creating LLM provider {provider_name}: {e}")
            return None

    @staticmethod
    def get_available_providers() -> list:
        """Get list of available provider names"""
        return list(LLMProviderFactory.PROVIDERS.keys())


# Convenience function
def generate_insights(transcript: str, user_responses: dict = None, provider: str = None) -> Optional[str]:
    """
    Generate insights using specified LLM provider

    Args:
        transcript: Full call transcript
        user_responses: Dictionary of user responses (optional)
        provider: LLM provider name ('openai', 'gemini', 'assemblyai')
                 If None, uses default from settings

    Returns:
        Insights text or None if generation fails
    """
    llm_provider = LLMProviderFactory.create_provider(provider)
    if not llm_provider:
        return None

    return llm_provider.generate_insights(transcript, user_responses)
