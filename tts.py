import os
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()


def main():
    api_key = os.getenv("ELEVENLABS_API_KEY")

    if not api_key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY is not set in your .env file"
        )

    client = ElevenLabs(api_key=api_key)

    print("Generating speech...")

    audio = client.text_to_speech.convert(
        text=(
            "Hello! This is a test of ElevenLabs text to speech. "
            "If you can hear this, everything is working correctly."
        ),
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_v3",
        output_format="mp3_44100_128",
    )

    output_file = Path("output.mp3")

    with open(output_file, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    print(f"Done! Audio saved to: {output_file}")


if __name__ == "__main__":
    main()