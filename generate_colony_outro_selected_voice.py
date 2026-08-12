from __future__ import annotations

import json
import os
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output" / "outro_v5"
CAPCUT_DIR = ROOT / "output" / "capcut_import" / "outro_v5"
VOICE_PATH = OUTPUT_DIR / "outro_selected_voice_en.mp3"
VIDEO_PATH = OUTPUT_DIR / "colony_outro_v5_selected_voice.mp4"
CAPCUT_VOICE_PATH = CAPCUT_DIR / VOICE_PATH.name
CAPCUT_VIDEO_PATH = CAPCUT_DIR / VIDEO_PATH.name
MANIFEST_PATH = OUTPUT_DIR / "selected_voice_manifest.json"

VOICE_ID = "Vuo6zmtjWmlDbzqgIDos"
MODEL_ID = "eleven_v3"
TEXT = (
    "This was Colony... a thriller where humanity's only hope may hide its darkest "
    "secret. I'll be back with another story worth discovering. If you enjoyed the "
    "review, leave a like and subscribe."
)


def duration(path: Path) -> float:
    return float(
        subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1", str(path),
            ],
            text=True,
            encoding="utf-8",
        ).strip()
    )


def main() -> int:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not available in this process.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CAPCUT_DIR.mkdir(parents=True, exist_ok=True)
    query = urllib.parse.urlencode({"output_format": "mp3_44100_128"})
    request = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?{query}",
        data=json.dumps(
            {
                "text": TEXT,
                "model_id": MODEL_ID,
                "language_code": "en",
                "apply_text_normalization": "auto",
            }
        ).encode("utf-8"),
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
        raise RuntimeError("ElevenLabs returned an invalid outro audio payload.")
    VOICE_PATH.write_bytes(audio)

    voice_duration = duration(VOICE_PATH)
    if voice_duration > 13.35:
        raise RuntimeError(
            f"Outro voice is too long for the approved caption window: {voice_duration:.3f}s"
        )

    music_rise = min(13.35, voice_duration + 0.15)
    filter_complex = (
        f"[1:a]adelay=100|100,volume=0.60[voice];"
        f"[2:a]atrim=start=15:duration=16.6,asetpts=PTS-STARTPTS,"
        f"volume='if(lt(t,{music_rise:.3f}),0.32,0.78)':eval=frame,"
        "afade=t=out:st=15.6:d=1.0[music];"
        "[voice][music]amix=inputs=2:duration=longest:normalize=0,"
        "alimiter=limit=0.891251[aout]"
    )
    source_video = OUTPUT_DIR / "colony_outro_v5.mp4"
    music_path = ROOT / "The Final Resolve.mp3"
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(source_video),
            "-i", str(VOICE_PATH),
            "-i", str(music_path),
            "-filter_complex", filter_complex,
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", "16.6", "-movflags", "+faststart", str(VIDEO_PATH),
        ],
        check=True,
    )
    CAPCUT_VOICE_PATH.write_bytes(VOICE_PATH.read_bytes())
    CAPCUT_VIDEO_PATH.write_bytes(VIDEO_PATH.read_bytes())

    manifest = {
        "voice_id": VOICE_ID,
        "model": MODEL_ID,
        "voice_settings": "voice defaults (no request override)",
        "text": TEXT,
        "voice_duration_sec": round(voice_duration, 3),
        "video_duration_sec": round(duration(VIDEO_PATH), 3),
        "voice_file": str(VOICE_PATH),
        "video_file": str(VIDEO_PATH),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
