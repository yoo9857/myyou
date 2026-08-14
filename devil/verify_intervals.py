"""Pull one frame per story-map event so the selected intervals can actually be looked at.

The timings were derived by reading the film's subtitle track, not by watching it. A
subtitle tells you when someone speaks, not what is on screen, and several beats here are
silent action — a dog carried up a hill, a body on a kitchen floor. `needs_visual_review`
stays true until these frames confirm the interval shows what the summary claims.

Two ways to run it:

    python verify_intervals.py                    all 33, four sheets — the first pass
    python verify_intervals.py jack_sacrifice ...  only those, one sheet — after a fix

Use the second form once the first pass is done. Re-extracting 33 frames and re-reading
four sheets to check one moved interval costs about eight times what the fix did, and the
other 32 frames are identical to the ones already looked at.

Bare timecodes work too, for scanning a region before committing to a timing:

    python verify_intervals.py 28:40 29:15 29:40
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORY_MAP = ROOT / "story_map.v1.json"
WORK = ROOT / "work" / "interval_check"
CONFIG = ROOT / "config.json"
PER_SHEET = 9
THUMB_W = 480
CLOCK = re.compile(r"^(\d+):(\d{2})$")


def grab(source: Path, at: float, label: str, out: Path) -> None:
    # A colon in the label is read as the next drawtext option and breaks the filter, so
    # timecodes get written as 3m20s. Escaping it works too but reads worse in the frame.
    drawn = label.replace(":", "m", 1) + "s" if CLOCK.match(label.split()[-1] or "") else label
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-hwaccel", "cuda",
         "-ss", f"{at:.3f}", "-i", str(source), "-frames:v", "1",
         "-vf", f"scale={THUMB_W}:-2,"
                f"drawtext=text='{drawn.replace(':', 'm')}':x=8:y=8:fontsize=20:"
                "fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=6",
         "-q:v", "3", "-y", str(out)],
        check=True,
    )


def contact_sheet(frames: list[Path], out: Path, across: int = 3) -> None:
    inputs: list[str] = []
    for path in frames:
        inputs += ["-i", str(path)]
    rows = (len(frames) + across - 1) // across
    # tile works on successive frames of one stream, not on separate inputs, so the stills
    # have to be concatenated into a stream first. Feeding tile several inputs silently
    # lays down only the first and leaves the rest of the grid black.
    chain = "".join(f"[{i}:v]" for i in range(len(frames)))
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *inputs,
         "-filter_complex",
         f"{chain}concat=n={len(frames)}:v=1:a=0[s];"
         f"[s]tile={across}x{rows}:padding=6:color=black[o]",
         "-map", "[o]", "-frames:v", "1", "-q:v", "3", "-y", str(out)],
        check=True,
    )


def seconds(text: str) -> float | None:
    match = CLOCK.match(text)
    return int(match.group(1)) * 60 + int(match.group(2)) if match else None


def main(argv: list[str]) -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    source = (ROOT / config["video"]).resolve()
    WORK.mkdir(parents=True, exist_ok=True)

    stamps = [seconds(arg) for arg in argv]
    if argv and all(s is not None for s in stamps):
        frames = []
        for index, at in enumerate(stamps):
            out = WORK / f"scan_{index:02d}.jpg"
            grab(source, at, f"{int(at)//60}:{int(at)%60:02d}", out)
            frames.append(out)
            print(f"  {int(at)//60:>3}:{int(at)%60:02d}")
        sheet = WORK / "scan.jpg"
        contact_sheet(frames, sheet, across=min(4, len(frames)))
        print(f"\n  {sheet.relative_to(ROOT.parent)}")
        return 0

    story = json.loads(STORY_MAP.read_text(encoding="utf-8"))
    shots = []
    for section in story["sections"]:
        for event in section["events"]:
            start, end = event["selected_intervals"][0]
            shots.append((event["id"], start + (end - start) * 0.5, event["summary"]))

    wanted = set(argv)
    unknown = wanted - {eid for eid, _, _ in shots}
    if unknown:
        raise SystemExit("사건 id가 아닙니다: " + ", ".join(sorted(unknown)))
    if not wanted:
        for stale in WORK.glob("*.jpg"):
            stale.unlink()

    frames = []
    for index, (eid, at, summary) in enumerate(shots):
        if wanted and eid not in wanted:
            continue
        out = WORK / f"{index:02d}_{eid}.jpg"
        grab(source, at, f"{index:02d} {eid}  {int(at)//60}:{int(at)%60:02d}", out)
        frames.append(out)
        print(f"  {index:02d} {int(at)//60:>3}:{int(at)%60:02d}  {eid:26} {summary[:44]}")

    if wanted:
        sheet = WORK / "recheck.jpg"
        contact_sheet(frames, sheet, across=min(3, len(frames)))
        print(f"\n프레임 {len(frames)}장\n  {sheet.relative_to(ROOT.parent)}")
        return 0

    sheets = []
    for start in range(0, len(frames), PER_SHEET):
        sheet = WORK / f"sheet_{start//PER_SHEET + 1}.jpg"
        contact_sheet(frames[start:start + PER_SHEET], sheet)
        sheets.append(sheet)

    print(f"\n프레임 {len(frames)}장, 시트 {len(sheets)}장")
    for sheet in sheets:
        print(f"  {sheet.relative_to(ROOT.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
