from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cue_range(cue: dict, name: str, errors: list[str], duration: float) -> tuple[float, float]:
    try:
        start, end = float(cue["start"]), float(cue["end"])
    except (KeyError, TypeError, ValueError):
        errors.append(f"{name.upper()}_TIME")
        return 0.0, 0.0
    if not 0 <= start < end <= duration:
        errors.append(f"{name.upper()}_RANGE")
    if not str(cue.get("text", "")).strip():
        errors.append(f"{name.upper()}_TEXT")
    return start, end


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a spoiler-safe movie-review outro plan")
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.plan.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"OUTRO_PLAN_UNREADABLE: {exc}", file=sys.stderr)
        return 2

    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("SCHEMA_VERSION")
    try:
        duration = float(data["duration_sec"])
        source_start = float(data["source_start"])
        source_end = float(data["source_end"])
    except (KeyError, TypeError, ValueError):
        print("OUTRO_TIME_FIELDS", file=sys.stderr)
        return 1
    if not 14.0 <= duration <= 18.0:
        errors.append("OUTRO_DURATION")
    if source_end - source_start + 0.05 < duration:
        errors.append("SOURCE_INTERVAL_TOO_SHORT")
    cutoff = data.get("spoiler_cutoff_source_sec")
    if cutoff is not None and source_end > float(cutoff):
        errors.append("SPOILER_CUTOFF")
    if data.get("spoiler_safe") is not True:
        errors.append("SPOILER_SAFE_REQUIRED")
    if data.get("movie_audio_muted") is not True:
        errors.append("MOVIE_AUDIO_NOT_MUTED")
    if data.get("movie_captions_suppressed") is not True:
        errors.append("MOVIE_CAPTIONS_NOT_SUPPRESSED")

    review_start, review_end = cue_range(data.get("review_cue", {}), "review", errors, duration)
    cta_start, cta_end = cue_range(data.get("cta_cue", {}), "cta", errors, duration)
    if max(review_start, cta_start) < min(review_end, cta_end):
        errors.append("SPEECH_CUE_OVERLAP")

    music = data.get("music", {})
    try:
        music_start = float(music["start"])
        rise_start = float(music["rise_start"])
        fade_start = float(music["fade_out_start"])
        music_end = float(music["end"])
    except (KeyError, TypeError, ValueError):
        errors.append("MUSIC_TIME")
    else:
        if not 0 <= music_start <= max(review_start, 0.0):
            errors.append("MUSIC_START")
        if rise_start < max(review_end, cta_end):
            errors.append("MUSIC_RISE_BEFORE_SPEECH_END")
        if not rise_start <= fade_start < music_end <= duration + 0.01:
            errors.append("MUSIC_FADE_RANGE")

    for key in ("video_fade_out_sec", "audio_fade_out_sec"):
        try:
            fade = float(data[key])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{key.upper()}_MISSING")
            continue
        if not 0.5 <= fade <= 1.5:
            errors.append(f"{key.upper()}_RANGE")

    report = {"duration_sec": duration, "errors": errors}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
