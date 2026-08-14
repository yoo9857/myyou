"""Lay music under the closing block and let it take over once the narration stops.

The previous review ended on music and this one ended on room tone, because the pipeline has
no notion of an outro - it mixes narration and film audio per clip and stops there. The
shape is the one that worked before: the music comes in with the closing block, sits well
under the voice while the last lines play, rises when they finish, and fades out on the last
frame.

    python scripts/add_outro_music.py devil/config.json "The Final Resolve.mp3"

The window is not a guess. It starts where the closing section starts in the edit plan and
the rise is where the last narration line actually stops, measured from its audio file.
Re-masters afterwards, because adding a track moves the programme loudness off target.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_ROOT))

UNDER_SPEECH = 0.30      # the voice has to stay clearly on top
AFTER_SPEECH = 0.78
RISE_SECONDS = 1.5
FADE_SECONDS = 6.0
SOURCE_START = 8.0       # skip the track's quiet opening


def duration(path: Path) -> float:
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)], text=True).strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("music", type=Path)
    parser.add_argument("--closing-section", default="closing_wrap")
    parser.add_argument("--source-start", type=float, default=SOURCE_START)
    args = parser.parse_args()

    import pipeline

    config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    root = args.config.resolve().parent
    package = root / "output" / "capcut_import"
    master = root / "output" / str(config.get("output_video", "rough_cut.mp4"))
    if not master.exists():
        raise SystemExit(f"최종본이 없습니다: {master}")
    if not args.music.exists():
        raise SystemExit(f"음악 파일이 없습니다: {args.music}")

    plan = json.loads((root / "output" / "edit_plan.json").read_text(encoding="utf-8"))
    total = duration(master)

    timeline, start_at, speech_end = 0.0, None, 0.0
    for segment in plan["segments"]:
        length = float(segment["source_end"]) - float(segment["source_start"])
        clip = package / str(config.get("clips_dir", "clips")) / \
            f"clip_{int(segment['order']):03d}_{segment['kind']}.mp4"
        if clip.exists():
            length = duration(clip)
        if segment["story_beat"] == args.closing_section and start_at is None:
            start_at = timeline
        if str(segment.get("narration", "")).strip():
            voice = pipeline.narration_audio_path(int(segment["order"]))
            if voice.exists():
                lead, _, _ = pipeline.segment_narration_timing(segment, length, config)
                speech_end = max(speech_end, timeline + lead + duration(voice))
        timeline += length
    if start_at is None:
        raise SystemExit(f"마무리 구간을 찾지 못했습니다: {args.closing_section}")

    span = total - start_at
    available = duration(args.music) - args.source_start
    if span > available:
        raise SystemExit(f"음악이 {span - available:.1f}초 모자랍니다. --source-start를 줄이십시오.")

    rise_at = max(0.0, speech_end - start_at)
    fade_at = max(rise_at + 1.0, span - FADE_SECONDS)
    # min/max rather than clip(): this ffmpeg build evaluates clip() to NaN, and volume
    # reports "Invalid value NaN for volume, setting to 0" and plays silence. The same
    # expression is in mix_constantine_selected_voice.py, so that outro was probably mute too.
    gain = (f"{UNDER_SPEECH:.3f}+{AFTER_SPEECH - UNDER_SPEECH:.3f}"
            f"*min(1,max(0,(t-{rise_at:.3f})/{RISE_SECONDS:.1f}))")
    stem = package / "outro_music_stem.m4a"
    subprocess.run(
        # -vn because a music file often carries cover art, and an m4a asked to hold a
        # still image fails the mux.
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(args.music), "-vn",
         "-af", f"atrim=start={args.source_start:.3f}:duration={span:.3f},"
                "asetpts=PTS-STARTPTS,aresample=48000,"
                f"volume=eval=frame:volume='{gain}',"
                f"afade=t=out:st={fade_at:.3f}:d={span - fade_at:.3f}",
         "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "192k", "-y", str(stem)],
        check=True)

    limiter = float(config.get("audio_limiter", 0.891251))
    mixed = master.with_name(master.stem + ".outro.mp4")
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(master), "-i", str(stem),
         "-filter_complex",
         f"[1:a]adelay={int(round(start_at * 1000))}:all=1[music];"
         f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
         f"alimiter=limit={limiter:.6f}:level=false[a]",
         "-map", "0:v:0", "-map", "[a]", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-movflags", "+faststart", "-y", str(mixed)],
        check=True)
    mixed.replace(master)
    pipeline.master_audio(config, master)

    print(f"  마무리 음악 {args.music.name}")
    print(f"  시작 {start_at/60:.2f}분, 길이 {span:.1f}초")
    print(f"  해설 종료 {speech_end/60:.2f}분에서 {UNDER_SPEECH} -> {AFTER_SPEECH}")
    print(f"  페이드아웃 마지막 {span - fade_at:.1f}초")
    print(f"  스템: {stem.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
