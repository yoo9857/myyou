"""Lay the review's recorded narration over the trailer cut and duck the film under it.

The lines are already recorded for the 19-minute review, so the soundtrack costs nothing to
build: pick the ones whose beat is on screen, space them so they never overlap, and let the
film play between them the way a trailer does.

    python devil/add_trailer_narration.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

GAP = 1.1          # silence between lines, so the cut can breathe
HEAD = 2.0         # let the first shot land before anyone speaks
TAIL = 3.0         # and finish on picture, not on a sentence


def duration(path: Path) -> float:
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)], text=True).strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # A finished cut is usually open in a player or an editor while the next one is built, and
    # Windows will not let a locked file be replaced. Versioned names sidestep that and keep
    # the previous take around to compare against.
    parser.add_argument("--out", default="devil_trailer_narrated.mp4")
    args = parser.parse_args()

    import pipeline

    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    plan = json.loads((ROOT / "output" / "trailer_plan.json").read_text(encoding="utf-8"))
    script = json.loads((ROOT / "output" / "narration_script_v5.json").read_text(encoding="utf-8"))
    review_plan = json.loads((ROOT / "output" / "edit_plan.json").read_text(encoding="utf-8"))
    trailer = ROOT / "output" / "devil_trailer_cut.mp4"
    audio_dir = ROOT / "output" / "capcut_import" / "narration_audio"

    # Which beat each recorded line belongs to, so a line only plays while its beat is up.
    beat_of = {int(s["order"]): s["story_event_id"] for s in review_plan["segments"]}
    lines = []
    for item in script["items"]:
        order = int(item["order"])
        clip = audio_dir / f"clip_{order:03d}.mp3"
        if item["use_narration"] and clip.exists() and order in beat_of:
            lines.append({"order": order, "beat": beat_of[order], "file": clip,
                          "text": item["tts_en"], "length": duration(clip)})

    # Walk the trailer shot by shot. When a beat comes up that still has an unused line and
    # there is room since the last one, that line goes in. The trailer's own order decides
    # which lines are used and in what sequence - nothing is re-cut to fit the words.
    used, placed, cursor = set(), [], HEAD
    total = duration(trailer)
    for shot in plan["shots"]:
        at = float(shot["timeline_start"])
        if at < cursor:
            continue
        candidate = next((l for l in lines
                          if l["beat"] == shot["event"] and l["order"] not in used), None)
        if candidate is None or at + candidate["length"] > total - TAIL:
            continue
        used.add(candidate["order"])
        placed.append({**candidate, "at": at})
        cursor = at + candidate["length"] + GAP

    if not placed:
        raise SystemExit("배치할 문장이 없습니다.")

    inputs, filters, labels = [], [], []
    gain = float(config.get("narration_voice_gain", 1.0))
    for index, line in enumerate(placed):
        inputs += ["-i", str(line["file"])]
        filters.append(f"[{index + 1}:a]aresample=48000,volume={gain:.4f},"
                       f"adelay={int(round(line['at'] * 1000))}:all=1[n{index}]")
        labels.append(f"[n{index}]")
    limiter = float(config.get("audio_limiter", 0.891251))
    # The narration stem keys a sidechain on the film bed, so the film ducks wherever a line
    # is speaking and comes straight back between them. Thirty-three separate windows would
    # otherwise need a volume expression long enough to be unreadable and easy to get wrong.
    threshold = float(config.get("trailer_duck_threshold", 0.03))
    ratio = float(config.get("trailer_duck_ratio", 12.0))
    chain = (";".join(filters) + ";" +
             f"anullsrc=r=48000:cl=stereo[silence];[silence]{''.join(labels)}"
             f"amix=inputs={len(placed) + 1}:duration=first:dropout_transition=0:normalize=0,"
             f"atrim=duration={total:.3f},asplit=2[vo][key];"
             f"[0:a]aresample=48000[bed];"
             f"[bed][key]sidechaincompress=threshold={threshold}:ratio={ratio}:"
             "attack=30:release=420:makeup=1[ducked];"
             f"[ducked][vo]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
             f"alimiter=limit={limiter:.6f}:level=false,atrim=duration={total:.3f}[a]")
    out = ROOT / "output" / args.out
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(trailer), *inputs,
         "-filter_complex", chain, "-map", "0:v:0", "-map", "[a]", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-movflags", "+faststart", "-y", str(out)],
        check=True)
    pipeline.master_audio(config, out)

    srt = ROOT / "output" / "capcut_import" / "trailer_narration.srt"
    def stamp(x):
        h, r = divmod(x, 3600); m, s = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"
    srt.write_text("".join(
        f"{i}\n{stamp(l['at'])} --> {stamp(l['at'] + l['length'])}\n{l['text']}\n\n"
        for i, l in enumerate(placed, start=1)), encoding="utf-8")

    print(f"  해설 {len(placed)}줄 배치 (녹음된 {len(lines)}줄 중)")
    for line in placed[:4]:
        print(f"    {line['at']/60:5.2f}분  {line['text'][:56]}")
    print(f"    ...")
    for line in placed[-2:]:
        print(f"    {line['at']/60:5.2f}분  {line['text'][:56]}")
    print(f"  자막: {srt.relative_to(ROOT.parent)}")
    print(f"  완료: {out.relative_to(ROOT.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
