from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
import os

client = ElevenLabs(
    api_key=os.getenv("API_KEY", "")
)

audio = client.text_to_speech.convert(
    text="The first move is what sets everything in motion.",
    voice_id="93nuHbke4dTER9x2pDwE",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
)

play(audio)
