"""Burn the edit plan into a watchable proxy so the order can be judged before anything is generated.

Getting the sequence wrong is cheap to fix and expensive to discover late. On this project
the beat order was wrong in every group - the cold open played third, the standoff played
before the character it comes after - and it was found only after the narration script had
been written four times and the voice generated as many. Both of those cost money per run.
The order does not: it is decided by the edit plan, and the edit plan already carries a
placeholder line for every narration slot.

So this renders the plan at proxy quality with everything you need to judge it burned into
the picture - segment number, beat id, and the narration line - and calls no API at all.
Watch it, fix the plan, run it again. Generate the script and the voice once, after.

    python scripts/build_structure_preview.py devil/config.json
    python scripts/build_structure_preview.py devil/config.json --from 900 --to 1040

Once the voice exists the preview plays the real mix - ducked bed, narration over it -
so what you judge is what ships. Before that, or with --hear-collisions, the film runs
at its natural level so you can hear which lines a narration slot would land on.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_ROOT))

STYLES = """[Script Info]
ScriptType: v4.00+
PlayResX: 960
PlayResY: 540
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Label,Consolas,15,&H00A0FF64,&H00000000,&HB4000000,1,0,3,0,0,7,14,14,10,1
Style: Narration,Arial,20,&H0064E1FF,&H00000000,&HB4000000,1,0,3,0,0,2,40,40,58,1
Style: Dialogue,Arial,18,&H00FFFFFF,&H00000000,&HB4000000,0,0,3,0,0,2,40,40,16,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def stamp(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{int(hours)}:{int(minutes):02d}:{secs:05.2f}"


def escape(text: str) -> str:
    # Subtitle tracks carry markup the burn would otherwise show literally, and ASS reads
    # braces as override blocks, so both are removed before the text reaches libass.
    text = re.sub(r"<[^>]+>", "", text)
    return (text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")
            .replace("\n", " ").strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--from", dest="start_sec", type=float, default=None,
                        help="Timeline second to start at, for checking one stretch.")
    parser.add_argument("--to", dest="end_sec", type=float, default=None)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--hear-collisions", action="store_true",
                        help="Play the film unducked and leave the voice out, to hear "
                             "exactly which lines a narration slot would land on.")
    args = parser.parse_args()

    import pipeline  # noqa: E402  - needs CODE_ROOT on the path first

    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.parent
    source = (root / config["video"]).resolve()
    plan = json.loads((root / "output" / "edit_plan.json").read_text(encoding="utf-8"))
    work = root / "work" / "preview"
    work.mkdir(parents=True, exist_ok=True)
    for stale in work.glob("*"):
        if stale.is_file():
            stale.unlink()

    subtitle_path = root / str(config.get("subtitle", ""))
    cues = pipeline.parse_srt(subtitle_path) if subtitle_path.exists() else []
    downmix = str(config.get("source_audio_downmix", "")).strip()

    lines, clips = [], []
    timeline = 0.0
    # Cue times are relative to the file being burned, not to the full review. With --from
    # they were left on the review's clock and every event landed past the end of a two-minute
    # excerpt, so the burn produced a clean picture and no captions at all.
    offset = None
    for segment in plan["segments"]:
        span = float(segment["source_end"]) - float(segment["source_start"])
        start, end = timeline, timeline + span
        if args.start_sec is not None and end < args.start_sec:
            timeline = end
            continue
        if args.end_sec is not None and start > args.end_sec:
            break
        if offset is None:
            offset = start
        start = start - offset

        order = int(segment["order"])
        text = str(segment.get("narration", "")).strip()
        clip = work / f"p_{order:03d}.mp4"
        voice = root / "output" / "capcut_import" / "narration_audio" / f"clip_{order:03d}.mp3"
        level = float(segment.get("audio_level", 0.96))
        bed = f"{downmix + ',' if downmix else ''}volume={level:.4f},aresample=48000"
        common = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-hwaccel", "cuda",
                  "-ss", f"{float(segment['source_start']):.3f}", "-t", f"{span:.3f}",
                  "-i", str(source)]
        video = f"[0:v:0]scale=-2:{args.height},fps=24,format=yuv420p[v]"
        encode = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
                  "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-ac", "2", "-y", str(clip)]
        # With the voice recorded, the preview plays the real mix - ducked bed and narration on
        # top - because judging whether a line talks over the film is impossible if the preview
        # runs the film at full level while the deliverable runs it 10 dB down.
        if args.hear_collisions or not (text and voice.exists()):
            subprocess.run([*common, "-filter_complex", f"{video};[0:a:0]{bed}[a]",
                            "-map", "[v]", "-map", "[a]", *encode], check=True)
        else:
            lead, _, _ = pipeline.segment_narration_timing(segment, span, config)
            delay = f",adelay={int(round(lead * 1000))}:all=1" if lead > 0 else ""
            subprocess.run(
                [*common, "-i", str(voice), "-filter_complex",
                 f"{video};[0:a:0]{bed}[b];[1:a:0]aresample=48000{delay}[n];"
                 "[b][n]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]",
                 "-map", "[v]", "-map", "[a]", *encode], check=True)
        # Cue times have to follow the encoded clip, not the plan. `-ss` lands on a keyframe,
        # so a clip comes out a few milliseconds off what was asked for, and concatenating 132
        # of them accumulated 2.66 seconds by the end - enough that captions visibly trailed
        # the lip movements from about the eleven-minute mark. pipeline.build_caption_tracks
        # already measures each clip for this reason; the preview has to as well.
        encoded = float(subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(clip)], text=True).strip())
        end = start + encoded
        source_start = float(segment["source_start"])
        source_end = source_start + min(encoded, span)

        resume_at = source_start
        narration_lead = narration_len = 0.0
        if text:
            narration_lead, narration_len, _ = pipeline.segment_narration_timing(
                segment, encoded, config)
            resume_at += narration_lead + narration_len + float(
                config.get("caption_resume_gap_sec", 0.12))
        label = (f"#{order:03d} {segment['kind']:15} {segment['story_event_id']}"
                 f"  src {source_start/60:.2f}m  {encoded:.1f}s")
        lines.append(f"Dialogue: 0,{stamp(start)},{stamp(end)},Label,,0,0,0,,{escape(label)}")
        if text:
            # Only while the voice is actually speaking, which is what the delivered track
            # does. Drawing it for the whole block put a narration caption on screen next to
            # a film line that had legitimately resumed - visible around 17:20.
            speak_from = start + narration_lead
            lines.append(
                f"Dialogue: 0,{stamp(speak_from)},{stamp(speak_from + narration_len)},"
                f"Narration,,0,0,0,,{escape(text)}")
        # The delivered caption tracks hold the film's dialogue back until the narration
        # caption is gone, and resume mid-cue if one was already running. Drawing both at
        # once - which this did at first - shows an overlap the finished review does not have,
        # and the point of a preview is to look like the thing it stands in for.
        for cue in cues:
            if cue.start >= source_end or cue.end <= resume_at:
                continue
            cue_start = start + max(cue.start, resume_at) - source_start
            cue_end = start + min(cue.end, source_end) - source_start
            if cue_end - cue_start >= 0.2:
                lines.append(f"Dialogue: 0,{stamp(cue_start)},{stamp(cue_end)},"
                             f"Dialogue,,0,0,0,,{escape(cue.text)}")

        clips.append(clip)
        timeline = end + offset
        print(f"  #{order:03d}  {(start + offset)/60:6.2f}m  {segment['story_event_id']}",
              flush=True)

    if not clips:
        raise SystemExit("구간이 선택되지 않았습니다.")

    ass_path = work / "preview.ass"
    ass_path.write_text(STYLES + "\n".join(lines) + "\n", encoding="utf-8")
    concat = work / "concat.txt"
    concat.write_text("\n".join(f"file '{c.as_posix()}'" for c in clips) + "\n", encoding="utf-8")
    joined = work / "joined.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "concat",
                    "-safe", "0", "-i", str(concat), "-c", "copy", "-y", str(joined)],
                   check=True)

    out = root / "output" / "structure_preview.mp4"
    # The subtitles filter takes a relative name with cwd set, because a Windows drive
    # letter's colon is read as a filter option separator. The output path is not a filter
    # argument, so it stays absolute.
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", joined.name,
         "-vf", f"subtitles={ass_path.name}", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "28", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", "-y",
         str(out)],
        check=True, cwd=work,
    )
    duration = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(out)], text=True).strip())
    print(f"\n  {len(clips)}구간 {duration/60:.2f}분 -> {out.relative_to(root)}")
    print("  자막 없음/생성 없음 — 순서를 확정한 뒤에 narration_pass.py generate를 한 번만 돌린다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
