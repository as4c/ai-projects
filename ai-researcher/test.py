
import os
import sys
import uuid
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_researcher.settings')
django.setup()

from django.conf import settings
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

# Use settings for API key
elevenlabs = ElevenLabs(
    api_key=settings.ELEVENLABS_API_KEY,
)


def text_to_speech_file(text: str) -> str:
    # Calling the text_to_speech conversion API with detailed parameters
    response = elevenlabs.text_to_speech.convert(
        voice_id=settings.ELEVENLABS_VOICE_ID,  # Hindi voice from settings
        output_format="mp3_22050_32",
        text=text,
        model_id="eleven_turbo_v2_5", # use the turbo model for low latency
        # Optional voice settings that allow you to customize the output
        voice_settings=VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True,
            speed=1.0,
        ),
    )

    # uncomment the line below to play the audio back
    # play(response)

    # Generating a unique file name for the output MP3 file
    save_file_path = f"{uuid.uuid4()}.mp3"

    # Writing the audio to a file
    with open(save_file_path, "wb") as f:
        for chunk in response:
            if chunk:
                f.write(chunk)

    print(f"{save_file_path}: A new audio file was saved successfully!")

    # Return the path of the saved audio file
    return save_file_path



test_text = """
Hello! Namaste! Main aapke GyanTV app ke experience ke baare mein jaanna chahta hoon.
Hum aapse 5 minutes ka time chahenge. Kya yeh baat-cheet ke liye sahi time hai?
Aap usually din ke kis time content dekhte hain? Jaise ki morning, evening,
commute ke dauran, ya sone se pehle? Aap typically app par kitna time spend karte hain?
"""


text_to_speech_file(test_text)
