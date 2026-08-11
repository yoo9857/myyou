from __future__ import annotations

import json
import os
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "Constantine" / "story_review_v5" / "output" / "voice_samples"
RAW_PATH = OUTPUT_DIR / "nayva_restrained_review_v2.raw.mp3"
FINAL_PATH = OUTPUT_DIR / "nayva_restrained_review_v2.mp3"
MANIFEST_PATH = OUTPUT_DIR / "nayva_restrained_review_v2.json"

VOICE_NAME = "Nayva"
VOICE_ID = "cfc7wVYq4gw4OpcEEAom"
MODEL_ID = "eleven_v3"
TEXT = (
    "He should be praying. Instead, Constantine studies the room with the calm "
    "of a man who's seen this far too many times."
)


def main() -> int:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not available in this process.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    query = urllib.parse.urlencode({"output_format": "mp3_44100_128"})
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?{query}"
    payload = json.dumps(
        {
            "text": TEXT,
            "model_id": MODEL_ID,
            "language_code": "en",
            "apply_text_normalization": "auto",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        audio = response.read()
    if len(audio) < 1000:
        raise RuntimeError("ElevenLabs returned an invalid audio payload.")
    RAW_PATH.write_bytes(audio)

    audio_filter = (
        "silenceremove=start_periods=1:start_duration=0.04:start_threshold=-50dB,"
        "areverse,silenceremove=start_periods=1:start_duration=0.08:start_threshold=-50dB,"
        "areverse,atempo=0.96,loudnorm=I=-16.5:TP=-1.5:LRA=7"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(RAW_PATH),
            "-af",
            audio_filter,
            "-ar",
            "48000",
            "-ac",
            "1",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(FINAL_PATH),
        ],
        check=True,
    )
    duration = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(FINAL_PATH),
            ],
            text=True,
            encoding="utf-8",
        ).strip()
    )
    manifest = {
        "voice": VOICE_NAME,
        "voice_id": VOICE_ID,
        "model": MODEL_ID,
        "delivery": "restrained, intimate, neutral American English",
        "emotion_tag": None,
        "pace": 0.96,
        "text": TEXT,
        "duration_sec": round(duration, 3),
        "file": str(FINAL_PATH),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
