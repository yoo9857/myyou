"""Solve each narration block's duck level from the film's measured loudness there.

One duck level for the whole review assumes every scene under narration is about as loud as
every other, and they are not. On The Devil All The Time a single fixed level of 0.32 held
48 of 49 cues comfortably above the film and left one - a loud passage at 15:31 - with the
narrator only 3.7 dB clear, under the 6 dB the delivery gate requires.

So the level is solved per cue instead: measure the film bed as the render will fold it
down, measure the voice file the review actually uses, and pick the level that puts the
voice the target distance above the bed. This is the lesson from the previous project, where
a fixed -6 dB duck turned out to be shallower than what the loud cues needed.

Never louder than the configured default, so a quiet scene is not pushed up, and never
below the floor, so the film does not disappear out from under the narration.

    python scripts/solve_duck.py devil/config.json [--target-lead-db 8.0]

Rewrites audio_level on the narration segments of output/edit_plan.json, which is the value
the render already reads. Run it before rendering.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from pathlib import Path

INTEGRATED = re.compile(r"^\s*I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", re.MULTILINE)


def loudness(args: list[str], prefix: str = "") -> float | None:
    """Measure integrated loudness, optionally through a filter chain first.

    The chain and the meter have to be one -af. Passing the chain as -filter:a and the meter
    as -af silently keeps only the meter - they are the same option - so a measurement meant
    to be taken through a downmix and a duck was taken on the raw source instead, and every
    number it produced was wrong in the same direction.
    """
    chain = f"{prefix},ebur128=peak=true" if prefix else "ebur128=peak=true"
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", *args, "-af", chain, "-f", "null", "-"],
        capture_output=True, text=True,
    )
    found = INTEGRATED.findall(result.stderr)
    return float(found[-1]) if found else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--target-lead-db", type=float, default=8.0,
                        help="Aim above the gate's 6 dB minimum so measurement noise cannot "
                             "drop a cue under it.")
    parser.add_argument("--floor", type=float, default=0.10,
                        help="Quietest the film may be pushed; below this it vanishes.")
    args = parser.parse_args()

    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.parent
    source = (root / config["video"]).resolve()
    plan_path = root / "output" / "edit_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    downmix = str(config.get("source_audio_downmix", "")).strip()
    default_level = float(config.get("narration_audio_level", 0.32))
    audio_dir = root / "output" / "capcut_import" / "narration_audio"

    narration = [s for s in plan["segments"]
                 if s["kind"] == "narration" and str(s.get("narration", "")).strip()]
    changed = []
    for index, segment in enumerate(narration, start=1):
        order = int(segment["order"])
        voice_file = audio_dir / f"clip_{order:03d}.mp3"
        if not voice_file.exists():
            continue
        start = float(segment["source_start"])
        span = float(segment["source_end"]) - start
        chain = f"{downmix + ',' if downmix else ''}aresample=48000"
        film = loudness(["-ss", f"{start:.3f}", "-t", f"{span:.3f}", "-i", str(source),
                         "-map", "0:a:0"], chain)
        voice = loudness(["-i", str(voice_file)])
        if film is None or voice is None:
            continue
        # A level of 1.0 leaves the bed at `film`; the wanted bed is target_lead below the
        # voice, and the level is the ratio between the two.
        wanted_bed = voice - args.target_lead_db
        level = min(default_level, max(args.floor, 10 ** ((wanted_bed - film) / 20.0)))
        previous = float(segment["audio_level"])
        segment["audio_level"] = round(level, 4)
        if abs(level - previous) > 0.005:
            changed.append((order, previous, level, film, voice))
        print(f"  {index:3}/{len(narration)}  cue {order:3}  원음 {film:7.2f}  해설 {voice:7.2f}"
              f"  더킹 {previous:.3f} -> {level:.3f}", flush=True)

    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    levels = sorted(float(s["audio_level"]) for s in narration)
    print(f"\n  {len(narration)}구간 중 {len(changed)}개 조정, "
          f"더킹 {levels[0]:.3f}~{levels[-1]:.3f}")
    for order, before, after, film, voice in changed:
        drop = 20 * math.log10(after / before)
        print(f"    cue {order:3}  {drop:+5.2f} dB 추가 (원음 {film:.1f} LUFS)")
    print(f"  기록: {plan_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
