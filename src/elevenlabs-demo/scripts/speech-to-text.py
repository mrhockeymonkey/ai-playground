# example.py
import json
import os
from elevenlabs.client import ElevenLabs

elevenlabs = ElevenLabs(
  api_key=os.getenv("API_KEY"),
)

audio_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "05-toucan-oiseaux-foret-pluviale-canopee.m4a",
)

with open(audio_path, "rb") as audio_data:
    transcription = elevenlabs.speech_to_text.convert(
        file=audio_data,
        model_id="scribe_v2", # Model to use
        tag_audio_events=True, # Tag audio events like laughter, applause, etc.
        language_code="fr", # Language of the audio file. If set to None, the model will detect the language automatically.
        diarize=True, # Whether to annotate who is speaking
    )

print(transcription)

audio_basename = os.path.splitext(os.path.basename(audio_path))[0]
output_dir = os.path.join(os.path.dirname(__file__), "..", "data")

json_path = os.path.join(output_dir, f"{audio_basename}.json")
with open(json_path, "w") as f:
    json.dump(transcription.model_dump(), f, indent=2)

text_path = os.path.join(output_dir, f"{audio_basename}.txt")
with open(text_path, "w") as f:
    f.write(transcription.text)
