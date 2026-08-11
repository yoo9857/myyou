from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from pipeline import parse_srt


ROOT = Path(__file__).resolve().parent
REVIEW_ROOT = ROOT / "Constantine" / "story_review_v5"
OUTPUT = REVIEW_ROOT / "output"
SRT_PATH = OUTPUT / "narration_v4_outro_en.srt"
AUDIO_ROOT = OUTPUT / "narration_audio_nayva_v1"
RAW_DIR = AUDIO_ROOT / "raw"
FITTED_DIR = AUDIO_ROOT / "fitted"
VOICE_ID = "cfc7wVYq4gw4OpcEEAom"
MODEL_ID = "eleven_v3"
VOICE_NAME = "Nayva"

NAME_CUES = {1, 4, 8, 12, 16, 19, 23, 25, 28}
TENSION_CUES = {4, 10, 15, 19, 25, 27}
COMIC_CUES = {3, 6, 14, 21, 24}


def tone_for(cue: int) -> tuple[str, str]:
    if cue == 29:
        return "softly", "spoiler-safe close"
    if cue in TENSION_CUES:
        return "tense", "restrained danger"
    if cue in COMIC_CUES:
        return "dryly", "dry American-style understatement"
    if cue in NAME_CUES:
        return "intrigued", "character or clue emphasis"
    return "thoughtful", "causal and atmospheric bridge"


def media_duration(path: Path) -> float:
    raw = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        text=True,
        encoding="utf-8",
    )
    return float(raw.strip())


def request_speech(key: str, cue: int, text: str, previous_text: str, next_text: str, output: Path) -> None:
    tone, _ = tone_for(cue)
    spoken_input = f"[{tone}] {text.replace('…', '...')}"
    payload: dict[str, object] = {
        "text": spoken_input,
        "model_id": MODEL_ID,
        "language_code": "en",
        "apply_text_normalization": "auto",
    }
    # Eleven v3 currently rejects previous_text/next_text. Keep these arguments
    # in the function contract so a future compatible model can restore request
    # stitching without changing the cue-generation loop.
    query = urllib.parse.urlencode({"output_format": "mp3_44100_128"})
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?{query}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                audio = response.read()
            if len(audio) < 1000:
                raise RuntimeError(f"ElevenLabs returned an invalid audio payload for cue {cue}.")
            output.write_bytes(audio)
            return
        except urllib.error.HTTPError as exc:
            if attempt == 3 or exc.code not in {429, 500, 502, 503, 504}:
                detail = exc.read().decode("utf-8", errors="replace")[:1000]
                raise RuntimeError(f"ElevenLabs request failed for cue {cue}: HTTP {exc.code}: {detail}") from None
            time.sleep(attempt * 2)


def fit_audio(raw: Path, output: Path, slot_duration: float) -> dict[str, float]:
    trimmed = output.with_suffix(".trimmed.wav")
    trim_filter = (
        "silenceremove=start_periods=1:start_duration=0.04:start_threshold=-50dB,"
        "areverse,silenceremove=start_periods=1:start_duration=0.08:start_threshold=-50dB,areverse"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af", trim_filter, "-ar", "48000", "-ac", "1", str(trimmed)],
        check=True,
    )
    trimmed_duration = media_duration(trimmed)
    target_max = max(0.5, slot_duration - 0.12)
    # Nayva's established review pace is 0.94-0.98. Use 0.96 unless the cue
    # would overrun, then apply only the speed-up required to fit.
    atempo = max(0.96, trimmed_duration / target_max)
    if atempo > 1.35:
        raise RuntimeError(
            f"Cue needs an unnatural {atempo:.3f}x speed-up; shorten the line instead: {raw.name}"
        )
    final_filter = f"atempo={atempo:.6f},loudnorm=I=-16.5:TP=-1.5:LRA=7,atrim=duration={target_max:.6f}"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(trimmed),
            "-af",
            final_filter,
            "-ar",
            "48000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s24le",
            str(output),
        ],
        check=True,
    )
    trimmed.unlink(missing_ok=True)
    fitted_duration = media_duration(output)
    return {
        "raw_duration_sec": media_duration(raw),
        "trimmed_duration_sec": trimmed_duration,
        "fitted_duration_sec": fitted_duration,
        "slot_duration_sec": slot_duration,
        "atempo": atempo,
    }


def main() -> int:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not available in this process.")
    cues = parse_srt(SRT_PATH)
    if len(cues) != 29:
        raise RuntimeError(f"Expected 29 approved review cues, found {len(cues)}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FITTED_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for index, cue in enumerate(cues, 1):
        raw = RAW_DIR / f"cue_{index:03d}.mp3"
        fitted = FITTED_DIR / f"cue_{index:03d}.wav"
        previous_text = cues[index - 2].text if index > 1 else ""
        next_text = cues[index].text if index < len(cues) else ""
        if not raw.exists() or raw.stat().st_size < 1000:
            request_speech(key, index, cue.text, previous_text, next_text, raw)
        metrics = fit_audio(raw, fitted, cue.end - cue.start)
        tag, purpose = tone_for(index)
        manifest.append(
            {
                "cue": index,
                "start_sec": cue.start,
                "end_sec": cue.end,
                "text": cue.text,
                "voice": VOICE_NAME,
                "voice_id": VOICE_ID,
                "model": MODEL_ID,
                "tone_tag": tag,
                "tone_purpose": purpose,
                "raw_file": str(raw),
                "fitted_file": str(fitted),
                **metrics,
            }
        )
        print(f"Nayva cue {index:02d}/29 ready | {tag} | {metrics['fitted_duration_sec']:.2f}s")
    report = {
        "schema_version": 1,
        "voice": VOICE_NAME,
        "voice_id": VOICE_ID,
        "model": MODEL_ID,
        "language": "en",
        "baseline_pace": 0.96,
        "cue_count": len(manifest),
        "max_atempo": max(float(item["atempo"]) for item in manifest),
        "overrun_count": sum(float(item["fitted_duration_sec"]) > float(item["slot_duration_sec"]) for item in manifest),
        "cues": manifest,
    }
    (AUDIO_ROOT / "manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: report[key] for key in ("voice", "model", "cue_count", "max_atempo", "overrun_count")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
