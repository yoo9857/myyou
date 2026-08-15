"""Measure how far the narration sits above the film it is ducking, cue by cue.

The delivery gate wants a per-line lead in dB and skips when it has none. On a pipeline
that mixes the narration into each clip at render time there is no narration stem and no
bed to compare, so the gate skipped silently and the balance went unverified - which is the
same shape as the fault that let a Constantine deliverable pass while the wrong file was
being checked.

Nothing here is inferred. For each narration block the film bed is rebuilt from the source
with the render's own filter minus the voice, and its loudness is measured; the voice is
measured from the mp3 the review actually uses. The lead is the difference.

    python scripts/measure_balance.py devil/config.json

Writes BALANCE_QA.json beside the project's output.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

INTEGRATED = re.compile(r"^\s*I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", re.MULTILINE)
TRUE_PEAK = re.compile(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS")


def measure(args: list[str], prefix: str = "") -> tuple[float, float] | None:
    """Measure loudness and true peak, optionally through a filter chain first.

    The chain and the meter must be a single -af. Given as separate -filter:a and -af they
    are the same option, so only the meter survives and the downmix and duck the measurement
    was supposed to pass through are silently dropped.
    """
    chain = f"{prefix},ebur128=peak=true" if prefix else "ebur128=peak=true"
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", *args, "-af", chain, "-f", "null", "-"],
        capture_output=True, text=True,
    )
    loud = INTEGRATED.findall(result.stderr)
    peak = TRUE_PEAK.findall(result.stderr)
    if not loud:
        return None
    return float(loud[-1]), (float(peak[-1]) if peak else 0.0)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    config_path = Path(argv[0]).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.parent
    source = (root / config["video"]).resolve()
    timeline = root / "output" / "capcut_import" / "timeline.csv"
    rows = list(csv.DictReader(timeline.read_text(encoding="utf-8-sig").splitlines()))

    downmix = str(config.get("source_audio_downmix", "")).strip()
    quiet = float(config.get("narration_audio_level", 0.32))
    voice_gain = float(config.get("narration_voice_gain", 1.0))
    loud_level = float(config.get("dialogue_audio_level", 0.96))

    per_line, film_levels = [], []
    # Only blocks that actually carry a line. A narration block whose line was dropped
    # has no voice in the render, but an mp3 from an earlier plan may still sit at that
    # order, and measuring it reported more cues than the review contains.
    narration_rows = [r for r in rows
                      if r["kind"] == "narration" and r["narration"].strip()]
    for index, row in enumerate(narration_rows, start=1):
        order = int(row["order"])
        start = float(row["source_start"])
        span = float(row["source_end"]) - start
        # The bed as the render made it: the same downmix, held at the ducked level for the
        # whole block rather than ramped, because the ramp's endpoints are what matter and
        # the hold is what the voice actually competes with.
        level = float(row["audio_level"]) if row.get("audio_level") else quiet
        chain = f"{downmix + ',' if downmix else ''}volume={level:.6f},aresample=48000"
        bed = measure(["-ss", f"{start:.3f}", "-t", f"{span:.3f}", "-i", str(source),
                       "-map", "0:a:0"], chain)
        voice_file = root / "output" / "capcut_import" / "narration_audio" / f"clip_{order:03d}.mp3"
        if bed is None or not voice_file.exists():
            continue
        # The render applies narration_voice_gain to the voice; measuring the raw mp3 reported
        # a lead 4 dB better than the mix actually has.
        voice = measure(["-i", str(voice_file)],
                        f"volume={voice_gain:.4f},aresample=48000" if voice_gain != 1.0 else "")
        if voice is None:
            continue
        film_lufs, voice_lufs = bed[0], voice[0]
        film_levels.append(film_lufs)
        per_line.append({
            "cue": order,
            "timeline_start": float(row["timeline_start"]),
            "film_lufs": round(film_lufs, 2),
            "narration_lufs": round(voice_lufs, 2),
            "resulting_lead_db": round(voice_lufs - film_lufs, 2),
        })
        print(f"  {index:3}/{len(narration_rows)}  cue {order:3}  "
              f"영화 {film_lufs:7.2f}  해설 {voice_lufs:7.2f}  "
              f"우위 {voice_lufs - film_lufs:+6.2f} dB", flush=True)

    final = root / "output" / str(config.get("output_video", "rough_cut.mp4"))
    programme = measure(["-i", str(final)]) if final.exists() else None
    leads = sorted(line["resulting_lead_db"] for line in per_line)
    report = {
        "source": str(final.relative_to(root)).replace("\\", "/") if final.exists() else None,
        "method": "The narration is baked into each clip, so the film bed under it was "
                  "rebuilt from the source with the render's downmix and ducked level, and "
                  "the voice measured from the mp3 the review uses. No stem was available "
                  "to subtract, and nothing here is estimated from one.",
        "measured": {
            "programme_lufs": round(programme[0], 2) if programme else None,
            "programme_true_peak_dbtp": round(programme[1], 2) if programme else None,
            "narration_cues": len(per_line),
            "lead_db_min": leads[0] if leads else None,
            "lead_db_median": leads[len(leads) // 2] if leads else None,
            "lead_db_max": leads[-1] if leads else None,
        },
        "changes": {"duck": {"per_line": per_line}},
    }
    out = root / "output" / "BALANCE_QA.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if leads:
        print(f"\n  {len(leads)}구간  우위 최소 {leads[0]:+.2f} / 중간 "
              f"{leads[len(leads)//2]:+.2f} / 최대 {leads[-1]:+.2f} dB")
    print(f"  기록: {out.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
