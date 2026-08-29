import os

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

ELEVENLABS_API_KEY = os.environ["ELEVENLABS_API_KEY"]
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
MODEL_ID = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_v3")
MAX_TTS_TEXT_LENGTH = 5000

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)


def synthesize_speech(text: str) -> bytes:
    audio_chunks = client.text_to_speech.convert(
        text=text,
        voice_id=VOICE_ID,
        model_id=MODEL_ID,
        output_format="mp3_44100_128",
    )
    return b"".join(audio_chunks)
