"""Regenerate the Constantine story-review V5 narration with the approved voice profile.

Same 29 approved cues and the same slot-fitting rules as the restrained Nayva pass;
only the voice changes, to the profile already locked in for COLONY
(voice_profiles/colony_original_normal.json).
"""
from __future__ import annotations

import hashlib
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
OUTPUT = ROOT / "Constantine" / "story_review_v5" / "output"
SRT_PATH = OUTPUT / "narration_v4_outro_en.srt"
AUDIO_ROOT = OUTPUT / "narration_audio_selected_voice"
RAW_DIR = AUDIO_ROOT / "raw"
FITTED_DIR = AUDIO_ROOT / "fitted"
PROFILE_PATH = ROOT / "voice_profiles" / "colony_original_normal.json"
EXPECTED_CUES = 29


def load_profile() -> dict:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    # Hash the canonical JSON, not the raw bytes, so the value matches the
    # profile_sha256 that generate_narration_audio.py records for COLONY.
    profile["_sha256"] = hashlib.sha256(
        json.dumps(profile, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return profile


def media_duration(path: Path) -> float:
    return float(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            text=True, encoding="utf-8",
        ).strip()
    )


def request_speech(key: str, profile: dict, cue_number: int, text: str, output: Path) -> None:
    # Matches the approved profile: no voice_settings override, provider defaults.
    payload = json.dumps(
        {
            "text": text,
            "model_id": profile["model_id"],
            "language_code": profile["language_code"],
            "apply_text_normalization": "auto",
        }
    ).encode("utf-8")
    query = urllib.parse.urlencode({"output_format": "mp3_44100_128"})
    request = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{profile['voice_id']}?{query}",
        data=payload,
        method="POST",
        headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                audio = response.read()
            if len(audio) < 1000:
                raise RuntimeError(f"Invalid audio payload for cue {cue_number}")
            output.write_bytes(audio)
            return
        except urllib.error.HTTPError as exc:
            if attempt == 3 or exc.code not in {429, 500, 502, 503, 504}:
                detail = exc.read().decode("utf-8", errors="replace")[:600]
                raise RuntimeError(
                    f"ElevenLabs request failed for cue {cue_number}: HTTP {exc.code}: {detail}"
                ) from None
            time.sleep(attempt * 2)


def fit_audio(raw: Path, output: Path, slot_duration: float, profile: dict) -> dict[str, float]:
    """Trim, fit to the caption slot, and normalise exactly as the profile prescribes."""
    trimmed = output.with_suffix(".trimmed.wav")
    trim_filter, _, loudness_filter = profile["postprocess"]["ffmpeg_filter"].rpartition(",")
    # The fitting pass has to insert atempo between the two halves, so the split must hold.
    if not loudness_filter.startswith("loudnorm=") or "silenceremove" not in trim_filter:
        raise RuntimeError(
            "Profile filter is not in the expected 'silenceremove...,loudnorm=...' shape: "
            f"{profile['postprocess']['ffmpeg_filter']}"
        )
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af", trim_filter,
         "-ar", "48000", "-ac", "1", str(trimmed)],
        check=True,
    )
    trimmed_duration = media_duration(trimmed)
    target_max = max(0.5, slot_duration - 0.12)
    atempo = max(0.96, trimmed_duration / target_max)
    if atempo > 1.35:
        raise RuntimeError(f"Cue {raw.name} requires unnatural {atempo:.3f}x speed")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(trimmed),
         "-af", f"atempo={atempo:.6f},{loudness_filter},atrim=duration={target_max:.6f}",
         "-ar", "48000", "-ac", "1", "-c:a", "pcm_s24le", str(output)],
        check=True,
    )
    trimmed.unlink(missing_ok=True)
    return {
        "raw_duration_sec": media_duration(raw),
        "trimmed_duration_sec": trimmed_duration,
        "fitted_duration_sec": media_duration(output),
        "slot_duration_sec": slot_duration,
        "atempo": atempo,
    }


def main() -> int:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not available in this process.")
    profile = load_profile()
    cues = parse_srt(SRT_PATH)
    if len(cues) != EXPECTED_CUES:
        raise RuntimeError(f"Expected {EXPECTED_CUES} approved cues, found {len(cues)}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FITTED_DIR.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, object]] = []
    for index, cue in enumerate(cues, 1):
        raw = RAW_DIR / f"cue_{index:03d}.mp3"
        fitted = FITTED_DIR / f"cue_{index:03d}.wav"
        if not raw.exists() or raw.stat().st_size < 1000:
            request_speech(key, profile, index, cue.text, raw)
        metrics = fit_audio(raw, fitted, cue.end - cue.start, profile)
        manifest.append(
            {
                "cue": index,
                "start_sec": cue.start,
                "end_sec": cue.end,
                "text": cue.text,
                "voice_id": profile["voice_id"],
                "model": profile["model_id"],
                "voice_settings": "voice defaults (no request override)",
                "profile_id": profile["profile_id"],
                "profile_sha256": profile["_sha256"],
                "raw_file": str(raw),
                "fitted_file": str(fitted),
                **metrics,
            }
        )
        print(
            f"cue {index:02d}/{EXPECTED_CUES} ready | "
            f"{metrics['fitted_duration_sec']:.2f}s in {metrics['slot_duration_sec']:.2f}s slot | "
            f"atempo {metrics['atempo']:.3f}",
            flush=True,
        )

    report = {
        "schema_version": 3,
        "voice_id": profile["voice_id"],
        "model": profile["model_id"],
        "voice_settings": "voice defaults (no request override)",
        "profile_id": profile["profile_id"],
        "profile_sha256": profile["_sha256"],
        "replaces": "narration_audio_nayva_v2_restrained (Nayva cfc7wVYq4gw4OpcEEAom)",
        "baseline_pace": 0.96,
        "cue_count": len(manifest),
        "max_atempo": max(float(item["atempo"]) for item in manifest),
        "overrun_count": sum(
            float(item["fitted_duration_sec"]) > float(item["slot_duration_sec"])
            for item in manifest
        ),
        "cues": manifest,
    }
    (AUDIO_ROOT / "manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(
        {k: report[k] for k in
         ("voice_id", "model", "profile_id", "cue_count", "max_atempo", "overrun_count")},
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
