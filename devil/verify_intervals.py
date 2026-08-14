"""Pull one frame per story-map event so the selected intervals can actually be looked at.

The timings were derived by reading the film's subtitle track, not by watching it. A
subtitle tells you when someone speaks, not what is on screen, and several beats here are
silent action — a dog carried up a hill, a body on a kitchen floor. `needs_visual_review`
stays true until these frames confirm the interval shows what the summary claims.

Writes contact sheets of nine, labelled with event id and timecode.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORY_MAP = ROOT / "story_map.v1.json"
WORK = ROOT / "work" / "interval_check"
CONFIG = ROOT / "config.json"
PER_SHEET = 9
THUMB_W = 480


def main() -> int:
    story = json.loads(STORY_MAP.read_text(encoding="utf-8"))
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    source = (ROOT / config["video"]).resolve()
    WORK.mkdir(parents=True, exist_ok=True)
    for stale in WORK.glob("*"):
        stale.unlink()

    shots = []
    for section in story["sections"]:
        for event in section["events"]:
            start, end = event["selected_intervals"][0]
            at = start + (end - start) * 0.5
            shots.append((event["id"], at, event["summary"]))

    frames = []
    for index, (eid, at, summary) in enumerate(shots):
        out = WORK / f"{index:02d}_{eid}.jpg"
        label = f"{index:02d} {eid}  {int(at)//60}:{int(at)%60:02d}"
        drawn = label.replace(":", r"\:").replace("'", "")
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-hwaccel", "cuda",
             "-ss", f"{at:.3f}", "-i", str(source), "-frames:v", "1",
             "-vf", f"scale={THUMB_W}:-2,"
                    f"drawtext=text='{drawn}':x=8:y=8:fontsize=20:fontcolor=white:"
                    "box=1:boxcolor=black@0.65:boxborderw=6",
             "-q:v", "3", "-y", str(out)],
            check=True,
        )
        frames.append(out)
        print(f"  {index:02d} {int(at)//60:>3}:{int(at)%60:02d}  {eid:26} {summary[:44]}")

    sheets = []
    for start in range(0, len(frames), PER_SHEET):
        batch = frames[start:start + PER_SHEET]
        sheet = WORK / f"sheet_{start//PER_SHEET + 1}.jpg"
        inputs = []
        for path in batch:
            inputs += ["-i", str(path)]
        rows = (len(batch) + 2) // 3
        # tile works on successive frames of one stream, not on separate inputs, so the
        # stills have to be concatenated into a stream first. Feeding tile several inputs
        # silently lays down only the first and leaves the rest of the grid black.
        chain = "".join(f"[{i}:v]" for i in range(len(batch)))
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", *inputs,
             "-filter_complex",
             f"{chain}concat=n={len(batch)}:v=1:a=0[s];[s]tile=3x{rows}:padding=6:color=black[o]",
             "-map", "[o]", "-frames:v", "1", "-q:v", "3", "-y", str(sheet)],
            check=True,
        )
        sheets.append(sheet)

    print(f"\n프레임 {len(frames)}장, 시트 {len(sheets)}장")
    for sheet in sheets:
        print(f"  {sheet.relative_to(ROOT.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
