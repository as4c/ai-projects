#!/usr/bin/env python3
"""
Test ElevenLabs Voice Generation
Simple script to test ElevenLabs TTS without making a phone call
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_researcher.settings')
django.setup()

from django.conf import settings
from ai_researcher.elevenlabs_client import generate_voice_response

def test_elevenlabs_voice():
    """Test ElevenLabs voice generation with Hinglish text"""

    # Test paragraph in Hinglish
    test_text = """
    Hello! Namaste! Main aapke GyanTV app ke experience ke baare mein jaanna chahta hoon.
    Hum aapse 5 minutes ka time chahenge. Kya yeh baat-cheet ke liye sahi time hai?
    Aap usually din ke kis time content dekhte hain? Jaise ki morning, evening,
    commute ke dauran, ya sone se pehle? Aap typically app par kitna time spend karte hain?
    """

    print("Testing ElevenLabs Voice Generation...")
    print(f"Text to convert: {test_text[:100]}...")
    print("\nGenerating audio...")

    # Use Hindi voice for Hinglish
    voice_id = settings.ELEVENLABS_VOICE_ID  # Hindi voice (Ananya) from settings

    try:
        api_key = settings.ELEVENLABS_API_KEY
        if api_key.endswith('_residency_in'):
            print("📍 Using India data residency endpoint (api.in.residency.elevenlabs.io)")
        elif api_key.endswith('_residency_eu'):
            print("📍 Using EU data residency endpoint (api.eu.residency.elevenlabs.io)")
        else:
            print("📍 Using global endpoint (api.elevenlabs.io)")
        print(f"🚀 Model: {settings.ELEVENLABS_MODEL_ID} (low latency)")

        # Generate audio using official SDK pattern
        audio_data = generate_voice_response(test_text, voice_id=voice_id)

        if audio_data:
            # Save to file
            output_file = "test_elevenlabs_voice.mp3"
            with open(output_file, "wb") as f:
                f.write(audio_data)

            file_size = len(audio_data)
            print(f"✅ Success! Audio generated and saved to: {output_file}")
            print(f"   File size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
            print(f"\n🎵 Play the file to hear the voice:")
            print(f"   - On Mac: open {output_file}")
            print(f"   - On Linux: xdg-open {output_file}")
            print(f"   - On Windows: start {output_file}")
            print(f"\n   Or use any media player to play: {output_file}")
            return True
        else:
            print("❌ Error: No audio data generated")
            return False

    except Exception as e:
        print(f"❌ Error generating voice: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_voices():
    """Test different voice options"""

    voices = {
        "Hindi (Ananya)": settings.ELEVENLABS_VOICE_ID,
        "English (Rachel)": "21m00Tcm4TlvDq8ikWAM",
    }

    test_text = "Hello! This is a test of ElevenLabs voice generation."

    print("\n" + "="*60)
    print("Testing Multiple Voices")
    print("="*60)

    for voice_name, voice_id in voices.items():
        print(f"\nTesting {voice_name} (ID: {voice_id})...")
        try:
            audio_data = generate_voice_response(test_text, voice_id=voice_id)
            if audio_data:
                output_file = f"test_voice_{voice_name.replace(' ', '_').lower()}.mp3"
                with open(output_file, "wb") as f:
                    f.write(audio_data)
                print(f"✅ Saved to: {output_file}")
            else:
                print(f"❌ Failed to generate audio")
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("="*60)
    print("ElevenLabs Voice Test Script")
    print("="*60)

    # Check API key
    if not hasattr(settings, 'ELEVENLABS_API_KEY') or not settings.ELEVENLABS_API_KEY:
        print("❌ Error: ELEVENLABS_API_KEY not found in settings")
        print("   Please set it in settings.py or as environment variable")
        sys.exit(1)

    print(f"API Key: {settings.ELEVENLABS_API_KEY[:10]}... (hidden)")

    # Test main voice
    success = test_elevenlabs_voice()

    if success:
        # Optionally test multiple voices
        response = input("\nTest multiple voices? (y/n): ").strip().lower()
        if response == 'y':
            test_multiple_voices()

    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60)

