import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DEFAULT_BASENAME = "05-toucan-oiseaux-foret-pluviale-canopee"

MAX_PAUSE_SECS = 1.0
MAX_CUE_CHARS = 84
MAX_CUE_SECS = 7.0
MAX_LINE_CHARS = 42

SENTENCE_END = (".", "?", "!", "…")
CLAUSE_END = (",", ";", ":")
CLOSING_CHARS = "»\"”’')] "


def is_sentence_end(text):
    return text.rstrip(CLOSING_CHARS).endswith(SENTENCE_END)


def cue_text(words):
    return " ".join(w["text"].strip() for w in words)


def too_long(words):
    return (
        len(cue_text(words)) > MAX_CUE_CHARS
        or words[-1]["end"] - words[0]["start"] > MAX_CUE_SECS
    )


def segment(words):
    cues = []
    current = []

    for word in words:
        if current:
            prev = current[-1]
            if (
                word.get("speaker_id") != prev.get("speaker_id")
                or word["start"] - prev["end"] > MAX_PAUSE_SECS
            ):
                cues.append(current)
                current = []

        current.append(word)

        if is_sentence_end(word["text"]):
            cues.append(current)
            current = []
        elif len(current) > 1 and too_long(current):
            split_at = next(
                (
                    i
                    for i in range(len(current) - 2, -1, -1)
                    if current[i]["text"].rstrip().endswith(CLAUSE_END)
                ),
                len(current) - 2,
            )
            cues.append(current[: split_at + 1])
            current = current[split_at + 1 :]

    if current:
        cues.append(current)
    return cues


def wrap(text):
    if len(text) <= MAX_LINE_CHARS:
        return text
    middle = len(text) // 2
    spaces = [
        i for i, c in enumerate(text) if c == " " and text[i + 1] not in ":;?!»"
    ]
    if not spaces:
        return text
    split = min(spaces, key=lambda i: abs(i - middle))
    return text[:split] + "\n" + text[split + 1 :]


def format_timestamp(secs):
    millis = round(secs * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    seconds, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def to_srt(transcription):
    words = [w for w in transcription["words"] if w["type"] == "word"]
    cues = segment(words)

    blocks = []
    for index, cue in enumerate(cues):
        start = cue[0]["start"]
        end = cue[-1]["end"]
        if index + 1 < len(cues):
            end = min(end, cues[index + 1][0]["start"])
        blocks.append(
            f"{index + 1}\n"
            f"{format_timestamp(start)} --> {format_timestamp(end)}\n"
            f"{wrap(cue_text(cue))}\n"
        )
    return "\n".join(blocks)


if __name__ == "__main__":
    basename = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASENAME

    with open(os.path.join(DATA_DIR, f"{basename}.json"), encoding="utf-8") as f:
        transcription = json.load(f)

    srt_path = os.path.join(DATA_DIR, f"{basename}.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(to_srt(transcription))

    print(f"Wrote {srt_path}")
