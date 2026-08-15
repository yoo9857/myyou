"""Build the film-dialogue caption track for the trailer cut.

The trailer plays 131 lines of the film's dialogue but shipped with only the narration
captioned, so the characters were audible and unreadable. This maps each subtitle cue onto
the trailer's own clock and drops the ones that cannot be read: anything under the narration,
which the delivered design suppresses, and anything too brief to land.

    python devil/build_trailer_dialogue_srt.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

MIN_ON_SCREEN = 0.9      # shorter than this and it flashes rather than reads
NARRATION_CLEAR = 0.15   # gap either side of a narration caption


# Subtitle tracks mark a change of speaker with a leading dash on each part, and the parser
# joins the cue's lines into one string, so "-Get out. -Come on, now." arrives as a single
# run with the dashes still in it. On screen it should be two lines and no dashes: the line
# break is what says a second person is talking.
SPEAKER_SPLIT = re.compile(r"(?:^|\s+)-\s*(?=\S)")


def split_speakers(text: str) -> str:
    parts = [p.strip() for p in SPEAKER_SPLIT.split(text) if p.strip()]
    return "\n".join(parts) if len(parts) > 1 else text.lstrip("- ").strip()


def stamp(seconds: float) -> str:
    hours, rest = divmod(max(0.0, seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(secs):02d},{int(secs % 1 * 1000):03d}"


def main() -> int:
    import pipeline

    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    plan = json.loads((ROOT / "output" / "trailer_plan.json").read_text(encoding="utf-8"))
    cues = pipeline.parse_srt(ROOT / str(config["subtitle"]))
    package = ROOT / "output" / "capcut_import"

    narration = [(c.start, c.end) for c in
                 pipeline.parse_srt(package / "trailer_narration.srt")]

    shots = plan["shots"]
    entries = []
    for index, shot in enumerate(shots):
        start, end = float(shot["source_start"]), float(shot["source_end"])
        base = float(shot["timeline_start"])
        # A caption may only outlive its shot if the next shot continues the same moment of
        # the film. Trailer shots jump - consecutive ones here sit 17 seconds apart in the
        # source - so a line allowed to run on was appearing over footage where nobody was
        # saying it. Visible from about 2:54.
        following = shots[index + 1] if index + 1 < len(shots) else None
        continues = bool(following and abs(float(following["source_start"]) - end) < 0.5)
        for cue in cues:
            overlap_start, overlap_end = max(cue.start, start), min(cue.end, end)
            if overlap_end - overlap_start < 0.2 or not cue.text.strip():
                continue
            at = base + (overlap_start - start)
            room = overlap_end - overlap_start
            if continues:
                room = max(room, min(cue.end - overlap_start, 2.6))
            entries.append([at, at + room,
                            split_speakers(re.sub(r"<[^>]+>", "", cue.text).strip())])

    entries.sort(key=lambda e: e[0])
    merged: list[list] = []
    for entry in entries:
        if merged and entry[2] == merged[-1][2] and entry[0] - merged[-1][1] < 1.0:
            merged[-1][1] = max(merged[-1][1], entry[1])   # same line across adjacent shots
            continue
        if merged and entry[0] < merged[-1][1]:
            entry[0] = merged[-1][1] + 0.04
        if entry[1] - entry[0] >= MIN_ON_SCREEN:
            merged.append(entry)

    kept = []
    for at, until, text in merged:
        clash = next(((a, b) for a, b in narration
                      if a - NARRATION_CLEAR < until and at < b + NARRATION_CLEAR), None)
        if clash is None:
            kept.append((at, until, text))
            continue
        # Narration wins the lower third; the line resumes after it if enough is left.
        resume = clash[1] + NARRATION_CLEAR
        # Resuming can walk into the *next* narration cue, so the tail is trimmed to whatever
        # is clear before it. One line slipped through overlapping a caption without this.
        following = min((a for a, _ in narration if a > resume), default=until)
        until = min(until, following - NARRATION_CLEAR)
        if until - resume >= MIN_ON_SCREEN:
            kept.append((resume, until, text))

    out = package / "trailer_movie_captions.srt"
    out.write_text("".join(
        f"{i}\n{stamp(a)} --> {stamp(b)}\n{t}\n\n"
        for i, (a, b, t) in enumerate(kept, start=1)), encoding="utf-8")

    dropped = len(merged) - len(kept)
    print(f"  영화 대사 자막 {len(kept)}개  (해설과 겹쳐 제외 {dropped}개)")
    print(f"  화면 유지 {min(b - a for a, b, _ in kept):.1f}~{max(b - a for a, b, _ in kept):.1f}초")
    print(f"  기록: {out.relative_to(ROOT.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
