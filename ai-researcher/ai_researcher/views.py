# views.py
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.voice_response import VoiceResponse, Start, Stream, Gather
from twilio.rest import Client
from django.conf import settings
import os
import uuid
import json
import random
import requests
from pathlib import Path
from typing import Dict

from .utils import generate_voice
from .transcription_helper import transcribe_audio
from .questionnaire import QuestionnaireHandler
from .decision_tree_handler import DecisionTreeHandler
from .elevenlabs_client import generate_voice_response
import hashlib

# Audio cache to avoid regenerating the same audio
_audio_cache = {}
MAX_AUDIO_CACHE_SIZE = 50  # Cache up to 50 audio files
from .disinterest_detector import DisinterestDetector
from .insight_generator import generate_call_insights
from .call_data_storage import save_call_data
from .voice_mapper import get_voice_id_for_language, get_twilio_language_code

# Get BASE_URL from settings (supports environment variables)
BASE_URL = settings.BASE_URL

# Store questionnaire handlers per call
_questionnaire_handlers: Dict[str, QuestionnaireHandler] = {}


def serve_audio(request, filename):
    """Serve generated audio files"""
    path = f"/tmp/{filename}"
    if os.path.exists(path):
        return FileResponse(open(path, "rb"), content_type="audio/mpeg")
    return HttpResponse("File not found", status=404)


def get_filler_word(user_response: str) -> str:
    """
    Get appropriate filler word based on user's response
    Returns short, natural filler words in Hinglish
    Uses diverse conversation fillers for natural flow

    Common Hindi/Hinglish fillers:
    - Achha (अच्छा) - "Okay", "alright"
    - Theek hai (ठीक है) - "Okay, fine"
    - Hmm/Haan (हाँ) - Thinking sound, "yes"
    - Bilkul (बिल्कुल) - "Absolutely"
    - Samajh gaya (समझ गया) - "Got it"
    - Koi baat nahi (कोई बात नहीं) - "No problem"

    Args:
        user_response: User's speech response

    Returns:
        Filler word in Hinglish
    """
    if not user_response:
        # Random selection from neutral fillers
        return random.choice(["Hmm", "Achha", "Theek hai", "Haan"])

    response_lower = user_response.lower().strip()
    word_count = len(user_response.split())

    # Very short responses (1-2 words)
    if word_count <= 2:
        # Positive short responses
        positive_short = ["yes", "yeah", "yep", "ok", "okay", "haan", "हाँ", "ठीक", "sure", "bilkul", "बिल्कुल", "ji", "जी"]
        if any(word in response_lower for word in positive_short):
            return random.choice([
                "Achha",
                "Theek hai",
                "Bilkul",
                "Haan, samajh gaya",
                "Achha, theek hai",
                "Haan, bilkul",
                "Ji, theek hai"
            ])

        # Negative short responses
        negative_short = ["no", "nah", "नहीं", "नही", "nhi", "na", "naa"]
        if any(word in response_lower for word in negative_short):
            return random.choice([
                "Theek hai",
                "Koi baat nahi",
                "Achha, theek hai",
                "Samajh gaya",
                "Koi problem nahi",
                "Theek hai, no worries"
            ])

        # Default for very short responses
        return random.choice([
            "Hmm",
            "Achha",
            "Theek hai",
            "Samajh gaya",
            "Haan",
            "Bilkul"
        ])

    # Medium responses (3-5 words)
    elif word_count <= 5:
        # Check for positive sentiment
        positive_words = ["good", "nice", "great", "achha", "accha", "बढ़िया", "अच्छा", "wonderful", "excellent", "best", "badhiya", "बढ़िया"]
        if any(word in response_lower for word in positive_words):
            return random.choice([
                "Achha, samajh gaya",
                "Bilkul, theek hai",
                "Haan, achha hai",
                "Theek hai, samajh gaya",
                "Waah, achha hai",
                "Bilkul, samajh gaya"
            ])

        # Check for time-related responses
        time_words = ["morning", "evening", "night", "day", "time", "subah", "shaam", "raat", "din", "समय", "वक्त"]
        if any(word in response_lower for word in time_words):
            return random.choice([
                "Achha, theek hai",
                "Hmm, samajh gaya",
                "Theek hai",
                "Achha, samajh gaya",
                "Haan, theek hai"
            ])

        # Check for number/quantity responses
        number_words = ["one", "two", "three", "ek", "do", "teen", "minutes", "hours", "minute", "hour", "minute", "ghanta", "घंटा"]
        if any(word in response_lower for word in number_words):
            return random.choice([
                "Achha",
                "Theek hai",
                "Hmm, samajh gaya",
                "Achha, theek hai",
                "Bilkul"
            ])

        # Check for category/topic responses
        category_words = ["business", "ai", "stock", "market", "communication", "skills", "topic", "category", "विषय", "श्रेणी"]
        if any(word in response_lower for word in category_words):
            return random.choice([
                "Achha, theek hai",
                "Haan, samajh gaya",
                "Bilkul, theek hai",
                "Theek hai"
            ])

        # Default for medium responses
        return random.choice([
            "Hmm, theek hai",
            "Achha, samajh gaya",
            "Theek hai",
            "Bilkul",
            "Haan, theek hai",
            "Achha, bilkul"
        ])

    # Long responses (user is explaining - 6+ words)
    else:
        # Check if user is explaining something
        explanation_indicators = ["because", "kyunki", "क्योंकि", "reason", "wajah", "वजह", "so", "toh", "तो", "matlab", "मतलब"]
        if any(word in response_lower for word in explanation_indicators):
            return random.choice([
                "Achha, samajh gaya",
                "Haan, bilkul samajh gaya",
                "Theek hai, samajh gaya",
                "Achha, theek hai",
                "Bilkul, samajh gaya",
                "Haan, achha hai"
            ])

        # Check for detailed descriptions
        detail_indicators = ["usually", "sometimes", "often", "always", "kabhi", "कभी", "हमेशा", "अक्सर"]
        if any(word in response_lower for word in detail_indicators):
            return random.choice([
                "Achha, theek hai",
                "Hmm, samajh gaya",
                "Theek hai, samajh gaya",
                "Achha, bilkul"
            ])

        # Default for long responses
        return random.choice([
            "Achha, samajh gaya",
            "Haan, theek hai",
            "Bilkul, samajh gaya",
            "Theek hai, samajh gaya",
            "Achha, bilkul theek hai",
            "Haan, achha hai"
        ])


def play_filler_word(vr: VoiceResponse, user_response: str, request, language: str = None) -> None:
    """
    Play a filler word immediately using Twilio TTS (fast) while processing

    Args:
        vr: VoiceResponse object
        user_response: User's speech response
        request: Django request object
        language: Language code to determine Twilio language
    """
    filler = get_filler_word(user_response)
    # Get Twilio language code for TTS
    twilio_language = get_twilio_language_code(language) if language else 'hi-IN'
    # Use Twilio TTS for instant playback (faster than ElevenLabs)
    vr.say(filler, voice='Polly.Aditi', language=twilio_language)


def play_elevenlabs_audio(vr: VoiceResponse, text: str, request, voice_id: str = None, language: str = None) -> bool:
    """
    Generate audio using ElevenLabs and add to VoiceResponse
    OPTIMIZED: Uses caching to avoid regenerating same audio

    Args:
        vr: VoiceResponse object
        text: Text to convert to speech
        request: Django request object (for building absolute URI)
        voice_id: ElevenLabs voice ID (default: from settings or language mapping)
        language: Language code to determine voice (e.g., 'hi', 'en', 'hinglish')

    Returns:
        True if audio was generated and added, False if fallback needed
    """
    global _audio_cache

    try:
        # Use voice_id from parameter, language mapping, or settings
        if voice_id is None:
            if language:
                voice_id = get_voice_id_for_language(language)
            else:
                voice_id = settings.ELEVENLABS_VOICE_ID

        # Create cache key based on text and voice_id
        cache_key = hashlib.md5(f"{text}:{voice_id}".encode()).hexdigest()[:16]

        # Check if audio is cached
        if cache_key in _audio_cache:
            cached_filename = _audio_cache[cache_key]
            cached_path = f"/tmp/{cached_filename}"
            if os.path.exists(cached_path):
                print(f"⚡ CACHE HIT: Using cached audio for '{text[:30]}...'")
                audio_url = request.build_absolute_uri(f'/audio/{cached_filename}')
                vr.play(audio_url)
                return True

        # Generate new audio
        audio_data = generate_voice_response(text, voice_id=voice_id)

        if audio_data and len(audio_data) > 0:
            filename = f"audio_{cache_key}.mp3"  # Use cache key in filename
            path = f"/tmp/{filename}"

            with open(path, "wb") as f:
                f.write(audio_data)

            # Add to cache (with size limit)
            if len(_audio_cache) >= MAX_AUDIO_CACHE_SIZE:
                # Remove oldest entry
                oldest_key = next(iter(_audio_cache))
                del _audio_cache[oldest_key]
            _audio_cache[cache_key] = filename

            # Use request.build_absolute_uri for dynamic URL
            audio_url = request.build_absolute_uri(f'/audio/{filename}')
            vr.play(audio_url)
            return True
    except Exception as e:
        print(f"Error generating ElevenLabs audio: {e}")
        import traceback
        traceback.print_exc()

    # Fallback to Twilio TTS - use language mapping
    twilio_language = get_twilio_language_code(language) if language else 'hi-IN'
    vr.say(text, voice='Polly.Aditi', language=twilio_language)
    return False


@csrf_exempt
def twilio_voice(request):
    """Original simple voice endpoint"""
    text = "Hello! This voice is generated using Eleven Labs."
    audio_path, filename = generate_voice(text, language="en")

    vr = VoiceResponse()
    # Use request.build_absolute_uri for dynamic URL (works with localhost/local IP)
    audio_url = request.build_absolute_uri(f'/audio/{filename}')
    vr.play(audio_url)

    return HttpResponse(str(vr), content_type="text/xml")


@csrf_exempt
def simple_test_call(request):
    """
    Simple test endpoint for recording testing
    Just says a message and hangs up - no complex logic
    """
    vr = VoiceResponse()
    vr.say(
        "This is sagar kumar. Recording should be enabled. "
        "The call will end now. Thank you!",
        voice='alice'
    )
    vr.hangup()
    return HttpResponse(str(vr), content_type="text/xml")


@csrf_exempt
def incoming_call(request):
    """
    Handle incoming Twilio call
    Starts Media Stream for real-time bidirectional audio
    """
    call_sid = request.POST.get('CallSid', '')

    vr = VoiceResponse()

    # Start Media Stream - connects to WebSocket endpoint
    start = Start()
    stream = Stream(
        url=f"wss://{request.get_host()}/media-stream/",
        parameters={
            'callSid': call_sid
        }
    )
    start.stream(stream)
    vr.append(start)

    # Say something while connecting
    vr.say(
        "Connecting you to our AI assistant. Please wait a moment.",
        voice='alice'
    )

    return HttpResponse(str(vr), content_type="text/xml")


@csrf_exempt
def call_with_gather(request):
    """
    Start the questionnaire call
    Uses Twilio Gather for speech recognition and ElevenLabs for TTS response
    Retrieves user data from pending calls if available
    """
    print("=" * 80)
    print("🔔 WEBHOOK RECEIVED: call_with_gather")
    print(f"📞 Call SID: {request.POST.get('CallSid', 'N/A')}")
    print(f"📱 From: {request.POST.get('From', 'N/A')}")
    print(f"📱 To: {request.POST.get('To', 'N/A')}")
    print(f"📋 All POST data: {dict(request.POST)}")
    print("=" * 80)

    try:
        call_sid = request.POST.get('CallSid', '')
        from_number = request.POST.get('From', '')  # Phone number being called
        to_number = request.POST.get('To', '')  # Also check To field

        # Try to get user data from pending calls
        user_name = None
        user_gender = None
        user_age = None
        event_name = None
        language = None

        # First, try to match by CallSid (most reliable)
        if call_sid and hasattr(trigger_call_with_questionnaire, '_pending_calls_by_sid'):
            if call_sid in trigger_call_with_questionnaire._pending_calls_by_sid:
                call_data = trigger_call_with_questionnaire._pending_calls_by_sid[call_sid]
                user_name = call_data.get('user_name')
                user_gender = call_data.get('user_gender')
                user_age = call_data.get('user_age')
                event_name = call_data.get('event_name')
                language = call_data.get('language')
                print(f"✅ Found user data by CallSid: {user_name}, {user_gender}, {user_age}, event: {event_name}, language: {language}")
                # Clean up
                del trigger_call_with_questionnaire._pending_calls_by_sid[call_sid]
                # Also remove from phone-based dict if exists
                phone_num = call_data.get('phone_number')
                if phone_num and hasattr(trigger_call_with_questionnaire, '_pending_calls'):
                    trigger_call_with_questionnaire._pending_calls.pop(phone_num, None)

        # If not found by CallSid, try phone number matching
        if not event_name and hasattr(trigger_call_with_questionnaire, '_pending_calls'):
            print(f"🔍 Checking pending calls by phone: {list(trigger_call_with_questionnaire._pending_calls.keys())}")
            # Try to match by phone number (check both From and To)
            for phone, call_data in list(trigger_call_with_questionnaire._pending_calls.items()):
                # Match by phone number (normalize for comparison)
                phone_normalized = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                from_normalized = from_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                to_normalized = to_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

                print(f"🔍 Comparing: phone={phone_normalized}, from={from_normalized}, to={to_normalized}")

                # Check if phone numbers match (either exact or one contains the other)
                if (phone_normalized == from_normalized or phone_normalized == to_normalized or
                    phone_normalized in from_normalized or from_normalized in phone_normalized or
                    phone_normalized in to_normalized or to_normalized in phone_normalized):
                    user_name = call_data.get('user_name')
                    user_gender = call_data.get('user_gender')
                    user_age = call_data.get('user_age')
                    event_name = call_data.get('event_name')
                    language = call_data.get('language')
                    print(f"✅ Found user data by phone number: {user_name}, {user_gender}, {user_age}, event: {event_name}, language: {language}")
                    # Remove from pending after use
                    del trigger_call_with_questionnaire._pending_calls[phone]
                    # Also remove from SID dict if exists
                    sid = call_data.get('call_sid')
                    if sid and hasattr(trigger_call_with_questionnaire, '_pending_calls_by_sid'):
                        trigger_call_with_questionnaire._pending_calls_by_sid.pop(sid, None)
                    break
            else:
                print(f"⚠️ No matching phone number found in pending calls")
        elif not event_name:
            print(f"⚠️ No pending calls dictionary found")

        # Initialize questionnaire handler for this call with user data
        # Use DecisionTreeHandler for subscription_cancelled, otherwise use QuestionnaireHandler
        print(f"🔧 Initializing handler - event_name: {event_name}, language: {language}")

        if call_sid and call_sid not in _questionnaire_handlers:
            print(f"🆕 Creating new handler for call_sid: {call_sid}")
            if event_name == "subscription_cancelled":
                print("🌳 Using DecisionTreeHandler")
                handler = DecisionTreeHandler(
                    event_name=event_name,
                    language=language or 'hi',
                    user_name=user_name,
                    user_gender=user_gender,
                    user_age=user_age
                )
            else:
                print("📋 Using QuestionnaireHandler")
                handler = QuestionnaireHandler(
                    user_name=user_name,
                    user_gender=user_gender,
                    user_age=user_age,
                    event_name=event_name,
                    language=language
                )
            _questionnaire_handlers[call_sid] = handler
        else:
            handler = _questionnaire_handlers.get(call_sid)
            if not handler:
                print(f"🔄 Creating handler (call_sid already exists but no handler)")
                if event_name == "subscription_cancelled":
                    handler = DecisionTreeHandler(
                        event_name=event_name,
                        language=language or 'hi',
                        user_name=user_name,
                        user_gender=user_gender,
                        user_age=user_age
                    )
                else:
                    handler = QuestionnaireHandler(
                        user_name=user_name,
                        user_gender=user_gender,
                        user_age=user_age,
                        event_name=event_name,
                        language=language
                    )
                if call_sid:
                    _questionnaire_handlers[call_sid] = handler
            else:
                print(f"♻️ Reusing existing handler for call_sid: {call_sid}")

        # Get the first question
        print(f"❓ Getting first question from handler...")
        question_data = handler.get_next_question()
        print(f"📝 Question data received: {question_data}")

        print(f"DEBUG: call_with_gather - call_sid={call_sid}, from={from_number}, to={to_number}")
        print(f"DEBUG: user_data - name={user_name}, gender={user_gender}, age={user_age}, event={event_name}, language={language}")
        print(f"DEBUG: question_data={question_data}")

        if not question_data:
            print("ERROR: No question data returned from handler")
            vr = VoiceResponse()
            error_msg = "Sorry, there was an error starting the questionnaire."
            language = getattr(handler, 'language', None) if handler else None
            play_elevenlabs_audio(vr, error_msg, request, language=language)
            vr.hangup()
            twiml_response = str(vr)
            print(f"DEBUG: Error TwiML response: {twiml_response}")
            return HttpResponse(twiml_response, content_type="text/xml")

        question_text, question_key = question_data

        # Store question info for next iteration
        is_decision_tree = isinstance(handler, DecisionTreeHandler)
        if is_decision_tree:
            handler.current_question_id = question_key
        else:
            handler._current_question_key = question_key
            handler._current_question_text = question_text

        vr = VoiceResponse()

        # Add agent question to conversation history (if not already added)
        # DecisionTreeHandler adds it automatically in get_next_question, but regular handler needs it
        if not is_decision_tree:
            handler.add_agent_message(question_text)

        # Use ElevenLabs for natural, lag-free conversation
        # Get language from handler to determine voice
        language = getattr(handler, 'language', None)
        print(f"DEBUG: Speaking question (language: {language or 'default'}): {question_text[:100]}...")
        audio_success = play_elevenlabs_audio(vr, question_text, request, language=language)
        print(f"DEBUG: Audio generation success: {audio_success}")

        # Get speech input from caller
        # Use request.build_absolute_uri for dynamic URL (works with localhost/local IP)
        process_speech_url = request.build_absolute_uri('/twilio/process-speech/')
        # Get Twilio language code based on handler language
        twilio_language = get_twilio_language_code(getattr(handler, 'language', None))
        gather = Gather(
            input='speech',
            action=process_speech_url,
            method='POST',
            speech_timeout='3',  # Wait 3 seconds after speech stops
            language=twilio_language,  # Language based on API parameter
            num_digits=0,  # Don't wait for digits, only speech
            timeout=30  # Total timeout: wait up to 30 seconds for user to speak
        )
        vr.append(gather)

        # Fallback if no input - redirect to restart
        # This only executes if Gather times out
        fallback_msg = "I didn't catch that. Please try again."
        language = getattr(handler, 'language', None) if handler else None
        play_elevenlabs_audio(vr, fallback_msg, request, language=language)
        call_url = request.build_absolute_uri('/twilio/call/')
        vr.redirect(call_url)

        twiml_response = str(vr)
        print(f"DEBUG: Final TwiML response length: {len(twiml_response)}")
        print(f"DEBUG: TwiML response preview: {twiml_response[:500]}")
        return HttpResponse(twiml_response, content_type="text/xml")
    except Exception as e:
        # Return error response if something goes wrong
        print(f"Error in call_with_gather: {e}")
        import traceback
        traceback.print_exc()
        vr = VoiceResponse()
        error_msg = "Sorry, there was an error processing your call."
        # Try to get language from handler if it exists, otherwise use default
        try:
            handler = _questionnaire_handlers.get(request.POST.get('CallSid', ''))
            language = getattr(handler, 'language', None) if handler else None
        except:
            language = None
        play_elevenlabs_audio(vr, error_msg, request, language=language)
        vr.hangup()
        return HttpResponse(str(vr), content_type="text/xml")


@csrf_exempt
def process_speech(request):
    """
    Process speech input from Gather
    Saves response and asks next questionnaire question via ElevenLabs
    """
    speech_result = request.POST.get('SpeechResult', '')
    call_sid = request.POST.get('CallSid', '')

    # Debug: Print all POST data to see what Twilio is sending
    print(f"Process Speech - Call SID: {call_sid}")
    print(f"Process Speech - Speech Result: {speech_result}")
    print(f"Process Speech - All POST data: {dict(request.POST)}")

    # Get questionnaire handler for this call (should already exist)
    handler = _questionnaire_handlers.get(call_sid)
    if not handler:
        # Fallback: create new handler if somehow missing
        handler = QuestionnaireHandler()
        if call_sid:
            _questionnaire_handlers[call_sid] = handler

    vr = VoiceResponse()

    if speech_result:
        try:
            # Initialize disinterest detector for this call
            if not hasattr(handler, '_disinterest_detector'):
                handler._disinterest_detector = DisinterestDetector()

            disinterest_detector = handler._disinterest_detector

            # Check for disinterest FIRST, before saving response
            if disinterest_detector.is_disinterested(speech_result):
                print(f"User showed disinterest: {speech_result}")
                termination_msg = "Thank you for your time. Goodbye!"
                handler.add_agent_message(termination_msg)

                # Use ElevenLabs for natural termination message
                language = getattr(handler, 'language', None)
                play_elevenlabs_audio(vr, termination_msg, request, language=language)

                if call_sid:
                    _questionnaire_handlers.pop(call_sid, None)

                vr.hangup()
                return HttpResponse(str(vr), content_type="text/xml")

            # Check if using DecisionTreeHandler
            is_decision_tree = isinstance(handler, DecisionTreeHandler)

            # Get current question key (we need to track this)
            if is_decision_tree:
                current_question_key = getattr(handler, 'current_question_id', None)
            else:
                current_question_key = getattr(handler, '_current_question_key', None)

            # Save the user's response
            if current_question_key:
                if is_decision_tree:
                    # For DecisionTreeHandler, get question text from conversation history
                    question_text = None
                    for speaker, text in reversed(handler.conversation_history):
                        if speaker == "Agent":
                            question_text = text
                            break
                    handler.save_response(current_question_key, speech_result, question_text=question_text)
                else:
                    # For regular QuestionnaireHandler
                    question_text = getattr(handler, '_current_question_text', None)
                    handler.save_response(current_question_key, speech_result, question_text=question_text)
                print(f"Saved response for {current_question_key}: {speech_result}")

            # Play filler word immediately (while processing next question)
            # This makes the conversation feel more responsive
            language = getattr(handler, 'language', None)
            play_filler_word(vr, speech_result, request, language=language)
            print(f"Playing filler word for response: {speech_result[:30]}...")

            # Check if user shows disinterest - terminate call (legacy check)
            if not is_decision_tree and hasattr(handler, 'should_terminate') and handler.should_terminate:
                termination_msg = handler.get_termination_message()
                handler.add_agent_message(termination_msg)

                # Use ElevenLabs for natural termination message
                language = getattr(handler, 'language', None)
                play_elevenlabs_audio(vr, termination_msg, request, language=language)

                if call_sid:
                    _questionnaire_handlers.pop(call_sid, None)

                vr.hangup()
                return HttpResponse(str(vr), content_type="text/xml")

            # Check if questionnaire is completed
            if not is_decision_tree and hasattr(handler, 'is_completed') and handler.is_completed():
                completion_msg = handler.get_completion_message()

                # Add completion message to conversation history
                handler.add_agent_message(completion_msg)

                # Use ElevenLabs for completion message
                language = getattr(handler, 'language', None)
                print(f"Speaking completion message (language: {language or 'default'})")
                play_elevenlabs_audio(vr, completion_msg, request, language=language)

                # Clean up handler
                if call_sid:
                    _questionnaire_handlers.pop(call_sid, None)

                vr.hangup()
                return HttpResponse(str(vr), content_type="text/xml")

            # TIMING: Start measuring lag
            import time
            response_received_time = time.time()
            print(f"⏱️ TIMING: User response received at {response_received_time:.3f}")

            # Get next question
            # For DecisionTreeHandler, pass the user response for analysis and routing
            analysis_start_time = time.time()
            if is_decision_tree:
                question_data = handler.get_next_question(user_response=speech_result)
            else:
                question_data = handler.get_next_question()
            analysis_end_time = time.time()
            analysis_duration = analysis_end_time - analysis_start_time
            print(f"⏱️ TIMING: Response analysis took {analysis_duration:.3f} seconds")

            if not question_data:
                # No more questions, complete
                completion_msg = handler.get_completion_message()

                # Add completion message to conversation history
                handler.add_agent_message(completion_msg)

                # Use ElevenLabs for completion message
                language = getattr(handler, 'language', None)
                print(f"Speaking completion message (language: {language or 'default'})")
                play_elevenlabs_audio(vr, completion_msg, request, language=language)

                if call_sid:
                    _questionnaire_handlers.pop(call_sid, None)

                vr.hangup()
                return HttpResponse(str(vr), content_type="text/xml")

            question_text, question_key = question_data

            # TIMING: Question ready
            question_ready_time = time.time()
            question_prep_duration = question_ready_time - response_received_time
            print(f"⏱️ TIMING: Question ready after {question_prep_duration:.3f} seconds (from response received)")

            # Store question info for next iteration
            is_decision_tree = isinstance(handler, DecisionTreeHandler)
            if is_decision_tree:
                handler.current_question_id = question_key
            else:
                handler._current_question_key = question_key
                handler._current_question_text = question_text
            print(f"Asking question: {question_key} - {question_text}")

            # Add agent question to conversation history (if not already added)
            # DecisionTreeHandler adds it automatically, but regular handler needs it
            if not is_decision_tree:
                handler.add_agent_message(question_text)

            # TIMING: Start audio generation
            audio_start_time = time.time()

            # Use ElevenLabs for natural, lag-free conversation in Hinglish
            # Get language from handler to determine voice
            language = getattr(handler, 'language', None)
            print(f"Speaking question (language: {language or 'default'}): {question_text[:50]}...")
            play_elevenlabs_audio(vr, question_text, request, language=language)

            # TIMING: Audio generation complete
            audio_end_time = time.time()
            audio_duration = audio_end_time - audio_start_time
            total_lag = audio_end_time - response_received_time
            print(f"⏱️ TIMING: Audio generation took {audio_duration:.3f} seconds")
            print(f"⏱️ TIMING: TOTAL LAG from user response to audio ready: {total_lag:.3f} seconds")

            # Continue the conversation - add Gather AFTER the question
            process_speech_url = request.build_absolute_uri('/twilio/process-speech/')
            # Get Twilio language code based on handler language
            twilio_language = get_twilio_language_code(getattr(handler, 'language', None))
            gather = Gather(
                input='speech',
                action=process_speech_url,
                method='POST',
                speech_timeout='3',  # Wait 3 seconds after speech stops
                language=twilio_language,  # Language based on API parameter
                num_digits=0,  # Don't wait for digits, only speech
                timeout=15  # Total timeout: wait up to 30 seconds for user to speak
            )
            vr.append(gather)

            # If Gather times out (after 30 seconds), redirect back to retry
            # This only executes if Gather completely times out
            fallback_msg = "I didn't understand. Please repeat."
            language = getattr(handler, 'language', None) if handler else None
            play_elevenlabs_audio(vr, fallback_msg, request, language=language)
            vr.redirect(process_speech_url)
        except Exception as e:
            # If processing fails, use simple fallback
            print(f"Error in process_speech: {e}")
            import traceback
            traceback.print_exc()
            error_msg = "I apologize, there was an error. Please continue."
            language = getattr(handler, 'language', None) if handler else None
            play_elevenlabs_audio(vr, error_msg, request, language=language)
            # Add Gather to continue
            process_speech_url = request.build_absolute_uri('/twilio/process-speech/')
            # Get Twilio language code based on handler language
            twilio_language = get_twilio_language_code(getattr(handler, 'language', None))
            gather = Gather(
                input='speech',
                action=process_speech_url,
                method='POST',
                speech_timeout='3',  # Wait 3 seconds after speech stops
                language=twilio_language,  # Language based on API parameter
                num_digits=0,
                timeout=30  # Total timeout: wait up to 30 seconds for user to speak
            )
            vr.append(gather)
    else:
        # No speech result - ask user to repeat
        fallback_msg = "I didn't understand. Please repeat."
        language = getattr(handler, 'language', None) if handler else None
        play_elevenlabs_audio(vr, fallback_msg, request, language=language)
        # Add Gather to get input again
        process_speech_url = request.build_absolute_uri('/twilio/process-speech/')
        # Get Twilio language code based on handler language
        twilio_language = get_twilio_language_code(getattr(handler, 'language', None))
        gather = Gather(
            input='speech',
            action=process_speech_url,
            method='POST',
            speech_timeout='3',  # Wait 3 seconds after speech stops
            language=twilio_language,  # Language based on API parameter
            num_digits=0,  # Don't wait for digits, only speech
            timeout=30  # Total timeout: wait up to 30 seconds for user to speak
        )
        vr.append(gather)
        # If still no input after timeout, say goodbye and hangup
        goodbye_msg = "Thank you for your time. Goodbye!"
        language = getattr(handler, 'language', None) if handler else None
        play_elevenlabs_audio(vr, goodbye_msg, request, language=language)
        vr.hangup()

    # Debug: Print TwiML
    final_twiml = str(vr)
    print("Process Speech TwiML Response:")
    print(final_twiml)

    return HttpResponse(final_twiml, content_type="text/xml")


@csrf_exempt
def trigger_call_with_questionnaire(request):
    """
    API endpoint to trigger a call with questionnaire mapping and user data

    Expected JSON payload:
    {
        "event_name": "gyantv_survey",  # Maps to questionnaire type
        "phone_number": "+917491073491",
        "name": "John Doe",
        "gender": "male",  # or "female"
        "age": "25",
        "language": "hi"  # Language code: 'hi' (Hindi), 'en' (English), 'hinglish', etc.
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)

        # Required fields
        event_name = data.get('event_name')
        phone_number = data.get('phone_number')

        if not event_name:
            return JsonResponse({'error': 'event_name is required'}, status=400)

        if not phone_number:
            return JsonResponse({'error': 'phone_number is required'}, status=400)

        # User data (optional but recommended)
        user_name = data.get('name', '')
        user_gender = data.get('gender', '')
        user_age = data.get('age', '')
        language = data.get('language', '')  # Language code (e.g., 'hi', 'en', 'hinglish')

        # Validate phone number format (E.164)
        if not phone_number.startswith('+'):
            return JsonResponse({
                'error': 'Phone number must be in E.164 format (e.g., +917491073491)'
            }, status=400)

        # Initialize Twilio client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        # Make the call
        webhook_url = f"{settings.BASE_URL}/twilio/call/"
        print(f"📞 Making Twilio call to: {phone_number}")
        print(f"🌐 Webhook URL: {webhook_url}")
        print(f"📋 Call data: event={event_name}, name={user_name}, language={language}")

        # Get call time limit from settings (default 3 minutes = 180 seconds)
        call_time_limit = getattr(settings, 'CALL_TIME_LIMIT_SECONDS', 180)

        call = client.calls.create(
            to=phone_number,
            from_=settings.TWILIO_PHONE_NUMBER,
            url=webhook_url,
            method='POST',
            record=True,
            time_limit=call_time_limit,  # Maximum call duration in seconds
            recording_status_callback=f"{settings.BASE_URL}/twilio/recording-webhook/",
            recording_status_callback_method='POST',
            recording_channels='dual',
            recording_status_callback_event=['completed']
        )

        print(f"⏱️ Call time limit: {call_time_limit} seconds ({call_time_limit // 60} minutes)")

        print(f"✅ Call created: SID={call.sid}, Status={call.status}")

        # Store user data and event_name in a temporary storage
        # We'll retrieve this when the call starts
        call_data = {
            'event_name': event_name,
            'user_name': user_name,
            'user_gender': user_gender,
            'user_age': user_age,
            'phone_number': phone_number,
            'language': language,
            'call_sid': call.sid  # Store call SID for matching
        }

        # Store in a simple dict (in production, use Redis or database)
        # We'll use call_sid as key when call starts
        if not hasattr(trigger_call_with_questionnaire, '_pending_calls'):
            trigger_call_with_questionnaire._pending_calls = {}

        # Store by phone number AND call SID (for better matching)
        trigger_call_with_questionnaire._pending_calls[phone_number] = call_data
        # Also store by call SID for direct lookup
        if not hasattr(trigger_call_with_questionnaire, '_pending_calls_by_sid'):
            trigger_call_with_questionnaire._pending_calls_by_sid = {}
        trigger_call_with_questionnaire._pending_calls_by_sid[call.sid] = call_data

        print(f"💾 Stored call data: phone={phone_number}, sid={call.sid}, event={event_name}")

        return JsonResponse({
            'success': True,
            'call_sid': call.sid,
            'status': call.status,
            'event_name': event_name,
            'user_data': {
                'name': user_name,
                'gender': user_gender,
                'age': user_age,
                'language': language
            },
            'message': 'Call initiated successfully'
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
    except Exception as e:
        error_msg = str(e)
        if 'not verified' in error_msg.lower():
            return JsonResponse({
                'error': 'Number not verified. Trial accounts can only call verified numbers.',
                'help': 'Verify this number at: https://console.twilio.com/us1/develop/phone-numbers/manage/verified'
            }, status=400)
        return JsonResponse({'error': error_msg}, status=500)



@csrf_exempt
def make_outbound_call(request):
    """
    Make an outbound call with AI agent
    Recording is enabled and webhook is configured

    Note: Trial accounts can only call verified numbers.
    Paid accounts can call any valid phone number.
    """
    to_number = request.POST.get('to', '')

    if not to_number:
        return JsonResponse({'error': 'to number required'}, status=400)

    # Validate phone number format (E.164 format)
    import re
    if not re.match(r'^\+[1-9]\d{1,14}$', to_number):
        return JsonResponse({
            'error': 'Invalid phone number format. Use E.164 format (e.g., +1234567890)',
            'example': '+917491073491'
        }, status=400)

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    try:
        # Get call time limit from settings (default 3 minutes = 180 seconds)
        call_time_limit = getattr(settings, 'CALL_TIME_LIMIT_SECONDS', 180)

        call = client.calls.create(
            to=to_number,
            from_=settings.TWILIO_PHONE_NUMBER,
            url=f"{BASE_URL}/twilio/call/",
            record=True,  # Enable recording
            time_limit=call_time_limit,  # Maximum call duration in seconds
            recording_status_callback=f"{BASE_URL}/twilio/recording-webhook/",
            recording_status_callback_method='POST'
        )

        return JsonResponse({
            'success': True,
            'call_sid': call.sid,
            'status': call.status,
            'recording_enabled': True,
            'to_number': to_number
        })
    except Exception as e:
        # Handle specific Twilio errors
        error_msg = str(e)
        if 'not verified' in error_msg.lower() or 'verified' in error_msg.lower():
            return JsonResponse({
                'error': 'Number not verified. Trial accounts can only call verified numbers.',
                'help': 'Verify this number at: https://console.twilio.com/us1/develop/phone-numbers/manage/verified',
                'upgrade': 'Or upgrade to paid account to call any number: https://console.twilio.com/billing'
            }, status=400)
        return JsonResponse({'error': error_msg}, status=500)


@csrf_exempt
def receive_event(request):
    """
    Simple POST API to receive event data from frontend
    Accepts 'event_name' in payload and returns 201 status
    """
    if request.method != 'POST':
        return JsonResponse(
            {'error': 'Method not allowed'},
            status=405
        )

    try:
        data = json.loads(request.body)
        event_name = data.get('event_name')

        if not event_name:
            return JsonResponse(
                {'error': 'event_name is required'},
                status=400
            )

        # Return 201 Created status
        return JsonResponse({
            'success': True,
            'message': 'Event received successfully',
            'event_name': event_name
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Invalid JSON payload'},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=500
        )


@csrf_exempt
def twilio_recording_webhook(request):
    """Twilio webhook to receive recording URL and save to local media folder"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Extract recording information from Twilio webhook
        recording_url = request.POST.get('RecordingUrl')
        recording_sid = request.POST.get('RecordingSid')
        call_sid = request.POST.get('CallSid')
        recording_duration = request.POST.get('RecordingDuration')
        recording_status = request.POST.get('RecordingStatus')

        if not recording_url:
            return JsonResponse(
                {'error': 'RecordingUrl is required'},
                status=400
            )

        # Setup directories
        media_root = Path(settings.MEDIA_ROOT)
        media_root.mkdir(parents=True, exist_ok=True)
        recordings_dir = media_root / 'recordings'
        transcripts_dir = media_root / 'transcripts'
        recordings_dir.mkdir(exist_ok=True)
        transcripts_dir.mkdir(exist_ok=True)

        # Download and save recording with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if recording_sid:
            filename = f"{recording_sid}_{timestamp}.mp3"
        else:
            filename = f"recording_{timestamp}_{uuid.uuid4().hex[:8]}.mp3"
        file_path = recordings_dir / filename

        auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        response = requests.get(recording_url, auth=auth, stream=True, timeout=30)
        response.raise_for_status()

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # Get handler to retrieve user data
        handler = _questionnaire_handlers.get(call_sid)

        # Extract user data from handler
        user_name = getattr(handler, 'user_name', '') if handler else ''
        user_gender = getattr(handler, 'user_gender', '') if handler else ''
        user_age = getattr(handler, 'user_age', '') if handler else ''
        event_name = getattr(handler, 'event_name', '') if handler else ''
        user_responses = getattr(handler, 'responses', {}) if handler else {}

        # Get phone number from call (try From field, fallback to To)
        phone_number = request.POST.get('From', '') or request.POST.get('To', '')

        # Generate and save transcript
        transcript_text = None
        formatted_transcript = None
        transcript_file_path = None
        insights = None

        try:
            # Get conversation history from handler if available
            if handler and hasattr(handler, 'get_formatted_transcript'):
                formatted_transcript = handler.get_formatted_transcript()

            # Also get raw transcript from audio (using factory pattern)
            transcription_provider = getattr(settings, 'DEFAULT_TRANSCRIPTION_PROVIDER', 'gemini')
            transcript_text = transcribe_audio(str(file_path), provider=transcription_provider)

            # Generate LLM insights from transcript (non-blocking - errors won't break the flow)
            insights = None
            if formatted_transcript or transcript_text:
                transcript_for_insights = formatted_transcript or transcript_text
                try:
                    # Get LLM provider from settings or use default
                    llm_provider = getattr(settings, 'DEFAULT_LLM_PROVIDER', 'gemini')

                    # Prepare user data for insight generation
                    language = getattr(handler, 'language', 'hi') if handler else 'hi'
                    user_data_for_insights = {
                        'name': user_name,
                        'gender': user_gender,
                        'age': user_age,
                        'event_name': event_name,
                        'language': language
                    }

                    insights = generate_call_insights(
                        transcript_for_insights,
                        user_responses,
                        provider=llm_provider,
                        user_data=user_data_for_insights
                    )
                    if insights:
                        print(f"Generated insights for call {call_sid} using {llm_provider}")
                except Exception as e:
                    # Don't let insight generation errors break the call flow
                    print(f"Warning: Could not generate insights (non-critical): {e}")
                    insights = None

            if formatted_transcript:
                # Use formatted transcript with Agent/User labels
                # Add timestamp to transcript filename
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                transcript_file_path = transcripts_dir / f"{recording_sid}_{timestamp}.txt"
                with open(transcript_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Call Recording Transcript\n{'=' * 50}\n\n")
                    f.write(f"Recording SID: {recording_sid}\n")
                    f.write(f"Call SID: {call_sid}\n")
                    f.write(f"Duration: {recording_duration} seconds\n")
                    f.write(f"Status: {recording_status}\n")
                    f.write(f"Start Time: {request.POST.get('RecordingStartTime', 'N/A')}\n")
                    f.write(f"\n{'=' * 50}\n\nCONVERSATION:\n\n{formatted_transcript}\n")

                    # Also include raw transcript for reference
                    if transcript_text:
                        f.write(f"\n{'=' * 50}\n\nRAW TRANSCRIPT (from audio):\n\n{transcript_text}\n")
            elif transcript_text:
                # Fallback to raw transcript if no conversation history
                # Add timestamp to transcript filename
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                transcript_file_path = transcripts_dir / f"{recording_sid}_{timestamp}.txt"
                with open(transcript_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Call Recording Transcript\n{'=' * 50}\n\n")
                    f.write(f"Recording SID: {recording_sid}\n")
                    f.write(f"Call SID: {call_sid}\n")
                    f.write(f"Duration: {recording_duration} seconds\n")
                    f.write(f"Status: {recording_status}\n")
                    f.write(f"Start Time: {request.POST.get('RecordingStartTime', 'N/A')}\n")
                    f.write(f"\n{'=' * 50}\n\nTRANSCRIPT:\n\n{transcript_text}\n")
        except Exception as e:
            print(f"Error generating transcript: {e}")
            import traceback
            traceback.print_exc()
            transcript_text = None

        # Save comprehensive call data using storage module
        call_data_file_path = None
        try:
            from datetime import datetime

            # Prepare call data dictionary
            call_data_dict = {
                'user_name': user_name or '',
                'phone_number': phone_number or '',
                'user_gender': user_gender or '',
                'user_age': user_age or '',
                'event_name': event_name or '',
                'call_sid': call_sid or '',
                'recording_sid': recording_sid or '',
                'call_created_on': request.POST.get('RecordingStartTime', datetime.now().isoformat()),
                'duration': recording_duration or '',
                'status': recording_status or '',
                'recording_url': recording_url or '',
                'recording_file': filename,
                'recording_path': str(file_path),
                'transcript': formatted_transcript or transcript_text or '',
                'user_responses': user_responses,
                'insights': insights or ''
            }

            # Save using storage module
            call_data_file_path = save_call_data(call_data_dict)
            print("call_data_file_path: ", call_data_file_path)
        except Exception as e:
            print(f"Error saving call data: {e}")
            import traceback
            traceback.print_exc()

        # Return response
        response_data = {
            'success': True,
            'message': 'Recording saved successfully',
            'recording_sid': recording_sid,
            'call_sid': call_sid,
            'recording_duration': recording_duration,
            'recording_status': recording_status,
            'file_path': str(file_path),
            'file_url': f"{settings.MEDIA_URL}recordings/{filename}",
            'transcript_available': transcript_text is not None
        }
        if transcript_file_path:
            response_data.update({
                'transcript_file_path': str(transcript_file_path),
                'transcript_file_url': f"{settings.MEDIA_URL}transcripts/{recording_sid}.txt",
                'transcript_preview': transcript_text[:200] + "..." if len(transcript_text) > 200 else transcript_text
            })
        return JsonResponse(response_data, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
