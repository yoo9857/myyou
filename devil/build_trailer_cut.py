"""Cut a trailer-shaped version of the review.

Shots run 1 to 5 seconds against the review's 26, and it uses a quarter of the source the
review does, so it is a different object rather than a shortened one. The film's own audio
rides with the picture and ducks under the narration, the same way the long review does it.

The shape is a trailer's, not a review's: long holds while it establishes, shots getting
shorter as it builds, a hard cut to black before the end. Nothing after the spoiler cutoff.

    python devil/build_trailer_cut.py            # plan only
    python devil/build_trailer_cut.py --render
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

TARGET = 330.0          # 5:30, inside the 5-6 minutes asked for
BLACK_BETWEEN_ACTS = 0.7

# A trailer accelerates. Each act names the beats it draws from, the length a shot holds, and
# how much of the running time it gets. The last act is the shortest cuts and the least time,
# which is what makes it read as a climax rather than a montage.
ACTS = [
    ("establish", 0.26, 5.2, ["prayer_log_present", "crucified_soldier", "meets_charlotte",
                              "emma_matchmaking", "arvin_bullied", "willard_teaches_revenge"]),
    ("descend", 0.30, 3.4, ["charlotte_illness", "jack_sacrifice", "roy_spider_sermon",
                            "helen_chooses_roy", "roy_kills_helen", "roy_meets_carl",
                            "lenora_and_arvin", "earskell_gives_pistol"]),
    ("close_in", 0.26, 2.2, ["teagardin_arrives", "teagardin_sermon", "lenora_groomed",
                             "carl_method", "bodecker_corruption", "lenora_pregnant",
                             "lenora_dies", "suicide_burial_refused"]),
    ("break", 0.18, 1.1, ["arvin_confronts_preacher", "preacher_dies", "arvin_rides_with_carl",
                          "woods_shootout", "bodecker_learns", "arvin_returns_home",
                          "arvin_understands_father", "bodecker_calls_him_out", "standoff"]),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()

    import pipeline

    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    story = json.loads((ROOT / "story_map.v1.json").read_text(encoding="utf-8"))
    events = {e["id"]: e for s in story["sections"] for e in s["events"]}
    cutoff = float(story["spoiler_cutoff_source_sec"])
    source = (ROOT / config["video"]).resolve()

    shots, timeline = [], 0.0
    for index, (act, share, hold, beat_ids) in enumerate(ACTS):
        budget = TARGET * share
        beats = [events[b] for b in beat_ids if b in events]
        spent = 0.0
        # Shots are taken across the beat's window rather than all from its head, so the act
        # does not replay the same establishing frame every time it returns to a character.
        per_beat = max(1, round(budget / hold / max(1, len(beats))))
        for beat in beats:
            window_start = float(beat["source_start"])
            window_end = min(float(beat["source_end"]), cutoff)
            room = window_end - window_start
            for step in range(per_beat):
                if spent >= budget:
                    break
                offset = window_start + (room - hold) * (step / max(1, per_beat)) if room > hold else window_start
                end = min(offset + hold, window_end)
                if end - offset < 0.5:
                    continue
                shots.append({"act": act, "event": beat["id"], "hold": round(end - offset, 3),
                              "source_start": round(offset, 3), "source_end": round(end, 3),
                              "timeline_start": round(timeline, 3)})
                timeline += end - offset
                spent += end - offset
        if index < len(ACTS) - 1:
            timeline += BLACK_BETWEEN_ACTS

    plan = {
        "project_title": story["project_title"] + " — TRAILER CUT",
        "note": "Trailer pacing over the review's own beats. The film's audio rides with "
                "the picture; add_trailer_narration.py ducks it under the recorded lines.",
        "spoiler_cutoff_source_sec": cutoff,
        "black_between_acts_sec": BLACK_BETWEEN_ACTS,
        "shots": shots,
    }
    out = ROOT / "output" / "trailer_plan.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    total = sum(s["hold"] for s in shots) + BLACK_BETWEEN_ACTS * (len(ACTS) - 1)
    print(f"  샷 {len(shots)}개, 합계 {total/60:.2f}분")
    for act, share, hold, _ in ACTS:
        picked = [s for s in shots if s["act"] == act]
        print(f"    {act:10} {len(picked):3}샷  홀드 {hold:4.1f}초  "
              f"{sum(s['hold'] for s in picked):6.1f}초")
    print(f"  최종 원본 지점 {max(s['source_end'] for s in shots)/60:.2f}분 "
          f"(차단선 {cutoff/60:.2f}분)")
    print(f"  기록: {out.relative_to(ROOT.parent)}")
    if not args.render:
        print("  --render 를 붙이면 영상을 만듭니다.")
        return 0

    work = ROOT / "work" / "trailer"
    work.mkdir(parents=True, exist_ok=True)
    for stale in work.glob("*.mp4"):
        stale.unlink()
    width = int(config.get("render_width", 1920))
    height = int(config.get("render_height", 1080))
    fps = int(config.get("render_fps", 24))
    lines = []
    for index, shot in enumerate(shots):
        clip = work / f"t_{index:03d}.mp4"
        # Short shots cut straight into each other, so each one gets a brief fade at both ends
        # or every join is an audible click.
        downmix = str(config.get("source_audio_downmix", "")).strip()
        edge = min(0.06, shot["hold"] / 4)
        audio_chain = (f"{downmix + ',' if downmix else ''}aresample=48000,"
                       f"afade=t=in:st=0:d={edge:.3f},"
                       f"afade=t=out:st={shot['hold'] - edge:.3f}:d={edge:.3f}")
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-hwaccel", "cuda",
             "-ss", f"{shot['source_start']:.3f}", "-t", f"{shot['hold']:.3f}",
             "-i", str(source),
             "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps},format=yuv420p",
             "-af", audio_chain,
             "-c:v", "libx264", "-preset", str(config.get("render_preset", "medium")),
             "-crf", str(config.get("render_crf", 19)),
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-y", str(clip)],
            check=True)
        lines.append(f"file '{clip.as_posix()}'")
        if index + 1 < len(shots) and shots[index + 1]["act"] != shot["act"]:
            black = work / f"black_{index:03d}.mp4"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error",
                 "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r={fps}",
                 "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                 "-t", f"{BLACK_BETWEEN_ACTS:.3f}", "-c:v", "libx264",
                 "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-b:a", "192k", "-y", str(black)], check=True)
            lines.append(f"file '{black.as_posix()}'")
        print(f"  {index + 1:3}/{len(shots)}  {shot['act']:10} {shot['event']}", flush=True)

    concat = work / "concat.txt"
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
    joined = ROOT / "output" / "devil_trailer_cut.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "concat",
                    "-safe", "0", "-i", str(concat), "-c", "copy",
                    "-movflags", "+faststart", "-y", str(joined)], check=True)
    faded = joined.with_name(joined.stem + ".faded.mp4")
    length = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(joined)], text=True).strip())
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(joined),
         "-vf", f"fade=t=in:st=0:d=1.2,fade=t=out:st={length - 1.6:.3f}:d=1.6",
         "-c:v", "libx264", "-preset", str(config.get("render_preset", "medium")),
         "-crf", str(config.get("render_crf", 19)), "-c:a", "copy",
         "-movflags", "+faststart", "-y", str(faded)], check=True)
    faded.replace(joined)
    print(f"\n  완료: {joined.relative_to(ROOT.parent)}  {length/60:.2f}분  (무음)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
