#!/usr/bin/env python3
"""
Simple ElevenLabs Voice Test (No Django Required)
Quick test script to generate audio from text
Uses official ElevenLabs SDK pattern with India data residency endpoint
"""
import os
import uuid

# Your ElevenLabs API Key (India data residency)
ELEVENLABS_API_KEY = "sk_0b42a640fabeed3b3e3fe03a3ca66d14f89d70ff0751c645_residency_in"

# Test paragraph in Hinglish
TEST_TEXT = """
Hello! Namaste! Main aapke GyanTV app ke experience ke baare mein jaanna chahta hoon.
Hum aapse 5 minutes ka time chahenge. Kya yeh baat-cheet ke liye sahi time hai?
Aap usually din ke kis time content dekhte hain? Jaise ki morning, evening,
commute ke dauran, ya sone se pehle?
"""

# Voice ID for Hindi/Hinglish
VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Ananya - Hindi voice

def generate_voice(text, voice_id=VOICE_ID):
    """Generate voice audio using ElevenLabs SDK (official pattern)"""
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import VoiceSettings

        # Initialize client with India data residency endpoint
        # Since you're using in.residency.elevenlabs.io, use the India API endpoint
        elevenlabs = ElevenLabs(
            api_key=ELEVENLABS_API_KEY,
            base_url="https://api.in.residency.elevenlabs.io"  # India data residency endpoint
        )

        print("🔄 Generating audio with ElevenLabs SDK (India data residency)...")

        # Call text_to_speech conversion API with detailed parameters
        response = elevenlabs.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_22050_32",  # Good quality, reasonable file size
            text=text,
            model_id="eleven_turbo_v2_5",  # Turbo model for low latency
            # Voice settings for customization
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
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
        print("❌ Error: elevenlabs package not installed")
        print("   Install with: pip install elevenlabs")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("="*60)
    print("ElevenLabs Voice Test (Simple)")
    print("="*60)
    print(f"\n📝 Text to convert:")
    print(f"{TEST_TEXT[:100]}...")
    print(f"\n🎤 Voice ID: {VOICE_ID}")
    print(f"🔑 API Key: {ELEVENLABS_API_KEY[:20]}...")
    print(f"🚀 Model: eleven_turbo_v2_5 (low latency)")

    # Generate audio
    audio_data = generate_voice(TEST_TEXT)

    if audio_data:
        # Generate unique filename
        output_file = f"test_elevenlabs_{uuid.uuid4().hex[:8]}.mp3"

        # Save to file
        with open(output_file, "wb") as f:
            f.write(audio_data)

        file_size = len(audio_data)
        print(f"\n✅ Success!")
        print(f"📁 File saved: {output_file}")
        print(f"📊 Size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
        print(f"\n🎵 To play the file:")
        print(f"   Mac: open {output_file}")
        print(f"   Linux: xdg-open {output_file}")
        print(f"   Windows: start {output_file}")
        print(f"\n   Or just double-click the file!")
    else:
        print("\n❌ Failed to generate audio")
        print("   Check your API key and internet connection")

if __name__ == "__main__":
    main()
